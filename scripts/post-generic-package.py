#!/usr/bin/env python3
"""POST a source tree to the WayGate generic webhook endpoint.

This helper defaults to the ``libs/core`` package so the current repository can
be fed through the generic webhook end to end during local testing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PACKAGE_ROOT = REPO_ROOT / "libs" / "core"
SKIPPED_PARTS = {"__pycache__", ".git", ".pytest_cache", ".mypy_cache"}


def default_endpoint() -> str:
    """Resolve the default generic webhook endpoint for local runs."""

    explicit_endpoint = os.getenv("WAYGATE_GENERIC_WEBHOOK_ENDPOINT")
    if explicit_endpoint:
        return explicit_endpoint

    port = os.getenv("API_PORT", "8080")
    return f"http://127.0.0.1:{port}/webhooks/generic-webhook"


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description="POST a package tree to the WayGate generic webhook"
    )
    parser.add_argument(
        "package_root",
        nargs="?",
        default=str(DEFAULT_PACKAGE_ROOT),
        help="Package or source-tree path to upload (default: libs/core)",
    )
    parser.add_argument(
        "--endpoint",
        default=default_endpoint(),
        help="Generic webhook endpoint URL",
    )
    parser.add_argument(
        "--event",
        default="package.snapshot",
        help="Webhook metadata event name",
    )
    parser.add_argument(
        "--source",
        default="waygate-script.package-upload",
        help="Webhook metadata source name",
    )
    parser.add_argument(
        "--topic",
        action="append",
        default=[],
        help="Topic to attach to the payload metadata (repeatable)",
    )
    parser.add_argument(
        "--tag",
        action="append",
        default=[],
        help="Tag to attach to the payload metadata (repeatable)",
    )
    parser.add_argument(
        "--output",
        help="Optional path to write the generated payload JSON",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build the payload and print it instead of posting it",
    )
    return parser.parse_args()


def resolve_package_root(raw_path: str) -> Path:
    """Resolve the requested package root relative to the repository root."""

    candidate = Path(raw_path)
    resolved = candidate if candidate.is_absolute() else REPO_ROOT / candidate
    package_root = resolved.resolve()
    if not package_root.exists():
        raise FileNotFoundError(f"Package root does not exist: {package_root}")
    if not package_root.is_dir():
        raise NotADirectoryError(f"Package root is not a directory: {package_root}")
    return package_root


def should_include(path: Path) -> bool:
    """Return whether the file should be included in the generated payload."""

    relative = path.relative_to(REPO_ROOT)
    if any(part in SKIPPED_PARTS for part in relative.parts):
        return False
    if any(part.startswith(".") for part in relative.parts):
        return False
    return path.is_file()


def detect_document_type(path: Path) -> str:
    """Map a file suffix to a generic webhook document type."""

    match path.suffix.lower():
        case ".py":
            return "python"
        case ".md":
            return "markdown"
        case ".toml":
            return "toml"
        case ".j2":
            return "jinja2"
        case ".typed":
            return "text"
        case _:
            return "text"


def read_text_document(path: Path) -> str | None:
    """Read a UTF-8 text document, skipping binary content."""

    payload = path.read_bytes()
    if b"\x00" in payload:
        return None
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError:
        return None


def build_document(path: Path, package_root: Path) -> dict[str, object] | None:
    """Build one generic-webhook document object for a file."""

    content = read_text_document(path)
    if content is None:
        return None

    relative_repo_path = path.relative_to(REPO_ROOT).as_posix()
    package_name = package_root.name
    return {
        "document_type": detect_document_type(path),
        "document_name": path.name,
        "document_path": relative_repo_path,
        "document_hash": f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}",
        "content": content,
        "metadata": {
            "topics": [package_name],
            "tags": [
                "source-tree",
                f"extension:{path.suffix.lower().lstrip('.') or 'none'}",
            ],
        },
    }


def build_payload(args: argparse.Namespace, package_root: Path) -> dict[str, object]:
    """Build the generic webhook payload for the package tree."""

    topics = args.topic or [package_root.name]
    tags = args.tag or ["generic-webhook", "e2e", package_root.name]

    documents: list[dict[str, object]] = []
    for path in sorted(package_root.rglob("*")):
        if not should_include(path):
            continue
        document = build_document(path, package_root)
        if document is not None:
            documents.append(document)

    if not documents:
        raise ValueError(f"No UTF-8 text documents found under {package_root}")

    return {
        "metadata": {
            "event": args.event,
            "source": args.source,
            "topics": topics,
            "tags": tags,
            "originated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        },
        "documents": documents,
    }


def emit_payload(payload: dict[str, object], output_path: str | None) -> str:
    """Render the payload to JSON and optionally write it to disk."""

    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if output_path:
        Path(output_path).write_text(rendered)
    return rendered


def post_payload(endpoint: str, body: bytes) -> int:
    """POST the payload and print the response body."""

    request = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "waygate-generic-package-script/0.1.0",
        },
        method="POST",
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


def main() -> int:
    """Build the payload, optionally print it, or POST it to the webhook."""

    args = parse_args()
    package_root = resolve_package_root(args.package_root)
    payload = build_payload(args, package_root)
    rendered = emit_payload(payload, args.output)

    if args.dry_run:
        print(rendered, end="")
        return 0

    return post_payload(args.endpoint, rendered.encode("utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
