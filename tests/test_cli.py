import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import chess

from chess_challenge.cli import build_parser, config_from_args, parse_color
from chess_challenge.clock import Clock, parse_clock
from chess_challenge.config import ROOT, Config


class ClockTest(unittest.TestCase):
    def test_parse_clock_formats(self):
        self.assertEqual(parse_clock("15:00"), 900.0)
        self.assertEqual(parse_clock("12:34"), 754.0)
        self.assertEqual(parse_clock("754"), 754.0)

    def test_parse_clock_rejects_garbage(self):
        with self.assertRaises(ValueError):
            parse_clock("abc")

    def test_spend_applies_overhead_and_increment(self):
        clock = Clock(900.0, 10.0, 5.0)
        clock.spend(20.0)
        self.assertEqual(clock.remaining, 885.0)

    def test_clock_never_goes_negative(self):
        clock = Clock(3.0, 0.0, 5.0)
        clock.spend(10.0)
        self.assertEqual(clock.remaining, 0.0)

    def test_set_and_format(self):
        clock = Clock(900.0, 10.0, 5.0)
        clock.set(754)
        self.assertEqual(str(clock), "12:34")


class ArgsTest(unittest.TestCase):
    def test_color_aliases(self):
        self.assertEqual(parse_color("brancas"), chess.WHITE)
        self.assertEqual(parse_color("Black"), chess.BLACK)

    def test_config_from_args(self):
        args = build_parser().parse_args(
            ["--color", "white", "--threads", "3", "--hash", "256", "--time", "5:00", "--no-ponder"]
        )
        config = config_from_args(args)
        self.assertEqual(config.threads, 3)
        self.assertEqual(config.hash_mb, 256)
        self.assertEqual(config.total_time, 300.0)
        self.assertFalse(config.ponder)


@unittest.skipUnless(Config().engine_path.exists(), "stockfish binary not available")
class CliSmokeTest(unittest.TestCase):
    def test_plays_a_move_and_logs_it(self):
        with tempfile.TemporaryDirectory() as directory:
            completed = subprocess.run(
                [
                    sys.executable, "-m", "chess_challenge",
                    "--color", "white", "--threads", "1", "--hash", "16",
                    "--time", "0:30", "--increment", "0", "--overhead", "0",
                    "--log-dir", directory,
                ],
                input="zzzz\ne7e5\nquit\n",
                capture_output=True,
                text=True,
                cwd=ROOT,
                timeout=60,
            )
            logs = list(Path(directory).glob("*.log"))
            self.assertEqual(len(logs), 1)
            text = logs[0].read_text(encoding="utf-8")
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout.count("ANUNCIE"), 2)
        self.assertIn("invalido", completed.stdout)
        self.assertIn("uci=e7e5", text)
        self.assertIn("color=white", text)


if __name__ == "__main__":
    unittest.main()
