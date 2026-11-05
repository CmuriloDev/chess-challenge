import unittest

import chess

from chess_challenge.timemanager import PonderCredit, TimeBudget, TimeManager, game_phase
from chess_challenge.tracker import SearchTracker


def make_tracker(depth, last_change, scores, mate=False, best_move=None):
    tracker = SearchTracker(chess.WHITE)
    tracker.best_move = best_move
    tracker.depth = depth
    tracker.last_change = last_change
    tracker.scores = list(scores)
    tracker.mate = mate
    return tracker


class GamePhaseTest(unittest.TestCase):
    def test_start_position_is_full_phase(self):
        self.assertEqual(game_phase(chess.Board()), 1.0)

    def test_bare_kings_is_zero(self):
        self.assertEqual(game_phase(chess.Board("8/8/4k3/8/8/4K3/8/8 w - - 0 1")), 0.0)


class BudgetTest(unittest.TestCase):
    def setUp(self):
        self.manager = TimeManager(increment=10.0, overhead=5.0)

    def test_hard_is_not_below_soft(self):
        for remaining in (900, 400, 120, 40, 14, 3):
            budget = self.manager.budget(chess.Board(), remaining)
            self.assertGreaterEqual(budget.hard, budget.soft)

    def test_less_time_means_smaller_budget(self):
        board = chess.Board()
        rich = self.manager.budget(board, 900)
        poor = self.manager.budget(board, 100)
        self.assertGreater(rich.soft, poor.soft)

    def test_never_spends_more_than_remaining(self):
        for remaining in (900, 200, 30, 10, 2):
            budget = self.manager.budget(chess.Board(), remaining)
            self.assertLess(budget.hard, remaining)

    def test_panic_mode_is_short(self):
        budget = self.manager.budget(chess.Board(), 8)
        self.assertLessEqual(budget.hard, 2.0)

    def test_endgame_allots_at_least_as_much_per_move_as_middlegame(self):
        middlegame = self.manager.budget(chess.Board(), 500)
        endgame = self.manager.budget(chess.Board("8/5pk1/6p1/8/8/6P1/5PK1/8 w - - 0 40"), 500)
        self.assertGreater(middlegame.soft, 0)
        self.assertGreaterEqual(endgame.soft, middlegame.soft)


class CreditTest(unittest.TestCase):
    def setUp(self):
        self.manager = TimeManager(increment=10.0, overhead=5.0)
        self.budget = TimeBudget(soft=10.0, hard=25.0)
        self.move = chess.Move.from_uci("e2e4")
        self.credit = PonderCredit(seconds=20.0, depth=24, move=self.move)

    def tracker(self, depth=22, best_move=None, last_change=0.3, scores=(30, 30, 31)):
        return make_tracker(depth, last_change, scores, best_move=best_move or self.move)

    def test_without_credit_stable_search_keeps_going(self):
        self.assertFalse(self.manager.should_stop(1.0, self.budget, self.tracker()))

    def test_credit_lets_a_confirmed_search_stop_early(self):
        self.assertTrue(self.manager.should_stop(1.0, self.budget, self.tracker(), self.credit))

    def test_no_credit_when_best_move_differs(self):
        other = chess.Move.from_uci("d2d4")
        tracker = self.tracker(best_move=other)
        self.assertFalse(self.manager.should_stop(1.0, self.budget, tracker, self.credit))

    def test_no_credit_before_search_catches_up_in_depth(self):
        self.assertFalse(self.manager.should_stop(1.0, self.budget, self.tracker(depth=15), self.credit))

    def test_no_credit_for_shallow_ponder(self):
        shallow = PonderCredit(seconds=20.0, depth=8, move=self.move)
        self.assertFalse(self.manager.should_stop(1.0, self.budget, self.tracker(depth=11), shallow))

    def test_no_credit_in_the_first_instants(self):
        self.assertFalse(self.manager.should_stop(0.1, self.budget, self.tracker(), self.credit))

    def test_unstable_search_still_needs_more_time(self):
        tracker = make_tracker(22, 0.9, [80, 60, 20], best_move=self.move)
        self.assertFalse(self.manager.should_stop(1.0, self.budget, tracker, self.credit))
        self.assertTrue(self.manager.should_stop(6.5, self.budget, tracker, self.credit))

    def test_credit_never_beats_the_hard_limit(self):
        self.assertTrue(self.manager.should_stop(25.0, self.budget, self.tracker(), None))


class StopTest(unittest.TestCase):
    def setUp(self):
        self.manager = TimeManager(increment=10.0, overhead=5.0)
        self.budget = TimeBudget(soft=10.0, hard=25.0)

    def test_stops_at_hard_limit(self):
        tracker = make_tracker(30, 0.0, [20, 20])
        self.assertTrue(self.manager.should_stop(25.0, self.budget, tracker))

    def test_keeps_going_before_soft_when_neutral(self):
        tracker = make_tracker(20, 4.0, [20, 20, 20])
        self.assertFalse(self.manager.should_stop(5.0, self.budget, tracker))

    def test_stable_search_stops_early(self):
        tracker = make_tracker(20, 0.5, [30, 30, 31, 30])
        self.assertTrue(self.manager.should_stop(6.5, self.budget, tracker))

    def test_unstable_search_extends_past_soft(self):
        tracker = make_tracker(20, 9.5, [80, 60, 20])
        self.assertFalse(self.manager.should_stop(11.0, self.budget, tracker))
        self.assertTrue(self.manager.should_stop(16.5, self.budget, tracker))

    def test_found_mate_stops_quickly(self):
        tracker = make_tracker(12, 0.3, [100000], mate=True)
        self.assertTrue(self.manager.should_stop(0.5, self.budget, tracker))


if __name__ == "__main__":
    unittest.main()
