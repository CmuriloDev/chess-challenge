from datetime import datetime
from pathlib import Path

import chess

from .engine import SearchResult


def color_name(color: chess.Color) -> str:
    return "white" if color == chess.WHITE else "black"


class GameLogger:
    def __init__(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = directory / f"game_{stamp}.log"
        self._file = self.path.open("w", encoding="utf-8")

    def _write(self, line: str) -> None:
        self._file.write(line + "\n")
        self._file.flush()

    def header(self, **fields: object) -> None:
        for key, value in fields.items():
            self._write(f"# {key}={value}")

    def engine_move(
        self, number: int, color: chess.Color, result: SearchResult, remaining: float
    ) -> None:
        pv = " ".join(move.uci() for move in result.pv)
        self._write(
            f"move={number} color={color_name(color)} uci={result.move.uci()} "
            f"depth={result.depth} nodes={result.nodes} eval={result.score} "
            f"pv={pv} time={result.elapsed:.3f}s source={result.source} "
            f"clock={remaining:.1f}s"
        )

    def opponent_move(self, number: int, color: chess.Color, move: chess.Move) -> None:
        self._write(f"move={number} color={color_name(color)} uci={move.uci()} source=opponent")

    def event(self, text: str) -> None:
        self._write(f"# {text}")

    def close(self) -> None:
        self._file.close()
