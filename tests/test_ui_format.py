import unittest

import chess

from chess_challenge.ui.format import (
    cell_of,
    eval_fraction,
    format_clock,
    format_count,
    move_list_rows,
    orient_score,
    pv_text,
    score_to_cp,
    square_at,
)


class FormatTest(unittest.TestCase):
    def test_clock(self):
        self.assertEqual(format_clock(754.9), "12:34")
        self.assertEqual(format_clock(-3), "0:00")

    def test_count(self):
        self.assertEqual(format_count(999), "999")
        self.assertEqual(format_count(15_000), "15k")
        self.assertEqual(format_count(2_500_000), "2.5M")
        self.assertEqual(format_count(3_000_000_000), "3.00G")

    def test_eval_fraction(self):
        self.assertAlmostEqual(eval_fraction(0), 0.5)
        self.assertGreater(eval_fraction(300), 0.6)
        self.assertLess(eval_fraction(-300), 0.4)
        self.assertEqual(eval_fraction(100000), 1.0)
        self.assertEqual(eval_fraction(-100000), 0.0)


class OrientTest(unittest.TestCase):
    def test_white_keeps_score(self):
        self.assertEqual(orient_score("+0.32", chess.WHITE), "+0.32")

    def test_black_flips_score(self):
        self.assertEqual(orient_score("+0.32", chess.BLACK), "-0.32")
        self.assertEqual(orient_score("-1.50", chess.BLACK), "+1.50")
        self.assertEqual(orient_score("#3", chess.BLACK), "#-3")
        self.assertEqual(orient_score("n/a", chess.BLACK), "n/a")


class ScoreToCpTest(unittest.TestCase):
    def test_conversion(self):
        self.assertEqual(score_to_cp("+0.32"), 32)
        self.assertEqual(score_to_cp("-1.50"), -150)
        self.assertEqual(score_to_cp("#3"), 100000)
        self.assertEqual(score_to_cp("#-2"), -100000)


class PvTest(unittest.TestCase):
    def test_pv_from_white(self):
        moves = [chess.Move.from_uci(m) for m in ("e2e4", "e7e5", "g1f3")]
        self.assertEqual(pv_text(chess.Board(), moves), "1. e4 e5 2. Nf3")

    def test_pv_from_black(self):
        board = chess.Board()
        board.push_uci("e2e4")
        moves = [chess.Move.from_uci(m) for m in ("e7e5", "g1f3")]
        self.assertEqual(pv_text(board, moves), "1... e5 2. Nf3")

    def test_pv_stops_at_illegal_move(self):
        moves = [chess.Move.from_uci(m) for m in ("e2e4", "e2e4")]
        self.assertEqual(pv_text(chess.Board(), moves), "1. e4")

    def test_pv_respects_limit(self):
        moves = [chess.Move.from_uci(m) for m in ("e2e4", "e7e5", "g1f3", "b8c6")]
        self.assertEqual(pv_text(chess.Board(), moves, limit=2), "1. e4 e5")


class MoveListTest(unittest.TestCase):
    def test_rows(self):
        board = chess.Board()
        for uci in ("e2e4", "e7e5", "g1f3"):
            board.push_uci(uci)
        self.assertEqual(move_list_rows(board), [(1, "e4", "e5"), (2, "Nf3", "")])

    def test_rows_starting_with_black(self):
        board = chess.Board("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1")
        board.push_uci("e7e5")
        self.assertEqual(move_list_rows(board), [(1, "...", "e5")])


class GeometryTest(unittest.TestCase):
    def test_square_mapping_roundtrip(self):
        for flipped in (False, True):
            for square in chess.SQUARES:
                column, row = cell_of(square, flipped)
                self.assertEqual(square_at(column, row, flipped), square)

    def test_orientation(self):
        self.assertEqual(cell_of(chess.A1, False), (0, 7))
        self.assertEqual(cell_of(chess.A1, True), (7, 0))


if __name__ == "__main__":
    unittest.main()
