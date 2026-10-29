"""Benchmark all eight sequential sorting algorithms on identical datasets."""
from random import Random
from statistics import median
from time import perf_counter

from .merge_sort import merge_sort
from .bubble_sort import bubble_sort
from .insertion_sort import insertion_sort
from .selection_sort import selection_sort
from .quick_sort import quick_sort
from .heap_sort import heap_sort
from .shell_sort import shell_sort
from .counting_sort import counting_sort

ALGORITHMS = {
    "Merge Sort": merge_sort,
    "Bubble Sort": bubble_sort,
    "Insertion Sort": insertion_sort,
    "Selection Sort": selection_sort,
    "Quick Sort": quick_sort,
    "Heap Sort": heap_sort,
    "Shell Sort": shell_sort,
    "Counting Sort": counting_sort,
}


def _time_ms(function, data):
    start = perf_counter()
    result = function(data.copy())
    return result, (perf_counter() - start) * 1000


def run_benchmark(numbers=None, sizes=None, repetitions=3):
    """Return one row per input size with timing for each algorithm.

    Quadratic algorithms use smaller input sizes to keep the UI responsive.
    Timings are medians and all algorithms receive identical input per size.
    """
    sizes = sizes or [100, 250, 500, 1000]
    repetitions = max(1, min(5, int(repetitions)))
    rng = Random(42)
    rows = []

    for raw_size in sizes:
        size = int(raw_size)
        if size < 1 or size > 5000:
            continue
        data = [rng.randint(-10000, 10000) for _ in range(size)]
        expected = sorted(data)
        timings = {}
        correct = {}

        for name, function in ALGORITHMS.items():
            # Avoid long waits on O(n^2) algorithms for large datasets.
            if name in ("Bubble Sort", "Insertion Sort", "Selection Sort") and size > 1000:
                timings[name] = None
                correct[name] = None
                continue
            samples = []
            result_ok = True
            for _ in range(repetitions):
                result, elapsed = _time_ms(function, data)
                samples.append(elapsed)
                result_ok = result_ok and result == expected
            timings[name] = round(median(samples), 3)
            correct[name] = result_ok

        rows.append({"size": size, "algorithm_ms": timings, "correct": correct,
                     "same_result": all(v is not False for v in correct.values())})
    return rows
