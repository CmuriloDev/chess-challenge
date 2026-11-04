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


def default_book_path() -> Path | None:
    folder = ROOT / "data" / "book"
    preferred = folder / "komodo.bin"
    if preferred.exists():
        return preferred
    found = sorted(folder.glob("*.bin")) if folder.exists() else []
    return found[0] if found else None


def default_syzygy_path() -> Path | None:
    folder = ROOT / "data" / "syzygy"
    if folder.exists() and any(folder.glob("*.rtbw")):
        return folder
    return None


def default_threads() -> int:
    return max(1, (os.cpu_count() or 2) - 2)


@dataclass
class Config:
    engine_path: Path = field(default_factory=default_engine_path)
    threads: int = field(default_factory=default_threads)
    hash_mb: int = 8192
    book_path: Path | None = field(default_factory=default_book_path)
    syzygy_path: Path | None = field(default_factory=default_syzygy_path)
    log_dir: Path = ROOT / "logs"
    total_time: float = 900.0
    increment: float = 10.0
    move_overhead: float = 2.0
    entry_estimate: float = 3.0
    ponder: bool = True
    book_max_plies: int = 10
    tablebase_max_pieces: int = 5
