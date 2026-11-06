from pathlib import Path

import chess
import chess.polyglot


class Book:
    def __init__(self, path: Path | None, max_plies: int) -> None:
        if path is not None and not path.exists():
            raise FileNotFoundError(f"Livro de aberturas nao encontrado em {path}")
        self._path = path
        self._max_plies = max_plies

    def pick(self, board: chess.Board) -> chess.Move | None:
        if self._path is None or board.ply() >= self._max_plies:
            return None
        try:
            with chess.polyglot.open_reader(str(self._path)) as reader:
                move = reader.weighted_choice(board).move
        except IndexError:
            return None
        return move if move in board.legal_moves else None
