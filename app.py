
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    Response,
    stream_with_context,
)
from queue import Queue
from threading import Thread
from time import perf_counter
import json

from src.sorting.merge_sort import merge_sort
from src.sorting.parallel_sort import parallel_merge_sort
from src.sorting.bubble_sort import bubble_sort
from src.sorting.insertion_sort import insertion_sort
from src.sorting.selection_sort import selection_sort
from src.sorting.quick_sort import quick_sort
from src.sorting.heap_sort import heap_sort
from src.sorting.shell_sort import shell_sort
from src.sorting.counting_sort import counting_sort, check_range
from src.sorting.benchmark import run_benchmark
from src.sorting.visualize import visualized_sort, ALGORITHM_LIMITS


app = Flask(__name__)

MAX_NUMBERS = 5000
MAX_ABS_VALUE = 2**53 - 1

ALGORITHMS = {
    "merge_sort": ("Merge Sort", merge_sort),
    "bubble_sort": ("Bubble Sort", bubble_sort),
    "insertion_sort": ("Insertion Sort", insertion_sort),
    "selection_sort": ("Selection Sort", selection_sort),
    "quick_sort": ("Quick Sort", quick_sort),
    "heap_sort": ("Heap Sort", heap_sort),
    "shell_sort": ("Shell Sort", shell_sort),
    "counting_sort": ("Counting Sort", counting_sort),
}


@app.get("/")
def index():
    return render_template("index.html", limits=ALGORITHM_LIMITS)


def parse_numbers(payload, limit=MAX_NUMBERS, algorithm_name=None):
    raw = payload.get("numbers", [])

    if isinstance(raw, str):
        parts = raw.replace(",", " ").replace(";", " ").split()

        if not parts:
            raise ValueError("Тоонуудыг оруулна уу.")

        try:
            numbers = [int(part) for part in parts]
        except ValueError as exc:
            raise ValueError(
                "Зөвхөн бүхэл тоо оруулна уу."
            ) from exc

    elif isinstance(raw, list):
        try:
            if any(isinstance(value, bool) for value in raw):
                raise ValueError

            numbers = [int(value) for value in raw]

            for original, converted in zip(raw, numbers):
                if isinstance(original, float) and original != converted:
                    raise ValueError

                if (
                    isinstance(original, str)
                    and str(converted) != original.strip()
                ):
                    raise ValueError

        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(
                "Бүхэл тоон жагсаалт оруулна уу."
            ) from exc

    else:
        raise ValueError("Тоонуудын формат буруу байна.")

    if len(numbers) < 4:
        raise ValueError(
            "Эрэмбэлэхийн тулд 4 болон түүнээс дээш тоо оруулна уу."
        )

    if len(numbers) > limit:
        subject = f"{algorithm_name}-д" if algorithm_name else ""
        raise ValueError(
            f"{subject} хамгийн ихдээ {limit} тоо оруулна уу.".strip()
        )

    if any(abs(value) > MAX_ABS_VALUE for value in numbers):
        raise ValueError("Тоон утга хэт том байна.")

    return numbers


def get_algorithm(payload):
    key = payload.get("algorithm", "merge_sort")

    if key not in ALGORITHMS:
        raise ValueError("Алгоритмын сонголт буруу байна.")

    return key, ALGORITHMS[key]


def prepare_request(payload):
    """Validate input and return sorting information."""
    key, (name, function) = get_algorithm(payload)

    limit = min(
        MAX_NUMBERS,
        ALGORITHM_LIMITS.get(key, MAX_NUMBERS),
    )

    numbers = parse_numbers(
        payload,
        limit=limit,
        algorithm_name=name,
    )

    if key == "counting_sort":
        check_range(numbers)

    return numbers, key, name, function


def time_algorithms(numbers, function):
    """Measure sequential and parallel sorting times."""
    start = perf_counter()
    sequential = function(numbers.copy())
    sequential_ms = (perf_counter() - start) * 1000

    start = perf_counter()
    parallel, _ = parallel_merge_sort(
        numbers.copy(),
        trace=False,
    )
    parallel_ms = (perf_counter() - start) * 1000

    return sequential, sequential_ms, parallel, parallel_ms


