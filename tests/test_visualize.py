import random
import unittest

from src.sorting.visualize import (
    ALGORITHM_LIMITS, MAX_EVENTS, MAX_SNAPSHOT_CELLS, MIN_EVENTS,
    event_budget, visualized_sort,
)


class VisualizedSortTests(unittest.TestCase):
    def test_every_algorithm_sorts_and_reports_events(self):
        rng = random.Random(5)
        data = [rng.randint(-30, 30) for _ in range(40)]

        for key in ALGORITHM_LIMITS:
            with self.subTest(algorithm=key):
                result, events, info = visualized_sort(data, key)
                self.assertEqual(result, sorted(data))
                self.assertEqual(events[0]["kind"], "start")
                self.assertEqual(events[-1]["kind"], "finish")
                self.assertEqual(events[-1]["values"], sorted(data))
                self.assertGreaterEqual(info["total_steps"], 0)

    def test_input_is_not_mutated(self):
        data = [3, 1, 2]
        visualized_sort(data, "bubble_sort")
        self.assertEqual(data, [3, 1, 2])

    def test_small_input_records_every_step(self):
        _, events, info = visualized_sort([3, 1, 2], "bubble_sort")
        self.assertEqual(info["stride"], 1)
        # start + finish + every step
        self.assertEqual(len(events), info["total_steps"] + 2)

    def test_events_are_bounded_for_worst_case_input(self):
        # 1000 reversed numbers is ~1M bubble-sort steps; recording all of
        # them used to need gigabytes of memory.
        data = list(range(1000, 0, -1))
        result, events, info = visualized_sort(data, "bubble_sort")

        self.assertEqual(result, sorted(data))
        self.assertGreater(info["total_steps"], 900_000)
        self.assertGreater(info["stride"], 1)
        self.assertLessEqual(len(events) * len(data), MAX_SNAPSHOT_CELLS * 1.05)

    def test_event_budget_limits(self):
        self.assertEqual(event_budget(1), MAX_EVENTS)
        self.assertEqual(event_budget(10 ** 9), MIN_EVENTS)
        self.assertLessEqual(event_budget(1000) * 1000, MAX_SNAPSHOT_CELLS)

    def test_quick_sort_survives_sorted_and_equal_input(self):
        # Used to hit Python's recursion limit on already sorted input.
        for data in (list(range(2000)), [7] * 500, list(range(2000, 0, -1))):
            with self.subTest(first=data[0], size=len(data)):
                result, _, _ = visualized_sort(data, "quick_sort")
                self.assertEqual(result, sorted(data))

    def test_counting_sort_rejects_huge_range(self):
        with self.assertRaises(ValueError):
            visualized_sort([0, 10 ** 9], "counting_sort")

    def test_unknown_algorithm(self):
        with self.assertRaises(ValueError):
            visualized_sort([2, 1], "nope")


if __name__ == "__main__":
    unittest.main()
