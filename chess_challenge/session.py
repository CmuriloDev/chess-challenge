from contextlib import contextmanager
from typing import Iterator

import chess

from .book import Book
from .clock import Clock
from .config import Config
from .engine import Engine
from .game import Game
from .logger import GameLogger, color_name
from .timemanager import TimeManager


@contextmanager
def open_game(config: Config, color: chess.Color) -> Iterator[Game]:
    book = Book(config.book_path, config.book_max_plies)
    with Engine(config) as engine:
        logger = GameLogger(config.log_dir)
        try:
            logger.header(
                engine=engine.name,
                color=color_name(color),
                threads=config.threads,
                hash_mb=config.hash_mb,
                book=config.book_path,
                syzygy=config.syzygy_path,
                time=config.total_time,
                increment=config.increment,
                overhead=config.move_overhead,
                entry_estimate=config.entry_estimate,
                ponder=config.ponder,
            )
            clock = Clock(
                config.total_time,
                config.increment,
                config.move_overhead,
                config.entry_estimate,
            )
            manager = TimeManager(config.increment, config.move_overhead)
            yield Game(config, engine, color, logger, clock, manager, book)
        finally:
            logger.close()
