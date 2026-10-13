"""Exercise real browser preconnection and concurrent input snapshots."""
import concurrent.futures
import http.client
import json
import socket
import sys
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from phone_input_fixture import InputServer


class PhoneInputFixtureTests(unittest.TestCase):
    def setUp(self):
        self.server = InputServer(0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_port

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, method, path, payload=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        try:
            body = None if payload is None else json.dumps(payload)
            connection.request(method, path, body, {"Content-Type": "application/json"})
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    def test_idle_browser_connection_does_not_block_page_and_events(self):
        with socket.create_connection(("127.0.0.1", self.port), timeout=2):
            status, page = self.request("GET", "/")
            self.assertEqual(status, 200)
            self.assertIn(b"LOCAL TEST", page)
            payload = {"events": [{"type": "pointerdown", "buttons": 1}],
                       "geometry": {"width": 393}, "value": "hello", "scroll_top": 0}
            self.assertEqual(self.request("POST", "/events", payload)[0], 200)
            status, body = self.request("GET", "/state")
            self.assertEqual(status, 200)
            state = json.loads(body)
            self.assertEqual(state["events"], payload["events"])
            self.assertEqual(state["latest"]["value"], "hello")

    def test_concurrent_updates_have_valid_bounded_snapshots(self):
        def update(index):
            payload = {"events": [{"type": "pointermove", "index": index}]}
            self.assertEqual(self.request("POST", "/events", payload)[0], 200)
            status, body = self.request("GET", "/state")
            self.assertEqual(status, 200)
            snapshot = json.loads(body)
            self.assertLessEqual(len(snapshot["events"]), 1000)
            self.assertTrue(all(event["type"] == "pointermove" for event in snapshot["events"]))

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(update, range(20)))
        state = json.loads(self.request("GET", "/state")[1])
        self.assertEqual(sorted(event["index"] for event in state["events"]), list(range(20)))


if __name__ == "__main__":
    unittest.main()
