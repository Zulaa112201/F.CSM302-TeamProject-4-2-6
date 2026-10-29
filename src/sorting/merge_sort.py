def merge(left, right):
    """Merge two already-sorted lists into one sorted list."""
    result = []
    i = j = 0

    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1

    result.extend(left[i:])
    result.extend(right[j:])
    return result


def merge_sort(numbers):
    """Sequential recursive Merge Sort; does not mutate the input list."""
    if len(numbers) <= 1:
        return list(numbers)

    middle = len(numbers) // 2
    left = merge_sort(numbers[:middle])
    right = merge_sort(numbers[middle:])
    return merge(left, right)