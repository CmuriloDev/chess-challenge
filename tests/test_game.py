import tempfile
import unittest
from pathlib import Path

import chess

from chess_challenge.book import Book
from chess_challenge.clock import Clock
from chess_challenge.config import Config
from chess_challenge.engine import Engine, SearchResult
from chess_challenge.game import Game, IllegalMove
from chess_challenge.logger import GameLogger
from chess_challenge.timemanager import TimeManager


class StubEngine:
    def __init__(self):
        self.calls = 0

    def search(self, board, budget, manager):
        self.calls += 1
        move = next(iter(board.legal_moves))
        return SearchResult(move, 10, 1000, "+0.10", [move], 0.2, "engine")


def build_game(engine, color=chess.WHITE, directory=None):
    config = Config(threads=1, hash_mb=16)
    logger = GameLogger(Path(directory))
    clock = Clock(900.0, 10.0, 5.0)
    manager = TimeManager(10.0, 5.0)
    return Game(config, engine, color, logger, clock, manager, Book(None, 10))


class GameTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)

    def make(self, color=chess.WHITE, directory=None):
        game = build_game(StubEngine(), color=color, directory=directory)
        self.addCleanup(game.logger.close)
        return game

    def test_rejects_illegal_and_malformed_moves(self):
        game = self.make(directory=self.directory.name)
        game.board.push_uci("e2e4")
        for text in ("e2e4", "zzzz", "", "e7e9"):
            with self.assertRaises(IllegalMove):
                game.apply_opponent_move(text)

    def test_accepts_uci_promotion(self):
        game = self.make(color=chess.BLACK, directory=self.directory.name)
        game.set_fen("8/4P3/8/8/8/k7/8/4K3 w - - 0 1")
        move = game.apply_opponent_move("e7e8q")
        self.assertEqual(move.promotion, chess.QUEEN)

    def test_choose_move_updates_clock_and_board(self):
        game = self.make(directory=self.directory.name)
        result = game.choose_move()
        self.assertEqual(game.board.peek(), result.move)
        self.assertEqual(game.clock.remaining, 900.0 - 0.2 - 5.0 + 10.0)
        self.assertFalse(game.our_turn)

    def test_single_legal_move_is_forced(self):
        game = self.make(directory=self.directory.name)
        game.set_fen("7k/8/8/8/8/8/6q1/7K w - - 0 1")
        legal = list(game.board.legal_moves)
        self.assertEqual(len(legal), 1)
        result = game.choose_move()
        self.assertEqual(result.move, legal[0])
        self.assertEqual(result.source, "forced")

    def test_undo_restores_previous_position(self):
        game = self.make(directory=self.directory.name)
        game.choose_move()
        self.assertIsNotNone(game.undo())
        self.assertEqual(game.board.fen(), chess.Board().fen())
        self.assertIsNone(game.undo())

    def test_set_fen_rejects_garbage(self):
        game = self.make(directory=self.directory.name)
        with self.assertRaises(IllegalMove):
            game.set_fen("not a fen")


class RealEngineGameTest(unittest.TestCase):
    @unittest.skipUnless(Config().engine_path.exists(), "stockfish binary not available")
    def test_full_cycle_with_real_engine(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Config(threads=1, hash_mb=16, increment=0.0, move_overhead=0.0)
            with Engine(config) as engine:
                logger = GameLogger(Path(directory))
                game = Game(
                    config, engine, chess.WHITE, logger, Clock(20.0, 0.0, 0.0),
                    TimeManager(0.0, 0.0, safety=1.0), Book(None, 10),
                )
                first = game.choose_move()
                game.apply_opponent_move("e7e5")
                second = game.choose_move()
                logger.close()
                text = logger.path.read_text(encoding="utf-8")
            self.assertIn(first.move.uci(), text)
            self.assertIn(second.move.uci(), text)
            self.assertIn("uci=e7e5", text)


if __name__ == "__main__":
    unittest.main()
