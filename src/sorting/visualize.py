"""Step-by-step recording of sorting algorithms for the visualizer.

Recording a full copy of the array after every step costs
O(steps * n) memory, which for O(n^2) algorithms grows like O(n^3).
To keep memory bounded we run every algorithm twice:

1. a cheap *counting pass* that only counts the steps, and
2. a *recording pass* that stores a snapshot only for every
   ``stride``-th step (plus the first and last event).

The number of stored snapshots is capped so that
``events * len(array)`` never exceeds ``MAX_SNAPSHOT_CELLS``.
"""

from math import ceil
from time import perf_counter

from .counting_sort import check_range

MAX_EVENTS = 5000
MIN_EVENTS = 200
MAX_SNAPSHOT_CELLS = 2_000_000

# Largest input accepted per algorithm. O(n^2) algorithms get a lower
# limit because the counting pass still has to walk every step.
ALGORITHM_LIMITS = {
    "merge_sort": 5000,
    "heap_sort": 5000,
    "counting_sort": 5000,
    "shell_sort": 2000,
    "quick_sort": 2000,
    "bubble_sort": 1000,
    "insertion_sort": 1000,
    "selection_sort": 1000,
}


def event_budget(size):
    """Maximum number of snapshots we are willing to keep for `size` items."""
    return max(MIN_EVENTS, min(MAX_EVENTS, MAX_SNAPSHOT_CELLS // max(size, 1)))


def _execute(values, algorithm_key, record):
    """Run the algorithm in place on `values`, calling record(kind, task)."""
    n = len(values)

    if algorithm_key == "bubble_sort":
        for i in range(n):
            swapped = False
            for j in range(n - i - 1):
                record("step", f"{values[j]} ба {values[j + 1]} харьцуулах")
                if values[j] > values[j + 1]:
                    values[j], values[j + 1] = values[j + 1], values[j]
                    swapped = True
                    record("step", "Хоёр элементийн байрыг сольлоо")
            if not swapped:
                break

    elif algorithm_key == "insertion_sort":
        for i in range(1, n):
            key = values[i]
            j = i - 1
            while j >= 0 and values[j] > key:
                values[j + 1] = values[j]
                record("step", f"{key} утгад байр гаргаж байна")
                j -= 1
            values[j + 1] = key
            record("step", f"{key} зөв байрлалдаа орлоо")

    elif algorithm_key == "selection_sort":
        for i in range(n):
            minimum = i
            for j in range(i + 1, n):
                record("step", f"Хамгийн багыг хайж байна: {j}")
                if values[j] < values[minimum]:
                    minimum = j
            values[i], values[minimum] = values[minimum], values[i]
            record("step", f"{values[i]} утгыг {i} байрлалд тавилаа")

    elif algorithm_key == "quick_sort":
        def quick_sort_range(low, high):
            # Loop on the larger partition and recurse on the smaller one,
            # so recursion depth stays O(log n) even on sorted input.
            while low < high:
                middle = (low + high) // 2
                values[middle], values[high] = values[high], values[middle]
                pivot = values[high]
                record("step", f"Pivot = {pivot}")
                i = low - 1

                for j in range(low, high):
                    record("step", f"{values[j]} ба pivot {pivot}")
                    if values[j] <= pivot:
                        i += 1
                        values[i], values[j] = values[j], values[i]
                        record("step", "Pivot-ийн зүүн хэсгийг байгуулж байна")

                pivot_index = i + 1
                values[pivot_index], values[high] = values[high], values[pivot_index]
                record("step", f"Pivot {pivot} байрлалаа оллоо")

                if pivot_index - low < high - pivot_index:
                    quick_sort_range(low, pivot_index - 1)
                    low = pivot_index + 1
                else:
                    quick_sort_range(pivot_index + 1, high)
                    high = pivot_index - 1

        quick_sort_range(0, n - 1)

    elif algorithm_key == "heap_sort":
        def heapify(size, root):
            largest = root
            left = 2 * root + 1
            right = 2 * root + 2

            if left < size and values[left] > values[largest]:
                largest = left
            if right < size and values[right] > values[largest]:
                largest = right

            if largest != root:
                values[root], values[largest] = values[largest], values[root]
                record("step", "Heap-ийн элементүүдийг сольж байна")
                heapify(size, largest)

        for i in range(n // 2 - 1, -1, -1):
            heapify(n, i)

        for end in range(n - 1, 0, -1):
            values[0], values[end] = values[end], values[0]
            record("step", "Хамгийн их утгыг төгсгөлд шилжүүлэв")
            heapify(end, 0)

    elif algorithm_key == "shell_sort":
        gap = n // 2
        while gap > 0:
            for i in range(gap, n):
                temp = values[i]
                j = i
                while j >= gap and values[j - gap] > temp:
                    values[j] = values[j - gap]
                    record("step", f"Gap = {gap}: элемент шилжүүлэв")
                    j -= gap
                values[j] = temp
                record("step", f"Gap = {gap}: байрлал шинэчлэв")
            gap //= 2

    elif algorithm_key == "counting_sort":
        if n:
            minimum, value_range = check_range(values)
            counts = [0] * value_range

            for value in values:
                counts[value - minimum] += 1
                record("step", f"{value} утгын давтамжийг тоолов")

            index = 0
            for offset, count in enumerate(counts):
                for _ in range(count):
                    values[index] = offset + minimum
                    index += 1
                    record("step", f"{offset + minimum} утгыг байрлуулав")

    elif algorithm_key == "merge_sort":
        def merge_range(left, right):
            if right - left <= 1:
                return

            middle = (left + right) // 2
            merge_range(left, middle)
            merge_range(middle, right)

            merged = []
            i, j = left, middle

            while i < middle and j < right:
                if values[i] <= values[j]:
                    merged.append(values[i])
                    i += 1
                else:
                    merged.append(values[j])
                    j += 1

            merged.extend(values[i:middle])
            merged.extend(values[j:right])
            values[left:right] = merged
            record("merge", f"{left}:{right} хэсгийг нэгтгэв")

        merge_range(0, n)

    else:
        raise ValueError("Алгоритмын сонголт буруу байна.")


def visualized_sort(numbers, algorithm_key):
    """Sort `numbers` and return (sorted_values, events, info).

    `info` has `total_steps` (every step the algorithm performed) and
    `stride` (1 means every step was recorded, N means every N-th step).
    """
    # Pass 1: count the steps without storing anything.
    total_steps = 0

    def count(kind, task):
        nonlocal total_steps
        total_steps += 1

    _execute(list(numbers), algorithm_key, count)

    stride = max(1, ceil(total_steps / event_budget(len(numbers))))

    # Pass 2: record snapshots, keeping only every `stride`-th step.
    values = list(numbers)
    events = []
    started = perf_counter()
    step_index = 0

    def snapshot(kind, task):
        events.append({
            "at": round((perf_counter() - started) * 1000, 3),
            "kind": kind,
            "task": task,
            "thread": "Selected Algorithm",
            "values": values.copy(),
        })

    def record(kind, task):
        nonlocal step_index
        if step_index % stride == 0:
            snapshot(kind, task)
        step_index += 1

    snapshot("start", f"{algorithm_key} эхэллээ")
    _execute(values, algorithm_key, record)
    snapshot("finish", f"{algorithm_key} дууслаа")

    return values, events, {"total_steps": total_steps, "stride": stride}
