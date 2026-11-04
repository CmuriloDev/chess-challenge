from dataclasses import dataclass

import chess

from .tracker import SearchTracker

INITIAL_MATERIAL = 62
MIN_SOFT = 0.2
MIN_DEPTH = 10
MATE_MIN_DEPTH = 8
DROP_THRESHOLD = 40
STABLE_DROP = 10
UNSTABLE_FACTOR = 1.6
STABLE_FACTOR = 0.6
STABLE_RATIO = 0.6
RECENT_CHANGE_RATIO = 0.2
MAX_SOFT_SHARE = 0.10
MAX_HARD_SHARE = 0.25
HARD_MULTIPLIER = 2.5
PANIC_SOFT_SHARE = 0.05


@dataclass(frozen=True)
class TimeBudget:
    soft: float
    hard: float


def game_phase(board: chess.Board) -> float:
    values = (
        (chess.KNIGHT, 3),
        (chess.BISHOP, 3),
        (chess.ROOK, 5),
        (chess.QUEEN, 9),
    )
    material = 0
    for piece_type, value in values:
        material += value * (
            len(board.pieces(piece_type, chess.WHITE))
            + len(board.pieces(piece_type, chess.BLACK))
        )
    return min(1.0, material / INITIAL_MATERIAL)


class TimeManager:
    def __init__(self, increment: float, overhead: float, safety: float = 15.0) -> None:
        self.increment = increment
        self.overhead = overhead
        self.safety = safety

    def budget(
        self, board: chess.Board, remaining: float, overhead: float | None = None
    ) -> TimeBudget:
        overhead = self.overhead if overhead is None else overhead
        if remaining < self.safety:
            soft = max(0.1, remaining * PANIC_SOFT_SHARE)
            hard = max(soft, min(soft * 2.0, remaining * MAX_HARD_SHARE))
            return TimeBudget(soft, hard)
        moves_left = 20 + 25 * game_phase(board)
        usable = remaining - self.safety
        soft = usable / moves_left + (self.increment - overhead)
        soft = max(MIN_SOFT, min(soft, remaining * MAX_SOFT_SHARE))
        hard = max(soft, min(soft * HARD_MULTIPLIER, remaining * MAX_HARD_SHARE))
        return TimeBudget(soft, hard)

    def should_stop(self, elapsed: float, budget: TimeBudget, tracker: SearchTracker) -> bool:
        if elapsed >= budget.hard:
            return True
        if tracker.mate and tracker.depth >= MATE_MIN_DEPTH and elapsed >= MIN_SOFT:
            return True
        target = min(budget.soft * self._factor(elapsed, budget, tracker), budget.hard)
        return elapsed >= target

    def _factor(self, elapsed: float, budget: TimeBudget, tracker: SearchTracker) -> float:
        if tracker.depth < MIN_DEPTH:
            return 1.0
        since_change = elapsed - tracker.last_change
        if tracker.drop >= DROP_THRESHOLD or since_change < RECENT_CHANGE_RATIO * budget.soft:
            return UNSTABLE_FACTOR
        if tracker.drop <= STABLE_DROP and elapsed > 0 and since_change / elapsed >= STABLE_RATIO:
            return STABLE_FACTOR
        return 1.0
