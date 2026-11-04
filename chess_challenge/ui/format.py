import math

import chess

MATE_THRESHOLD = 90000
EVAL_SCALE = 400.0


def format_clock(seconds: float) -> str:
    minutes, secs = divmod(int(max(0.0, seconds)), 60)
    return f"{minutes}:{secs:02d}"


def format_count(value: int) -> str:
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}G"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.0f}k"
    return str(value)


def eval_fraction(centipawns: int) -> float:
    if centipawns >= MATE_THRESHOLD:
        return 1.0
    if centipawns <= -MATE_THRESHOLD:
        return 0.0
    return 1.0 / (1.0 + math.exp(-centipawns / EVAL_SCALE))


def pv_text(board: chess.Board, pv: list[chess.Move], limit: int = 10) -> str:
    probe = board.copy()
    parts: list[str] = []
    for index, move in enumerate(pv[:limit]):
        if move not in probe.legal_moves:
            break
        number = probe.fullmove_number
        if probe.turn == chess.WHITE:
            parts.append(f"{number}. {probe.san(move)}")
        elif index == 0:
            parts.append(f"{number}... {probe.san(move)}")
        else:
            parts.append(probe.san(move))
        probe.push(move)
    return " ".join(parts)


def move_list_rows(board: chess.Board) -> list[tuple[int, str, str]]:
    replay = chess.Board(board.root().fen())
    rows: list[tuple[int, str, str]] = []
    for move in board.move_stack:
        number = replay.fullmove_number
        san = replay.san(move)
        if replay.turn == chess.WHITE:
            rows.append((number, san, ""))
        elif rows and rows[-1][0] == number:
            rows[-1] = (number, rows[-1][1], san)
        else:
            rows.append((number, "...", san))
        replay.push(move)
    return rows


def square_at(column: int, row: int, flipped: bool) -> chess.Square:
    if flipped:
        return chess.square(7 - column, row)
    return chess.square(column, 7 - row)


def cell_of(square: chess.Square, flipped: bool) -> tuple[int, int]:
    file, rank = chess.square_file(square), chess.square_rank(square)
    if flipped:
        return 7 - file, rank
    return file, 7 - rank
