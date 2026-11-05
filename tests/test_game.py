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
        self.pondered = []
        self.stops = 0

    def start_ponder(self, board):
        self.pondered.append(board.fen())

    def stop_ponder(self):
        self.stops += 1

    def search(self, board, budget, manager, on_info=None, root_moves=None):
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

    def test_opponent_entry_latency_is_charged_to_the_clock(self):
        game = self.make(directory=self.directory.name)
        game.choose_move()
        before = game.clock.remaining
        game.apply_opponent_move("e7e5", entry_latency=6.0)
        game.choose_move()
        self.assertAlmostEqual(game.clock.remaining, before - 0.2 - 5.0 - 6.0 + 10.0)

    def repeat_position(self, game, times=2):
        for _ in range(times):
            for uci in ("g1f3", "g8f6", "f3g1", "f6g8"):
                game.board.push_uci(uci)

    def test_threefold_repetition_does_not_end_the_game(self):
        game = self.make(directory=self.directory.name)
        self.repeat_position(game)
        self.assertTrue(game.board.can_claim_threefold_repetition())
        self.assertIsNone(game.outcome())

    def test_fifty_move_rule_does_not_end_the_game(self):
        game = self.make(directory=self.directory.name)
        game.set_fen("4k3/8/8/8/8/8/4P3/4K2R w - - 100 80")
        self.assertIsNone(game.outcome())

    def test_draw_notice_is_reported_once_and_resets(self):
        game = self.make(directory=self.directory.name)
        self.assertIsNone(game.new_draw_notice())
        self.repeat_position(game)
        self.assertIsNotNone(game.new_draw_notice())
        self.assertIsNone(game.new_draw_notice())
        game.set_fen(chess.STARTING_FEN)
        self.assertIsNone(game.new_draw_notice())
        self.repeat_position(game)
        self.assertIsNotNone(game.new_draw_notice())

    def test_checkmate_still_ends_the_game(self):
        game = self.make(directory=self.directory.name)
        for uci in ("f2f3", "e7e5", "g2g4", "d8h4"):
            game.board.push_uci(uci)
        self.assertIsNotNone(game.outcome())

    def test_stalemate_still_ends_the_game(self):
        game = self.make(directory=self.directory.name)
        game.set_fen("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
        self.assertIsNotNone(game.outcome())

    def test_keeps_choosing_moves_after_repetition(self):
        game = self.make(directory=self.directory.name)
        self.repeat_position(game)
        legal = set(game.board.legal_moves)
        plies = len(game.board.move_stack)
        result = game.choose_move()
        self.assertIn(result.move, legal)
        self.assertEqual(len(game.board.move_stack), plies + 1)

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


class PonderTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)

    def make(self, ponder):
        engine = StubEngine()
        game = build_game(engine, directory=self.directory.name)
        game.config.ponder = ponder
        self.addCleanup(game.logger.close)
        return game, engine

    def test_ponders_on_predicted_reply_when_enabled(self):
        game, engine = self.make(True)
        first = next(iter(game.board.legal_moves))
        board = game.board.copy()
        board.push(first)
        reply = next(iter(board.legal_moves))
        game.engine.search = lambda b, budget, manager, on_info=None: SearchResult(
            first, 10, 1000, "+0.10", [first, reply], 0.2, "engine"
        )
        game.choose_move()
        board.push(reply)
        self.assertEqual(engine.pondered, [board.fen()])

    def test_ponders_on_current_position_after_book_move(self):
        game, engine = self.make(True)
        first = next(iter(game.board.legal_moves))
        game.engine.search = lambda b, budget, manager, on_info=None: SearchResult(
            first, 0, 0, "n/a", [first], 0.0, "book"
        )
        game.choose_move()
        self.assertEqual(engine.pondered, [game.board.fen()])

    def test_does_not_ponder_when_disabled(self):
        game, engine = self.make(False)
        first = next(iter(game.board.legal_moves))
        game.engine.search = lambda b, budget, manager, on_info=None: SearchResult(
            first, 10, 1000, "+0.10", [first, first], 0.2, "engine"
        )
        game.choose_move()
        self.assertEqual(engine.pondered, [])

    def test_opponent_move_stops_pondering(self):
        game, engine = self.make(True)
        game.board.push_uci("e2e4")
        before = engine.stops
        game.apply_opponent_move("e7e5")
        self.assertEqual(engine.stops, before + 1)


