import time
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

    def test_reports_live_info_while_searching(self):
        updates = []
        self.engine.search(chess.Board(), TimeBudget(0.5, 1.0), self.manager, updates.append)
        self.assertGreater(len(updates), 0)
        depths = [item.depth for item in updates]
        self.assertEqual(depths, sorted(depths))
        self.assertTrue(all(item.pv for item in updates))

    def test_ponder_reports_info_and_stops_cleanly(self):
        board = chess.Board()
        board.push_uci("e2e4")
        self.engine.start_ponder(board)
        time.sleep(0.5)
        live = self.engine.ponder_live()
        self.engine.stop_ponder()
        self.assertIsNotNone(live)
        self.assertIsNone(self.engine.ponder_live())

    def test_ponder_credit_shortens_search_on_predicted_reply(self):
        board = chess.Board()
        for uci in ("e2e4", "e7e5"):
            board.push_uci(uci)
        self.engine.new_game()
        self.engine.start_ponder(board)
        time.sleep(4.0)
        budget = TimeBudget(6.0, 12.0)
        credited = self.engine.search(board, budget, self.manager)
        plain = self.engine.search(board, budget, self.manager)
        self.assertLess(credited.elapsed, 2.5)
        self.assertLess(credited.elapsed, plain.elapsed - 1.0)
        self.assertIn(credited.move, board.legal_moves)

    def test_ponder_credit_is_ignored_on_a_different_position(self):
        board = chess.Board()
        board.push_uci("e2e4")
        self.engine.new_game()
        predicted = board.copy()
        predicted.push_uci("e7e5")
        self.engine.start_ponder(predicted)
        time.sleep(2.0)
        surprise = board.copy()
        surprise.push_uci("c7c5")
        result = self.engine.search(surprise, TimeBudget(2.0, 4.0), self.manager)
        self.assertGreater(result.elapsed, 1.0)

    def test_finds_mate_in_one(self):
        board = chess.Board("r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4")
        result = self.engine.search(board, TimeBudget(1.0, 2.0), self.manager)
        self.assertEqual(result.move.uci(), "h5f7")


if __name__ == "__main__":
    unittest.main()
