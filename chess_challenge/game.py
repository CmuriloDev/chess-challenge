import time
from typing import Callable

import chess

from .book import Book
from .clock import Clock
from .config import Config
from .engine import Engine, LiveInfo, SearchResult
from .logger import GameLogger
from .timemanager import TimeBudget, TimeManager

FORCED_MOVE_BUDGET = TimeBudget(0.05, 0.1)
BETTER_CP = 30
STRONG_CP = 100
MATE_CP = 90000
KEEP_CP = 15
ALTERNATIVE_SHARE = 0.5
FINAL_TERMINATIONS = (
    chess.Termination.CHECKMATE,
    chess.Termination.STALEMATE,
    chess.Termination.INSUFFICIENT_MATERIAL,
)


class IllegalMove(Exception):
    pass


class Game:
    def __init__(
        self,
        config: Config,
        engine: Engine,
        color: chess.Color,
        logger: GameLogger,
        clock: Clock,
        manager: TimeManager,
        book: Book,
    ) -> None:
        self.config = config
        self.engine = engine
        self.color = color
        self.logger = logger
        self.clock = clock
        self.manager = manager
        self.book = book
        self.board = chess.Board()
        self._typed = False
        self.ponder_board: chess.Board | None = None
        self._notice: str | None = None

    @property
    def our_turn(self) -> bool:
        return self.board.turn == self.color

    def outcome(self) -> chess.Outcome | None:
        outcome = self.board.outcome(claim_draw=True)
        if outcome is not None and outcome.termination in FINAL_TERMINATIONS:
            return outcome
        return None

    def new_draw_notice(self) -> str | None:
        outcome = self.board.outcome(claim_draw=True)
        if outcome is None or outcome.termination in FINAL_TERMINATIONS:
            self._notice = None
            return None
        name = outcome.termination.name
        if name == self._notice:
            return None
        self._notice = name
        self.logger.event(f"aviso={name} jogo continua")
        return name

    def apply_opponent_move(self, text: str, entry_latency: float | None = None) -> chess.Move:
        try:
            move = chess.Move.from_uci(text.strip().lower())
        except ValueError as error:
            raise IllegalMove(text) from error
        if move not in self.board.legal_moves:
            raise IllegalMove(text)
        self.engine.stop_ponder()
        self.ponder_board = None
        if entry_latency is not None:
            self.clock.record_entry(entry_latency)
        self._typed = True
        number = self.board.fullmove_number
        mover = self.board.turn
        self.board.push(move)
        self.logger.opponent_move(number, mover, move)
        return move

    def choose_move(self, on_info: Callable[[LiveInfo], None] | None = None) -> SearchResult:
        board = self.board
        start = time.perf_counter()
        legal = list(board.legal_moves)
        book_move = self.book.pick(board)
        if book_move is not None:
            result = SearchResult(
                book_move, 0, 0, "n/a", [book_move], time.perf_counter() - start, "book"
            )
        elif len(legal) == 1:
            result = self.engine.search(board, FORCED_MOVE_BUDGET, self.manager, on_info)
            result.move = legal[0]
            result.source = "forced"
        else:
            overhead = self.clock.expected_overhead(self._typed)
            budget = self.manager.budget(board, self.clock.remaining, overhead)
            result = self.engine.search(board, budget, self.manager, on_info)
            result = self._avoid_repetition(result, budget, on_info)
        number = board.fullmove_number
        mover = board.turn
        result.san = board.san(result.move)
        board.push(result.move)
        self.clock.spend(result.elapsed, self._typed)
        self._typed = False
        self.logger.engine_move(number, mover, result, self.clock.remaining)
        self._ponder(result)
        return result

    def _our_cp(self, result: SearchResult) -> int:
        return result.centipawns if self.color == chess.WHITE else -result.centipawns

    def _after(self, move: chess.Move) -> chess.Board:
        board = self.board.copy()
        board.push(move)
        return board

    def _draws_now(self, move: chess.Move) -> bool:
        board = self._after(move)
        return board.is_repetition(3) or board.halfmove_clock >= 100

    def _repeats(self, move: chess.Move) -> bool:
        return self._after(move).is_repetition(2)

    def _avoid_repetition(
        self,
        result: SearchResult,
        budget: TimeBudget,
        on_info: Callable[[LiveInfo], None] | None,
    ) -> SearchResult:
        cp = self._our_cp(result)
        if result.source != "engine" or cp < BETTER_CP or cp >= MATE_CP:
            return result
        strong = cp >= STRONG_CP

        def bad(move: chess.Move) -> bool:
            return self._draws_now(move) or (strong and self._repeats(move))

        if not bad(result.move):
            return result
        allowed = [move for move in self.board.legal_moves if not bad(move)]
        if not allowed:
            return result
        extra = TimeBudget(budget.soft * ALTERNATIVE_SHARE, budget.hard * ALTERNATIVE_SHARE)
        alternative = self.engine.search(self.board, extra, self.manager, on_info, root_moves=allowed)
        total = result.elapsed + alternative.elapsed
        if self._our_cp(alternative) < KEEP_CP:
            result.elapsed = total
            return result
        alternative.elapsed = total
        alternative.source = "engine-norep"
        self.logger.event(f"repeticao evitada: {result.move.uci()} trocado por {alternative.move.uci()}")
        return alternative

    def _ponder(self, result: SearchResult) -> None:
        if not self.config.ponder or self.outcome() is not None:
            return
        predicted = self.board.copy()
        if len(result.pv) >= 2 and result.pv[1] in predicted.legal_moves:
            predicted.push(result.pv[1])
        self.ponder_board = predicted
        self.engine.start_ponder(predicted)

    def undo(self) -> chess.Move | None:
        self.engine.stop_ponder()
        self.ponder_board = None
        if not self.board.move_stack:
            return None
        return self.board.pop()

    def set_fen(self, fen: str) -> None:
        try:
            board = chess.Board(fen)
        except ValueError as error:
            raise IllegalMove(fen) from error
        self.engine.stop_ponder()
        self.ponder_board = None
        self.board = board
        self.logger.event(f"fen={board.fen()}")
