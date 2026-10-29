def quick_sort(numbers):
    arr = numbers.copy()

    def sort(low, high):
        if low >= high:
            return
        pivot = arr[(low + high) // 2]
        i, j = low, high
        while i <= j:
            while arr[i] < pivot:
                i += 1
            while arr[j] > pivot:
                j -= 1
            if i <= j:
                arr[i], arr[j] = arr[j], arr[i]
                i += 1
                j -= 1
        if low < j:
            sort(low, j)
        if i < high:
            sort(i, high)

    sort(0, len(arr) - 1)
    return arr
