import json
import unittest

from app import app
from src.sorting.visualize import ALGORITHM_LIMITS


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def post(self, path, body):
        return self.client.post(path, json=body)

    def test_index_exposes_limits_to_frontend(self):
        page = self.client.get("/").get_data(as_text=True)
        self.assertIn("window.SORT_LIMITS", page)
        self.assertIn('"bubble_sort": 1000', page)

    def test_sort_every_algorithm(self):
        data = [5, 3, -2, 9, 0, 3, 7, 1]
        for key in ALGORITHM_LIMITS:
            with self.subTest(algorithm=key):
                response = self.post(
                    "/api/sort", {"numbers": data, "algorithm": key}
                )
                body = response.get_json()
                self.assertEqual(response.status_code, 200)
                self.assertTrue(body["same_result"])
                self.assertEqual(body["sequential_result"], sorted(data))
                self.assertGreater(body["sequential_ms"], 0)
                self.assertGreater(body["parallel_ms"], 0)

    def test_string_input(self):
        response = self.post(
            "/api/sort", {"numbers": "3, 1; 2 -5", "algorithm": "heap_sort"}
        )
        self.assertEqual(response.get_json()["sequential_result"], [-5, 1, 2, 3])

    def test_invalid_input_returns_400(self):
        bad_bodies = [
            {"numbers": ""},
            {"numbers": "1 2 x"},
            {"numbers": [1.5]},
            {"numbers": [True]},
            {"numbers": [None]},
            {"numbers": [1, 2], "algorithm": "nope"},
            {"numbers": [10 ** 30]},
            {"numbers": 5},
            {},
        ]
        for body in bad_bodies:
            with self.subTest(body=body):
                response = self.post("/api/sort", body)
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.get_json())

    def test_infinity_does_not_crash_server(self):
        response = self.client.post(
            "/api/sort",
            data='{"numbers": [Infinity, 1]}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_per_algorithm_limit(self):
        too_many = list(range(ALGORITHM_LIMITS["bubble_sort"] + 1))
        response = self.post(
            "/api/sort", {"numbers": too_many, "algorithm": "bubble_sort"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("1000", response.get_json()["error"])

        # The same amount is fine for an algorithm with a higher limit.
        response = self.post(
            "/api/sort", {"numbers": too_many, "algorithm": "merge_sort"}
        )
        self.assertEqual(response.status_code, 200)

    def test_counting_sort_range_error_is_400(self):
        for path in ("/api/sort", "/api/sort/stream"):
            with self.subTest(path=path):
                response = self.post(
                    path,
                    {"numbers": [0, 10 ** 9], "algorithm": "counting_sort"},
                )
                self.assertEqual(response.status_code, 400)

    def test_get_sort_is_405(self):
        self.assertEqual(self.client.get("/api/sort").status_code, 405)

    def test_stream_returns_events_then_result(self):
        response = self.post(
            "/api/sort/stream",
            {"numbers": "5 3 1 4 2", "algorithm": "quick_sort"},
        )
        self.assertEqual(response.status_code, 200)
        messages = [
            json.loads(line)
            for line in response.get_data(as_text=True).splitlines()
            if line
        ]
        types = [message["type"] for message in messages]
        self.assertEqual(types[-1], "result")
        self.assertIn("event", types)
        self.assertNotIn("error", types)

        result = messages[-1]["data"]
        self.assertTrue(result["same_result"])
        self.assertEqual(result["sequential_result"], [1, 2, 3, 4, 5])
        self.assertEqual(result["stride"], 1)

    def test_stream_worst_case_stays_small(self):
        data = list(range(1000, 0, -1))
        response = self.post(
            "/api/sort/stream", {"numbers": data, "algorithm": "bubble_sort"}
        )
        self.assertEqual(response.status_code, 200)
        text = response.get_data(as_text=True)
        messages = [json.loads(line) for line in text.splitlines() if line]

        self.assertEqual(messages[-1]["type"], "result")
        self.assertTrue(messages[-1]["data"]["same_result"])
        self.assertGreater(messages[-1]["data"]["stride"], 1)
        self.assertLess(len(text), 40_000_000)

    def test_benchmark(self):
        response = self.client.get("/api/benchmark")
        body = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(body["all_correct"])
        self.assertTrue(body["results"])


if __name__ == "__main__":
    unittest.main()
