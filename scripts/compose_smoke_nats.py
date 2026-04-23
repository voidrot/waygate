#!/usr/bin/env python3
"""Run the end-to-end Docker Compose smoke test against communication-nats."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_EXAMPLE = REPO_ROOT / "env.compose.example"
FIXTURE_PATH = REPO_ROOT / "scripts" / "fixtures" / "generic-webhook.sample.json"
COMPOSE_FILE = REPO_ROOT / "compose.prod.yml"
COMPOSE_PROFILES = ("nats", "chroma", "ollama")
SMOKE_MODEL_NAME = "qwen2.5:0.5b"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the end-to-end NATS-backed Docker Compose smoke test"
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=900.0,
        help="Maximum time to wait for the web app readiness and workflow output",
    )
    parser.add_argument(
        "--skip-model-pull",
        action="store_true",
        help="Skip pulling Ollama models before starting the web app and worker",
    )
    parser.add_argument(
        "--keep-up",
        action="store_true",
        help="Leave the compose stack running after the test finishes",
    )
    return parser.parse_args()


def load_env_template() -> list[str]:
    return ENV_EXAMPLE.read_text().splitlines()


def reserve_host_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return int(sock.getsockname()[1])


def override_env_lines(lines: list[str], overrides: dict[str, str]) -> list[str]:
    rendered: list[str] = []
    seen: set[str] = set()
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            rendered.append(line)
            continue

        key, _sep, _value = line.partition("=")
        key = key.strip()
        if key in overrides:
            rendered.append(f'{key} = "{overrides[key]}"')
            seen.add(key)
        else:
            rendered.append(line)

    for key, value in overrides.items():
        if key not in seen:
            rendered.append(f'{key} = "{value}"')

    return rendered


def parse_env_lines(lines: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            continue
        key, _sep, raw_value = line.partition("=")
        value = raw_value.strip()
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        values[key.strip()] = value
    return values


def compose_env(temp_root: Path) -> tuple[Path, int]:
    wiki_root = temp_root / "wiki"
    wiki_root.mkdir(parents=True, exist_ok=True)

    api_port = reserve_host_port()

    overrides = {
        "WIKI_DATA_DIR": str(wiki_root),
        "WAYGATE_CORE__COMMUNICATION_PLUGIN_NAME": "communication-nats",
        "WAYGATE_CORE__METADATA_MODEL_NAME": SMOKE_MODEL_NAME,
        "WAYGATE_CORE__DRAFT_MODEL_NAME": SMOKE_MODEL_NAME,
        "WAYGATE_CORE__REVIEW_MODEL_NAME": SMOKE_MODEL_NAME,
        "API_PORT": str(api_port),
        "POSTGRES_PORT": str(reserve_host_port()),
        "VALKEY_PORT": str(reserve_host_port()),
        "CHROMA_PORT": str(reserve_host_port()),
        "OLLAMA_PORT": str(reserve_host_port()),
        "NATS_CLIENT_PORT": str(reserve_host_port()),
        "NATS_MONITORING_PORT": str(reserve_host_port()),
        "NATS_CLUSTER_PORT": str(reserve_host_port()),
    }
    lines = override_env_lines(load_env_template(), overrides)
    env_path = temp_root / ".env.compose"
    env_path.write_text("\n".join(lines) + "\n")
    return env_path, api_port


def run_compose(
    args: list[str],
    *,
    env_file: Path,
    project_name: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["WAYGATE_COMPOSE_ENV_FILE"] = str(env_file)
    env["COMPOSE_PROJECT_NAME"] = project_name
    env.update(parse_env_lines(env_file.read_text().splitlines()))
    return subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(COMPOSE_FILE),
            *(item for profile in COMPOSE_PROFILES for item in ("--profile", profile)),
            *args,
        ],
        cwd=REPO_ROOT,
        env=env,
        check=check,
        capture_output=True,
        text=True,
    )


def wait_for_http(url: str, *, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                if 200 <= response.status < 500:
                    return
        except Exception as exc:  # pragma: no cover - exercised by real smoke runs
            last_error = exc
        time.sleep(2)
    raise TimeoutError(f"Timed out waiting for {url}: {last_error}")


def post_fixture(webhook_url: str) -> dict[str, object]:
    request = urllib.request.Request(
        webhook_url,
        data=FIXTURE_PATH.read_bytes(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read().decode("utf-8")
        return json.loads(payload)


def wait_for_output(wiki_root: Path, *, timeout_seconds: float) -> Path:
    compiled_root = wiki_root / "compiled"
    review_root = wiki_root / "review"
    raw_root = wiki_root / "raw"
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        raw_files = sorted(path for path in raw_root.rglob("*") if path.is_file())
        compiled_files = sorted(
            path for path in compiled_root.rglob("*") if path.is_file()
        )
        review_files = sorted(path for path in review_root.rglob("*") if path.is_file())
        if raw_files and (compiled_files or review_files):
            return compiled_files[0] if compiled_files else review_files[0]
        time.sleep(2)
    raise TimeoutError("Timed out waiting for raw and workflow output artifacts")


def dump_failure_context(env_file: Path) -> None:
    project_name = os.environ.get("COMPOSE_PROJECT_NAME", "waygate")
    for args in (
        ["ps"],
        ["logs", "--tail=200", "web", "worker", "ollama", "nats"],
    ):
        try:
            result = run_compose(
                args,
                env_file=env_file,
                project_name=project_name,
                check=False,
            )
        except Exception as exc:  # pragma: no cover - exercised by real smoke runs
            print(f"failed to collect compose diagnostics: {exc}", file=sys.stderr)
            continue
        if result.stdout:
            print(result.stdout, file=sys.stderr)
        if result.stderr:
            print(result.stderr, file=sys.stderr)


def run_smoke_test(options: argparse.Namespace) -> int:
    with tempfile.TemporaryDirectory(prefix="waygate-nats-smoke-") as temp_dir:
        temp_root = Path(temp_dir)
        env_file, api_port = compose_env(temp_root)
        wiki_root = temp_root / "wiki"
        project_name = f"waygate-smoke-{uuid.uuid4().hex[:8]}"
        os.environ["COMPOSE_PROJECT_NAME"] = project_name
        api_ready_url = f"http://127.0.0.1:{api_port}/openapi.json"
        webhook_url = f"http://127.0.0.1:{api_port}/webhooks/generic-webhook"

        try:
            run_compose(
                ["up", "-d", "db", "valkey", "chromadb", "nats", "ollama"],
                env_file=env_file,
                project_name=project_name,
            )

            if not options.skip_model_pull:
                for model in (SMOKE_MODEL_NAME,):
                    run_compose(
                        ["exec", "-T", "ollama", "ollama", "pull", model],
                        env_file=env_file,
                        project_name=project_name,
                    )

            run_compose(
                ["up", "-d", "--build", "web", "worker"],
                env_file=env_file,
                project_name=project_name,
            )
            wait_for_http(api_ready_url, timeout_seconds=options.timeout_seconds)
            response = post_fixture(webhook_url)
            output_path = wait_for_output(
                wiki_root, timeout_seconds=options.timeout_seconds
            )
        except Exception:
            dump_failure_context(env_file)
            raise
        finally:
            if not options.keep_up:
                run_compose(
                    ["down"],
                    env_file=env_file,
                    project_name=project_name,
                    check=False,
                )

        print(json.dumps(response, indent=2, sort_keys=True))
        print(f"workflow output: {output_path}")
        return 0


def main() -> int:
    options = parse_args()
    return run_smoke_test(options)


if __name__ == "__main__":
    raise SystemExit(main())
