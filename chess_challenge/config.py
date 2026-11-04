import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def default_engine_path() -> Path:
    env = os.environ.get("STOCKFISH_PATH")
    if env:
        return Path(env)
    name = "stockfish.exe" if os.name == "nt" else "stockfish"
    local = ROOT / "bin" / name
    if local.exists():
        return local
    found = shutil.which("stockfish")
    if found:
        return Path(found)
    return local


def default_threads() -> int:
    return max(1, (os.cpu_count() or 2) - 2)


@dataclass
class Config:
    engine_path: Path = field(default_factory=default_engine_path)
    threads: int = field(default_factory=default_threads)
    hash_mb: int = 8192
    book_path: Path | None = None
    syzygy_path: Path | None = None
    log_dir: Path = ROOT / "logs"
    total_time: float = 900.0
    increment: float = 10.0
    move_overhead: float = 5.0
    ponder: bool = True
    book_max_plies: int = 10
    tablebase_max_pieces: int = 5
