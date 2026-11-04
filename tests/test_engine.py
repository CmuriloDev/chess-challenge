import unittest

import chess

from chess_challenge.config import Config
from chess_challenge.engine import Engine
from chess_challenge.timemanager import TimeBudget, TimeManager


def engine_available() -> bool:
    return Config().engine_path.exists()


@unittest.skipUnless(engine_available(), "stockfish binary not available")
class EngineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = Engine(Config(threads=1, hash_mb=16))
        cls.manager = TimeManager(increment=0.0, overhead=0.0)

    @classmethod
    def tearDownClass(cls):
        cls.engine.close()

    def test_returns_legal_move_within_hard_limit(self):
        board = chess.Board()
        result = self.engine.search(board, TimeBudget(0.3, 0.6), self.manager)
        self.assertIn(result.move, board.legal_moves)
        self.assertLess(result.elapsed, 1.5)
        self.assertGreater(result.depth, 0)
        self.assertGreater(result.nodes, 0)

    def test_finds_mate_in_one(self):
        board = chess.Board("r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4")
        result = self.engine.search(board, TimeBudget(1.0, 2.0), self.manager)
        self.assertEqual(result.move.uci(), "h5f7")


if __name__ == "__main__":
    unittest.main()
