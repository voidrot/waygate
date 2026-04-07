from datetime import UTC, datetime
import json

from receiver.core import checkpoints


def test_set_poll_checkpoint_round_trips(tmp_path, monkeypatch) -> None:
    checkpoint_file = tmp_path / "poll_checkpoints.json"
    monkeypatch.setattr(checkpoints, "_checkpoints_file", lambda: checkpoint_file)

    expected = datetime(2026, 4, 6, 12, 30, tzinfo=UTC)
    checkpoints.set_poll_checkpoint("plugin-a", expected)

    assert checkpoints.get_poll_checkpoint("plugin-a") == expected
    assert json.loads(checkpoint_file.read_text(encoding="utf-8")) == {
        "plugin-a": expected.isoformat()
    }


def test_get_poll_checkpoint_ignores_malformed_file(tmp_path, monkeypatch) -> None:
    checkpoint_file = tmp_path / "poll_checkpoints.json"
    checkpoint_file.write_text("{not-json", encoding="utf-8")
    monkeypatch.setattr(checkpoints, "_checkpoints_file", lambda: checkpoint_file)

    assert checkpoints.get_poll_checkpoint("plugin-a") is None