class ScriptedEngine:
    name = "Scripted"

    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def search(self, board, budget, manager, on_info=None, root_moves=None):
        self.calls.append(root_moves)
        return self.results.pop(0)

    def start_ponder(self, board):
        pass

    def stop_ponder(self):
        pass


def scripted(uci, white_cp, elapsed=1.0):
    move = chess.Move.from_uci(uci)
    return SearchResult(move, 20, 1000, f"{white_cp / 100:+.2f}", [move], elapsed, "engine", centipawns=white_cp)


class RepetitionAvoidanceTest(unittest.TestCase):
    CYCLE = ("g1f3", "g8f6", "f3g1", "f6g8")

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)

    def make(self, results, color, plies=()):
        engine = ScriptedEngine(results)
        game = build_game(engine, color=color, directory=self.directory.name)
        self.addCleanup(game.logger.close)
        for uci in plies:
            game.board.push_uci(uci)
        return game, engine

    def test_avoids_threefold_when_better(self):
        plies = self.CYCLE + self.CYCLE[:3]
        game, engine = self.make([scripted("f6g8", -80), scripted("d7d6", -60)], chess.BLACK, plies)
        result = game.choose_move()
        self.assertEqual(result.move.uci(), "d7d6")
        self.assertEqual(result.source, "engine-norep")
        self.assertEqual(len(engine.calls), 2)
        self.assertNotIn(chess.Move.from_uci("f6g8"), engine.calls[1])
        self.assertAlmostEqual(result.elapsed, 2.0)

    def test_accepts_threefold_when_not_better(self):
        plies = self.CYCLE + self.CYCLE[:3]
        game, engine = self.make([scripted("f6g8", -10)], chess.BLACK, plies)
        result = game.choose_move()
        self.assertEqual(result.move.uci(), "f6g8")
        self.assertEqual(len(engine.calls), 1)

    def test_keeps_repetition_when_alternative_loses_the_edge(self):
        plies = self.CYCLE + self.CYCLE[:3]
        game, engine = self.make([scripted("f6g8", -80), scripted("d7d6", -5)], chess.BLACK, plies)
        result = game.choose_move()
        self.assertEqual(result.move.uci(), "f6g8")
        self.assertEqual(len(engine.calls), 2)
        self.assertAlmostEqual(result.elapsed, 2.0)

    def test_strong_edge_also_avoids_second_occurrence(self):
        plies = self.CYCLE[:3]
        game, engine = self.make([scripted("f6g8", -150), scripted("d7d6", -140)], chess.BLACK, plies)
        result = game.choose_move()
        self.assertEqual(result.move.uci(), "d7d6")
        self.assertEqual(result.source, "engine-norep")

    def test_moderate_edge_allows_second_occurrence(self):
        plies = self.CYCLE[:3]
        game, engine = self.make([scripted("f6g8", -50)], chess.BLACK, plies)
        result = game.choose_move()
        self.assertEqual(result.move.uci(), "f6g8")
        self.assertEqual(len(engine.calls), 1)

    def test_avoids_fifty_move_draw_when_better(self):
        game, engine = self.make([scripted("a1b1", 300), scripted("a2a4", 290)], chess.WHITE)
        game.set_fen("4k3/8/8/8/8/8/P7/R3K3 w - - 99 80")
        result = game.choose_move()
        self.assertEqual(result.move.uci(), "a2a4")
        self.assertEqual(result.source, "engine-norep")

    def test_keeps_move_when_every_alternative_also_draws(self):
        game, engine = self.make([scripted("a1b1", 300)], chess.WHITE)
        game.set_fen("4k3/8/8/8/8/8/8/R3K3 w - - 99 80")
        result = game.choose_move()
        self.assertEqual(result.move.uci(), "a1b1")
        self.assertEqual(len(engine.calls), 1)

    def test_never_overrides_forced_mate(self):
        plies = self.CYCLE + self.CYCLE[:3]
        game, engine = self.make([scripted("f6g8", -100000)], chess.BLACK, plies)
        result = game.choose_move()
        self.assertEqual(result.move.uci(), "f6g8")
        self.assertEqual(len(engine.calls), 1)

    def test_logs_the_swap(self):
        plies = self.CYCLE + self.CYCLE[:3]
        game, engine = self.make([scripted("f6g8", -80), scripted("d7d6", -60)], chess.BLACK, plies)
        game.choose_move()
        game.logger.close()
        self.assertIn("repeticao evitada", game.logger.path.read_text(encoding="utf-8"))


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
