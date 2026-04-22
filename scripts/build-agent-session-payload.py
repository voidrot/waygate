#!/usr/bin/env python3
"""Build a normalized completed agent-session payload from transcript JSON."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description="Build a normalized completed agent-session payload"
    )
    parser.add_argument(
        "--messages-file", required=True, help="Path to message list JSON"
    )
    parser.add_argument("--output", help="Destination file. Defaults to stdout.")
    parser.add_argument(
        "--session-id", required=True, help="Stable upstream session id"
    )
    parser.add_argument("--title", required=True, help="Session title")
    parser.add_argument("--provider", required=True, help="Upstream provider name")
    parser.add_argument("--surface", required=True, help="Upstream UI/runtime surface")
    parser.add_argument(
        "--capture-adapter", required=True, help="Exporter or bridge name"
    )
    parser.add_argument(
        "--capture-adapter-version",
        default="0.1.0",
        help="Exporter or bridge version",
    )
    parser.add_argument("--conversation-url", help="Canonical conversation URL")
    parser.add_argument(
        "--visibility",
        default="internal",
        choices=["public", "internal", "private"],
        help="Stored raw-document visibility",
    )
    parser.add_argument("--topic", action="append", default=[], help="Session topic")
    parser.add_argument("--tag", action="append", default=[], help="Session tag")
    return parser.parse_args()


def load_messages(path: Path) -> list[dict[str, Any]]:
    """Load transcript messages from JSON."""

    loaded = json.loads(path.read_text())
    if not isinstance(loaded, list) or not loaded:
        raise ValueError("messages file must contain a non-empty JSON list")
    return loaded


def iso_timestamp(value: str | None, fallback: datetime) -> str:
    """Normalize an optional timestamp string to UTC ISO-8601."""

    if value is None:
        return fallback.astimezone(UTC).isoformat().replace("+00:00", "Z")

    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


def run_git(*args: str) -> str | None:
    """Run a git command and return stripped stdout when available."""

    try:
        completed = subprocess.run(
            ["git", *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError, subprocess.CalledProcessError:
        return None
    value = completed.stdout.strip()
    return value or None


def discover_repository_metadata() -> dict[str, Any]:
    """Best-effort repository metadata discovery from git."""

    repository_root = run_git("rev-parse", "--show-toplevel")
    if repository_root is None:
        return {}

    dirty_output = run_git("status", "--porcelain")
    return {
        "repository_name": Path(repository_root).name,
        "repository_url": run_git("config", "--get", "remote.origin.url"),
        "branch": run_git("branch", "--show-current"),
        "commit_sha": run_git("rev-parse", "HEAD"),
        "dirty_worktree": bool(dirty_output),
    }


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    """Build the normalized completed-session payload."""

    messages = load_messages(Path(args.messages_file))
    now = datetime.now(UTC)
    started_at = iso_timestamp(messages[0].get("created_at"), now)
    completed_at = iso_timestamp(messages[-1].get("created_at"), now)
    repository = discover_repository_metadata()

    payload = {
        "schema_version": "v1",
        "capture_adapter": args.capture_adapter,
        "capture_adapter_version": args.capture_adapter_version,
        "provider": args.provider,
        "surface": args.surface,
        "exported_at": now.isoformat().replace("+00:00", "Z"),
        "visibility": args.visibility,
        "session": {
            "session_id": args.session_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "title": args.title,
            "conversation_url": args.conversation_url,
            "topics": args.topic,
            "tags": args.tag,
            "workspace": {
                "workspace_name": Path.cwd().name,
                "workspace_root": str(Path.cwd()),
            },
            "repository": repository or None,
            "messages": messages,
        },
    }

    if payload["session"]["repository"] is None:
        del payload["session"]["repository"]
    if payload["session"]["conversation_url"] is None:
        del payload["session"]["conversation_url"]
    return payload


def main() -> int:
    """Build and emit the normalized payload."""

    args = parse_args()
    payload = build_payload(args)
    rendered = json.dumps(payload, sort_keys=True, indent=2) + "\n"

    if args.output:
        Path(args.output).write_text(rendered)
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
