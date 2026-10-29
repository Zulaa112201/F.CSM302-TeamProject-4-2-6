RANGE_ERROR = (
    "Counting Sort: утгуудын хүрээ хэт том байна. "
    "Өөр алгоритм сонгоно уу."
)


def check_range(numbers):
    """Return (minimum, value_range); raise ValueError if the range is too big.

    The same rule is used by the sorting function and by the visualizer,
    so both always accept or reject the same input.
    """
    minimum = min(numbers)
    maximum = max(numbers)
    value_range = maximum - minimum + 1

    if value_range > max(1_000_000, len(numbers) * 100):
        raise ValueError(RANGE_ERROR)

    return minimum, value_range


def counting_sort(numbers):
    if not numbers:
        return []

    minimum, value_range = check_range(numbers)
    counts = [0] * value_range

    for number in numbers:
        counts[number - minimum] += 1

    result = []
    for index, count in enumerate(counts):
        result.extend([index + minimum] * count)

    return result
