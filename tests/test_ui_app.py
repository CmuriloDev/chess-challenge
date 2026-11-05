import tempfile
import time
import tkinter as tk
import unittest
from pathlib import Path

import chess

from chess_challenge.book import Book
from chess_challenge.clock import Clock
from chess_challenge.config import Config
from chess_challenge.engine import SearchResult
from chess_challenge.game import Game
from chess_challenge.logger import GameLogger
from chess_challenge.timemanager import TimeManager
from chess_challenge.ui.app import App


class StubEngine:
    name = "Stub"

    def search(self, board, budget, manager, on_info=None):
        move = next(iter(board.legal_moves))
        return SearchResult(move, 12, 5000, "+0.25", [move], 0.1, "engine")

    def start_ponder(self, board):
        pass

    def stop_ponder(self):
        pass

    def ponder_live(self):
        return None


def open_root():
    try:
        root = tk.Tk()
    except tk.TclError:
        return None
    root.withdraw()
    return root


class AppTest(unittest.TestCase):
    def setUp(self):
        self.root = open_root()
        if self.root is None:
            self.skipTest("no display available")
        self.addCleanup(self.root.destroy)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)

    def make_app(self, color):
        config = Config(threads=1, hash_mb=16)
        logger = GameLogger(Path(self.directory.name))
        self.addCleanup(logger.close)
        game = Game(
            config,
            StubEngine(),
            color,
            logger,
            Clock(900.0, 10.0, 2.0),
            TimeManager(10.0, 2.0),
            Book(None, 10),
        )
        app = App(self.root, game)
        self.addCleanup(app.join_worker)
        self.addCleanup(app.shutdown)
        return app

    def pump(self, condition, timeout=3.0):
        deadline = time.perf_counter() + timeout
        while time.perf_counter() < deadline:
            self.root.update()
            if condition():
                return True
            time.sleep(0.01)
        return False

    def test_plays_first_move_as_white_and_announces_it(self):
        app = self.make_app(chess.WHITE)
        self.assertTrue(self.pump(lambda: app.announced is not None))
        self.assertEqual(len(app.game.board.move_stack), 1)
        self.assertIn(app.announced.uci(), app.banner_move.cget("text"))

    def test_waits_for_opponent_when_black(self):
        app = self.make_app(chess.BLACK)
        self.root.update()
        self.assertFalse(app.thinking)
        self.assertEqual(len(app.game.board.move_stack), 0)

    def test_rejects_illegal_text_and_keeps_board(self):
        app = self.make_app(chess.WHITE)
        self.pump(lambda: app.announced is not None)
        app.submit("zzzz")
        self.assertIn("ilegal", app.message.cget("text"))
        self.assertEqual(len(app.game.board.move_stack), 1)

    def test_click_to_move_triggers_reply(self):
        app = self.make_app(chess.WHITE)
        self.pump(lambda: app.announced is not None)
        app.on_square(chess.E7)
        self.assertEqual(app.selected, chess.E7)
        app.on_square(chess.E5)
        self.assertTrue(self.pump(lambda: len(app.game.board.move_stack) == 3 and not app.thinking))
        self.assertEqual(app.game.board.move_stack[1].uci(), "e7e5")

    def test_measured_entry_latency_reaches_the_clock(self):
        app = self.make_app(chess.WHITE)
        self.pump(lambda: app.announced is not None)
        app.first_input = time.perf_counter() - 4.0
        app.submit("e7e5")
        self.pump(lambda: len(app.game.board.move_stack) == 3 and not app.thinking)
        self.assertGreaterEqual(app.game.clock.expected_entry(), 4.0)


if __name__ == "__main__":
    unittest.main()
