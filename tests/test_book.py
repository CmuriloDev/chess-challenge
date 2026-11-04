import struct
import tempfile
import unittest
from pathlib import Path

import chess
import chess.polyglot

from chess_challenge.book import Book


def polyglot_entry(board: chess.Board, move: chess.Move) -> bytes:
    raw = move.to_square | (move.from_square << 6)
    return struct.pack(">QHHI", chess.polyglot.zobrist_hash(board), raw, 1, 0)


def write_book(path: Path, board: chess.Board, move: chess.Move) -> None:
    path.write_bytes(polyglot_entry(board, move))


class BookTest(unittest.TestCase):
    def test_no_book_returns_none(self):
        self.assertIsNone(Book(None, 10).pick(chess.Board()))

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            Book(Path("does-not-exist.bin"), 10)

    def test_returns_book_move_inside_ply_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "book.bin"
            board = chess.Board()
            move = chess.Move.from_uci("e2e4")
            write_book(path, board, move)
            self.assertEqual(Book(path, 10).pick(board), move)

    def test_ignores_book_after_ply_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "book.bin"
            board = chess.Board()
            for uci in ("e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "a7a6", "b5a4", "g8f6", "e1g1", "f8e7"):
                board.push_uci(uci)
            self.assertEqual(board.ply(), 10)
            write_book(path, board, chess.Move.from_uci("f1e1"))
            self.assertIsNone(Book(path, 10).pick(board))
            self.assertEqual(Book(path, 12).pick(board), chess.Move.from_uci("f1e1"))

    def test_unknown_position_returns_none(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "book.bin"
            write_book(path, chess.Board(), chess.Move.from_uci("e2e4"))
            board = chess.Board()
            board.push_uci("d2d4")
            self.assertIsNone(Book(path, 10).pick(board))


if __name__ == "__main__":
    unittest.main()
