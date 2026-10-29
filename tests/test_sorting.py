import random
import unittest

from src.sorting.merge_sort import merge_sort
from src.sorting.parallel_sort import parallel_merge_sort
from src.sorting.bubble_sort import bubble_sort
from src.sorting.insertion_sort import insertion_sort
from src.sorting.selection_sort import selection_sort
from src.sorting.quick_sort import quick_sort
from src.sorting.heap_sort import heap_sort
from src.sorting.shell_sort import shell_sort
from src.sorting.counting_sort import counting_sort
from src.sorting.benchmark import run_benchmark

ALL_ALGORITHMS = [
    merge_sort, bubble_sort, insertion_sort, selection_sort,
    quick_sort, heap_sort, shell_sort, counting_sort,
]


class SortingTests(unittest.TestCase):
    def test_sequential_sort(self):
        self.assertEqual(merge_sort([4, 1, 3, 2]), [1, 2, 3, 4])

    def test_parallel_sort(self):
        result, events = parallel_merge_sort([4, -1, 3, 3, 0, 9])
        self.assertEqual(result, [-1, 0, 3, 3, 4, 9])
        self.assertTrue(any(event["kind"] == "merge" for event in events))

    def test_empty_and_single(self):
        self.assertEqual(merge_sort([]), [])
        self.assertEqual(parallel_merge_sort([5])[0], [5])

    def test_does_not_mutate_input(self):
        values = [3, 1, 2]
        merge_sort(values)
        self.assertEqual(values, [3, 1, 2])


class AllAlgorithmsTests(unittest.TestCase):
    def test_edge_cases(self):
        cases = [[], [1], [2, 1], [5] * 7, [3, -3, 0], list(range(20)),
                 list(range(20, 0, -1))]
        for function in ALL_ALGORITHMS:
            for case in cases:
                with self.subTest(algorithm=function.__name__, case=case):
                    self.assertEqual(function(case.copy()), sorted(case))

    def test_random_inputs(self):
        rng = random.Random(7)
        for function in ALL_ALGORITHMS:
            for _ in range(100):
                data = [rng.randint(-50, 50) for _ in range(rng.randint(0, 60))]
                with self.subTest(algorithm=function.__name__):
                    self.assertEqual(function(data.copy()), sorted(data))

    def test_input_is_not_mutated(self):
        for function in ALL_ALGORITHMS:
            data = [3, 1, 2]
            function(data)
            self.assertEqual(data, [3, 1, 2], function.__name__)

    def test_counting_sort_rejects_huge_range(self):
        with self.assertRaises(ValueError):
            counting_sort([0, 10 ** 9])


class ParallelAndBenchmarkTests(unittest.TestCase):
    def test_untraced_parallel_matches_and_has_no_events(self):
        data = [random.Random(1).randint(-99, 99) for _ in range(500)]
        result, events = parallel_merge_sort(data, trace=False)
        self.assertEqual(result, sorted(data))
        self.assertEqual(events, [])

    def test_untraced_parallel_edge_cases(self):
        self.assertEqual(parallel_merge_sort([], trace=False)[0], [])
        self.assertEqual(parallel_merge_sort([5], trace=False)[0], [5])
        self.assertEqual(parallel_merge_sort([2, 1], trace=False)[0], [1, 2])

    def test_benchmark_rows(self):
        rows = run_benchmark(sizes=[10, 50], repetitions=1)
        self.assertEqual([row["size"] for row in rows], [10, 50])
        for row in rows:
            self.assertTrue(row["same_result"])
            for key in ("sequential_ms", "parallel_ms", "parallel_traced_ms",
                        "sequential_time", "parallel_time"):
                self.assertIn(key, row)


if __name__ == "__main__":
    unittest.main()
