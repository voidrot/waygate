#!/usr/bin/env python3
"""POST a completed agent-session payload to the WayGate API."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import time
import urllib.error
import urllib.request
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description="POST an agent-session payload")
    parser.add_argument("payload_file", help="Path to payload JSON")
    parser.add_argument(
        "--endpoint",
        default="http://127.0.0.1:8000/webhooks/agent-session",
        help="Webhook endpoint URL",
    )
    parser.add_argument(
        "--signing-secret",
        help="Shared secret used to add HMAC signature headers",
    )
    return parser.parse_args()


def build_headers(body: bytes, signing_secret: str | None) -> dict[str, str]:
    """Build HTTP headers for the request."""

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "waygate-agent-session-script/0.1.0",
    }
    if signing_secret is None:
        return headers

    timestamp = str(int(time.time()))
    digest = hmac.new(
        signing_secret.encode("utf-8"),
        timestamp.encode("utf-8") + b"." + body,
        hashlib.sha256,
    ).hexdigest()
    headers["X-Waygate-Timestamp"] = timestamp
    headers["X-Waygate-Signature"] = f"sha256={digest}"
    return headers


def main() -> int:
    """POST the payload and print the response."""

    args = parse_args()
    payload_path = Path(args.payload_file)
    body = payload_path.read_bytes()
    headers = build_headers(body, args.signing_secret)
    request = urllib.request.Request(
        args.endpoint, data=body, headers=headers, method="POST"
    )

    try:
        with urllib.request.urlopen(request) as response:
            response_body = response.read().decode("utf-8")
            parsed = json.loads(response_body)
            print(json.dumps(parsed, indent=2, sort_keys=True))
            return 0
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        print(detail)
        return exc.code


if __name__ == "__main__":
    raise SystemExit(main())