@app.get("/api/sort")
def sort_method_error():
    return jsonify({
        "error": "POST хүсэлт ашиглана уу."
    }), 405


@app.post("/api/sort")
def sort_api():
    payload = request.get_json(silent=True) or {}

    try:
        numbers, key, name, function = prepare_request(payload)

    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        (
            sequential,
            sequential_ms,
            parallel,
            parallel_ms,
        ) = time_algorithms(numbers, function)

        return jsonify({
            "original": numbers,
            "algorithm": key,
            "algorithm_name": name,
            "sequential_result": sequential,
            "parallel_result": parallel,
            "sequential_ms": round(sequential_ms, 3),
            "parallel_ms": round(parallel_ms, 3),
            "same_result": (
                sequential == parallel == sorted(numbers)
            ),
            "count": len(numbers),
        })

    except Exception:
        app.logger.exception("Sorting failed")

        return jsonify({
            "error": "Эрэмбэлэлтэд алдаа гарлаа. Terminal-ийг шалгана уу."
        }), 500


@app.post("/api/sort/stream")
def sort_stream_api():
    payload = request.get_json(silent=True) or {}

    try:
        numbers, key, name, function = prepare_request(payload)

    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    event_queue = Queue()

    def sorting_job():
        try:
            (
                sequential,
                sequential_ms,
                parallel,
                parallel_ms,
            ) = time_algorithms(numbers, function)

            visual_result, visual_events, info = visualized_sort(
                numbers,
                key,
            )

            for event in visual_events:
                event_queue.put({
                    "type": "event",
                    "event": event,
                })

            expected = sorted(numbers)

            event_queue.put({
                "type": "result",
                "data": {
                    "original": numbers,
                    "algorithm": key,
                    "algorithm_name": name,
                    "sequential_result": sequential,
                    "parallel_result": parallel,
                    "sequential_ms": round(sequential_ms, 3),
                    "parallel_ms": round(parallel_ms, 3),
                    "same_result": (
                        sequential
                        == parallel
                        == visual_result
                        == expected
                    ),
                    "count": len(numbers),
                    "total_steps": info["total_steps"],
                    "stride": info["stride"],
                    "shown_events": len(visual_events),
                },
            })

        except Exception:
            app.logger.exception("Streaming sort failed")

            event_queue.put({
                "type": "error",
                "error": (
                    "Эрэмбэлэлтэд алдаа гарлаа. "
                    "Terminal-ийг шалгана уу."
                ),
            })

        finally:
            event_queue.put(None)

    def generate():
        Thread(
            target=sorting_job,
            daemon=True,
        ).start()

        while True:
            message = event_queue.get()

            if message is None:
                break

            yield json.dumps(
                message,
                ensure_ascii=False,
            ) + "\n"

    return Response(
        stream_with_context(generate()),
        content_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache, no-store",
            "X-Accel-Buffering": "no",
        },
    )
    
    
@app.route("/api/benchmark", methods=["GET", "POST"])
def benchmark_api():
    try:
        if request.method == "POST":
            payload = request.get_json(silent=True) or {}
            numbers = parse_numbers(payload)

            print("BENCHMARK INPUT:", numbers)
            print("BENCHMARK COUNT:", len(numbers))

            results = run_benchmark(numbers=numbers)

        else:
            results = run_benchmark()

        print(
            "BENCHMARK RESULT SIZE:",
            [row["size"] for row in results],
        )

        return jsonify({
            "results": results,
            "all_correct": all(
                row.get("same_result", False)
                for row in results
            ),
        })

    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    except Exception as exc:
        app.logger.exception("Benchmark failed")
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(debug=True, threaded=True)

        
if __name__ == "__main__":
    app.run(
        debug=True,
        threaded=True,
    )
