from typing import Any, Mapping

import chess


class SearchTracker:
    def __init__(self, turn: chess.Color) -> None:
        self.turn = turn
        self.best_move: chess.Move | None = None
        self.last_change = 0.0
        self.depth = 0
        self.scores: list[int] = []
        self.mate = False

    def update(self, info: Mapping[str, Any], elapsed: float) -> None:
        depth = info.get("depth", 0)
        pv = info.get("pv")
        score = info.get("score")
        if not pv or score is None or depth <= self.depth:
            return
        self.depth = depth
        move = pv[0]
        if move != self.best_move:
            self.best_move = move
            self.last_change = elapsed
        pov = score.pov(self.turn)
        self.mate = pov.is_mate() and (pov.mate() or 0) > 0
        self.scores.append(pov.score(mate_score=100000))

    @property
    def drop(self) -> int:
        if not self.scores:
            return 0
        return max(self.scores[-6:]) - self.scores[-1]
