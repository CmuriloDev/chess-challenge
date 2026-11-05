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
CREDIT_SHARE = 0.8
CREDIT_MIN_DEPTH = 12
CREDIT_DEPTH_SLACK = 2
CREDIT_MIN_ELAPSED = 0.25


@dataclass(frozen=True)
class TimeBudget:
    soft: float
    hard: float


@dataclass(frozen=True)
class PonderCredit:
    seconds: float
    depth: int
    move: chess.Move


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

    def should_stop(
        self,
        elapsed: float,
        budget: TimeBudget,
        tracker: SearchTracker,
        credit: PonderCredit | None = None,
    ) -> bool:
        if elapsed >= budget.hard:
            return True
        if tracker.mate and tracker.depth >= MATE_MIN_DEPTH and elapsed >= MIN_SOFT:
            return True
        confirmed = self._confirmed(elapsed, tracker, credit)
        target = min(budget.soft * self._factor(elapsed, budget, tracker, confirmed), budget.hard)
        bonus = min(credit.seconds * CREDIT_SHARE, budget.soft) if confirmed and credit else 0.0
        return elapsed + bonus >= target

    def _confirmed(
        self, elapsed: float, tracker: SearchTracker, credit: PonderCredit | None
    ) -> bool:
        if credit is None or elapsed < CREDIT_MIN_ELAPSED:
            return False
        if credit.depth < CREDIT_MIN_DEPTH or tracker.best_move != credit.move:
            return False
        return tracker.depth >= credit.depth - CREDIT_DEPTH_SLACK

    def _factor(
        self,
        elapsed: float,
        budget: TimeBudget,
        tracker: SearchTracker,
        confirmed: bool = False,
    ) -> float:
        if tracker.depth < MIN_DEPTH:
            return 1.0
        since_change = elapsed - tracker.last_change
        recent = since_change < RECENT_CHANGE_RATIO * budget.soft and not confirmed
        if tracker.drop >= DROP_THRESHOLD or recent:
            return UNSTABLE_FACTOR
        steady = confirmed or (elapsed > 0 and since_change / elapsed >= STABLE_RATIO)
        if tracker.drop <= STABLE_DROP and steady:
            return STABLE_FACTOR
        return 1.0
