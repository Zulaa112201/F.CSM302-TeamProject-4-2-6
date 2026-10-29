
from concurrent.futures import ThreadPoolExecutor
from threading import current_thread, Lock
from time import perf_counter

from .merge_sort import merge, merge_sort


def _elapsed(started_at):
    return round((perf_counter() - started_at) * 1000, 3)


def _parallel_merge_sort_plain(numbers):
    """Two-thread merge sort without event tracing (for fair timing)."""
    if len(numbers) <= 1:
        return list(numbers)

    middle = len(numbers) // 2

    with ThreadPoolExecutor(
        max_workers=2,
        thread_name_prefix="SortWorker"
    ) as executor:
        left_future = executor.submit(merge_sort, numbers[:middle])
        right_future = executor.submit(merge_sort, numbers[middle:])
        left_sorted = left_future.result()
        right_sorted = right_future.result()

    return merge(left_sorted, right_sorted)


def parallel_merge_sort(numbers, on_event=None, trace=True):
    """Sort with two worker threads.

    With ``trace=True`` (default) every merge is recorded as an event that
    carries a full snapshot of the array, which is useful for visualising
    thread activity but adds a lot of overhead. Pass ``trace=False`` to
    measure the sorting itself; the returned event list is then empty.
    """
    numbers = list(numbers)

    if not trace:
        return _parallel_merge_sort_plain(numbers), []

    started_at = perf_counter()
    events = []
    events_lock = Lock()

    def emit(event):
        with events_lock:
            events.append(event)

        if on_event is not None:
            on_event(event)

    if len(numbers) <= 1:
        event = {
            "kind": "merge",
            "thread": "MainThread",
            "task": "Array already sorted",
            "at": _elapsed(started_at),
            "values": numbers.copy(),
        }
        emit(event)
        return numbers, events

    def merge_sort_trace(values, snapshot, offset, task_name):
        values = list(values)

        if len(values) <= 1:
            return values

        middle = len(values) // 2

        left = merge_sort_trace(
            values[:middle], snapshot, offset, task_name
        )
        right = merge_sort_trace(
            values[middle:], snapshot, offset + middle, task_name
        )

        result = merge(left, right)

        snapshot[offset:offset + len(result)] = result

        emit({
            "kind": "step",
            "thread": current_thread().name,
            "task": f"{task_name}: merge {len(result)} items",
            "at": _elapsed(started_at),
            "values": snapshot.copy(),
        })

        return result

    def worker(values, offset, task_name):
        thread_name = current_thread().name
        snapshot = numbers.copy()

        emit({
            "kind": "start",
            "thread": thread_name,
            "task": task_name,
            "at": _elapsed(started_at),
            "values": snapshot.copy(),
        })

        result = merge_sort_trace(
            values, snapshot, offset, task_name
        )

        snapshot[offset:offset + len(result)] = result

        emit({
            "kind": "finish",
            "thread": thread_name,
            "task": task_name,
            "at": _elapsed(started_at),
            "values": snapshot.copy(),
        })

        return result

    middle = len(numbers) // 2

    with ThreadPoolExecutor(
        max_workers=2,
        thread_name_prefix="SortWorker"
    ) as executor:
        left_future = executor.submit(
            worker, numbers[:middle], 0, "Sort left half"
        )
        right_future = executor.submit(
            worker, numbers[middle:], middle, "Sort right half"
        )

        left_sorted = left_future.result()
        right_sorted = right_future.result()

    result = merge(left_sorted, right_sorted)

    emit({
        "kind": "merge",
        "thread": "MainThread",
        "task": "Final merge",
        "at": _elapsed(started_at),
        "values": result.copy(),
    })

    return result, events
