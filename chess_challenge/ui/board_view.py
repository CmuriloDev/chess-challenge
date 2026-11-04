import tkinter as tk
from typing import Callable

import chess

from .format import cell_of, square_at

LIGHT = "#ebecd0"
DARK = "#739552"
LAST_LIGHT = "#f5f682"
LAST_DARK = "#b9ca43"
SELECTED = "#f7d154"
ARROW = "#16a34a"
LABEL = "#9ca3af"
BACKGROUND = "#1e1f22"
WHITE_FILL = "#fafafa"
WHITE_EDGE = "#1a1a1a"
BLACK_FILL = "#141414"
BLACK_EDGE = "#d4d4d4"
PIECE_FONT = "Segoe UI Symbol"
GLYPHS = {
    chess.KING: "♚",
    chess.QUEEN: "♛",
    chess.ROOK: "♜",
    chess.BISHOP: "♝",
    chess.KNIGHT: "♞",
    chess.PAWN: "♟",
}


class BoardView(tk.Canvas):
    def __init__(
        self,
        master: tk.Misc,
        size: int = 640,
        margin: int = 26,
        on_click: Callable[[chess.Square], None] | None = None,
    ) -> None:
        super().__init__(
            master, width=size, height=size, bg=BACKGROUND, highlightthickness=0
        )
        self.margin = margin
        self.cell = (size - 2 * self.margin) // 8
        self._on_click = on_click
        self._flipped = False
        self._board = chess.Board()
        self._last: chess.Move | None = None
        self._announced: chess.Move | None = None
        self._selected: chess.Square | None = None
        self.bind("<Button-1>", self._clicked)

    def render(
        self,
        board: chess.Board,
        flipped: bool,
        last_move: chess.Move | None = None,
        announced: chess.Move | None = None,
        selected: chess.Square | None = None,
    ) -> None:
        self._board = board
        self._flipped = flipped
        self._last = last_move
        self._announced = announced
        self._selected = selected
        self._draw()

    def _origin(self, square: chess.Square) -> tuple[int, int]:
        column, row = cell_of(square, self._flipped)
        return self.margin + column * self.cell, self.margin + row * self.cell

    def _center(self, square: chess.Square) -> tuple[float, float]:
        x, y = self._origin(square)
        return x + self.cell / 2, y + self.cell / 2

    def _draw(self) -> None:
        self.delete("all")
        highlighted = set()
        if self._last is not None:
            highlighted = {self._last.from_square, self._last.to_square}
        for square in chess.SQUARES:
            x, y = self._origin(square)
            light = (chess.square_file(square) + chess.square_rank(square)) % 2 == 1
            if square == self._selected:
                color = SELECTED
            elif square in highlighted:
                color = LAST_LIGHT if light else LAST_DARK
            else:
                color = LIGHT if light else DARK
            self.create_rectangle(x, y, x + self.cell, y + self.cell, fill=color, outline=color)
        self._draw_labels()
        if self._announced is not None:
            self._draw_arrow(self._announced)
        for square, piece in self._board.piece_map().items():
            self._draw_piece(square, piece)

    def _draw_labels(self) -> None:
        for index in range(8):
            file_index = 7 - index if self._flipped else index
            rank_index = index if self._flipped else 7 - index
            x = self.margin + index * self.cell + self.cell / 2
            y = self.margin + index * self.cell + self.cell / 2
            file_letter = chess.FILE_NAMES[file_index]
            rank_number = chess.RANK_NAMES[rank_index]
            bottom = self.margin + 8 * self.cell + self.margin / 2
            top = self.margin / 2
            self.create_text(x, bottom, text=file_letter, fill=LABEL, font=("Segoe UI", 10, "bold"))
            self.create_text(x, top, text=file_letter, fill=LABEL, font=("Segoe UI", 10, "bold"))
            left = self.margin / 2
            right = self.margin + 8 * self.cell + self.margin / 2
            self.create_text(left, y, text=rank_number, fill=LABEL, font=("Segoe UI", 10, "bold"))
            self.create_text(right, y, text=rank_number, fill=LABEL, font=("Segoe UI", 10, "bold"))

    def _draw_piece(self, square: chess.Square, piece: chess.Piece) -> None:
        x, y = self._center(square)
        size = -int(self.cell * 0.78)
        glyph = GLYPHS[piece.piece_type]
        font = (PIECE_FONT, size)
        if piece.color == chess.WHITE:
            fill, edge = WHITE_FILL, WHITE_EDGE
        else:
            fill, edge = BLACK_FILL, BLACK_EDGE
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)):
            self.create_text(x + dx, y + dy, text=glyph, fill=edge, font=font)
        self.create_text(x, y, text=glyph, fill=fill, font=font)

    def _draw_arrow(self, move: chess.Move) -> None:
        x1, y1 = self._center(move.from_square)
        x2, y2 = self._center(move.to_square)
        self.create_line(
            x1,
            y1,
            x2,
            y2,
            fill=ARROW,
            width=self.cell * 0.16,
            arrow=tk.LAST,
            arrowshape=(self.cell * 0.34, self.cell * 0.4, self.cell * 0.2),
            capstyle=tk.ROUND,
        )

    def _clicked(self, event: tk.Event) -> None:
        if self._on_click is None:
            return
        column = (event.x - self.margin) // self.cell
        row = (event.y - self.margin) // self.cell
        if 0 <= column < 8 and 0 <= row < 8:
            self._on_click(square_at(column, row, self._flipped))
