import tempfile
import unittest
from pathlib import Path

import chess

from chess_challenge.engine import SearchResult
from chess_challenge.logger import GameLogger


class LoggerTest(unittest.TestCase):
    def test_engine_move_line_has_required_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            logger = GameLogger(Path(directory))
            move = chess.Move.from_uci("e2e4")
            reply = chess.Move.from_uci("e7e5")
            result = SearchResult(move, 22, 1234567, "+0.30", [move, reply], 3.2, "engine")
            logger.engine_move(1, chess.WHITE, result, 880.0)
            logger.close()
            text = logger.path.read_text(encoding="utf-8")
        for field in (
            "move=1",
            "color=white",
            "uci=e2e4",
            "depth=22",
            "nodes=1234567",
            "eval=+0.30",
            "pv=e2e4 e7e5",
            "time=3.200s",
        ):
            self.assertIn(field, text)

    def test_opponent_move_line(self):
        with tempfile.TemporaryDirectory() as directory:
            logger = GameLogger(Path(directory))
            logger.opponent_move(1, chess.BLACK, chess.Move.from_uci("e7e5"))
            logger.close()
            text = logger.path.read_text(encoding="utf-8")
        self.assertIn("color=black", text)
        self.assertIn("uci=e7e5", text)


if __name__ == "__main__":
    unittest.main()
