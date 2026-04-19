#!/usr/bin/env python3
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from uuid import uuid4


class MockWorkerHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/workflows/trigger":
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"detail":"not found"}')
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length) if content_length else b"{}"

        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"detail":"invalid json"}')
            return

        print("mock-worker received:", json.dumps(payload, indent=2, sort_keys=True))

        response = {
            "status": "accepted",
            "message_id": str(uuid4()),
        }
        response_bytes = json.dumps(response).encode("utf-8")

        self.send_response(202)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)


def main() -> None:
    server = HTTPServer(("127.0.0.1", 8090), MockWorkerHandler)
    print("mock-worker listening on http://127.0.0.1:8090/workflows/trigger")
    server.serve_forever()


if __name__ == "__main__":
    main()
