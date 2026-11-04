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

    @property
    def our_turn(self) -> bool:
        return self.board.turn == self.color

    def outcome(self) -> chess.Outcome | None:
        return self.board.outcome(claim_draw=True)

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
        number = board.fullmove_number
        mover = board.turn
        result.san = board.san(result.move)
        board.push(result.move)
        self.clock.spend(result.elapsed, self._typed)
        self._typed = False
        self.logger.engine_move(number, mover, result, self.clock.remaining)
        self._ponder(result)
        return result

    def _ponder(self, result: SearchResult) -> None:
        if not self.config.ponder or len(result.pv) < 2 or self.outcome() is not None:
            return
        reply = result.pv[1]
        if reply not in self.board.legal_moves:
            return
        predicted = self.board.copy()
        predicted.push(reply)
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
