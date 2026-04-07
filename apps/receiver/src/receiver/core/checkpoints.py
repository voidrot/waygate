from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from waygate_core.settings import get_runtime_settings


def _checkpoints_file() -> Path:
    settings = get_runtime_settings()
    base_dir = Path(settings.local_storage_path)
    meta_dir = base_dir / "meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    return meta_dir / "poll_checkpoints.json"


def _read_all_checkpoints() -> dict[str, str]:
    file_path = _checkpoints_file()
    if not file_path.exists():
        return {}

    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {str(key): str(value) for key, value in data.items()}
    except json.JSONDecodeError:
        return {}

    return {}


def get_poll_checkpoint(plugin_name: str) -> datetime | None:
    all_checkpoints = _read_all_checkpoints()
    value = all_checkpoints.get(plugin_name)
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None

    return parsed


def set_poll_checkpoint(plugin_name: str, checkpoint: datetime) -> None:
    all_checkpoints = _read_all_checkpoints()
    all_checkpoints[plugin_name] = checkpoint.isoformat()
    file_path = _checkpoints_file()
    file_path.write_text(json.dumps(all_checkpoints, indent=2), encoding="utf-8")
