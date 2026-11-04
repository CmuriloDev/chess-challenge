import os
import time
from dataclasses import dataclass, field

import chess
import chess.engine

from .config import Config
from .timemanager import TimeBudget, TimeManager
from .tracker import SearchTracker

POLL_INTERVAL = 0.01
LIMIT_GRACE = 1.0


@dataclass
class SearchResult:
    move: chess.Move
    depth: int
    nodes: int
    score: str
    pv: list[chess.Move]
    elapsed: float
    source: str
    san: str = field(default="")


def format_score(score: chess.engine.PovScore | None) -> str:
    if score is None:
        return "n/a"
    white = score.white()
    if white.is_mate():
        return f"#{white.mate()}"
    return f"{white.score() / 100:+.2f}"


class Engine:
    def __init__(self, config: Config) -> None:
        if not config.engine_path.exists():
            raise FileNotFoundError(f"Stockfish nao encontrado em {config.engine_path}")
        self._engine = chess.engine.SimpleEngine.popen_uci(str(config.engine_path))
        self._game = object()
        self._ponder: chess.engine.SimpleAnalysis | None = None
        self._configure(config)

    def _configure(self, config: Config) -> None:
        options: dict[str, object] = {"Threads": config.threads, "Hash": config.hash_mb}
        if config.syzygy_path is not None and config.syzygy_path.exists():
            options["SyzygyPath"] = os.fspath(config.syzygy_path)
            options["SyzygyProbeLimit"] = min(5, config.tablebase_max_pieces)
        supported = {key: value for key, value in options.items() if key in self._engine.options}
        self._engine.configure(supported)

    @property
    def name(self) -> str:
        return self._engine.id.get("name", "Stockfish")

    def new_game(self) -> None:
        self._game = object()

    def start_ponder(self, board: chess.Board) -> None:
        self.stop_ponder()
        if board.is_game_over():
            return
        self._ponder = self._engine.analysis(board, chess.engine.Limit(), game=self._game)

    def stop_ponder(self) -> None:
        analysis, self._ponder = self._ponder, None
        if analysis is None:
            return
        try:
            analysis.stop()
            analysis.wait()
        except chess.engine.EngineError:
            pass

    def search(self, board: chess.Board, budget: TimeBudget, manager: TimeManager) -> SearchResult:
        self.stop_ponder()
        start = time.perf_counter()
        tracker = SearchTracker(board.turn)
        limit = chess.engine.Limit(time=budget.hard + LIMIT_GRACE)
        with self._engine.analysis(board, limit, game=self._game) as analysis:
            while True:
                time.sleep(POLL_INTERVAL)
                elapsed = time.perf_counter() - start
                tracker.update(dict(analysis.info), elapsed)
                if manager.should_stop(elapsed, budget, tracker):
                    break
            analysis.stop()
            best = analysis.wait()
        elapsed = time.perf_counter() - start
        info = dict(analysis.info)
        pv = list(info.get("pv") or [])
        move = best.move or (pv[0] if pv else next(iter(board.legal_moves)))
        if not pv or pv[0] != move:
            pv = [move]
        return SearchResult(
            move=move,
            depth=int(info.get("depth", 0)),
            nodes=int(info.get("nodes", 0)),
            score=format_score(info.get("score")),
            pv=pv,
            elapsed=elapsed,
            source="engine",
        )

    def close(self) -> None:
        self.stop_ponder()
        try:
            self._engine.quit()
        except chess.engine.EngineError:
            self._engine.close()

    def __enter__(self) -> "Engine":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
