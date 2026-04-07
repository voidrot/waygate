from pathlib import Path
import sys


def _add_workspace_src_paths() -> None:
    root = Path(__file__).resolve().parents[1]
    src_paths = sorted(
        [
            *root.glob("apps/*/src"),
            *root.glob("libs/*/src"),
            *root.glob("plugins/*/src"),
        ]
    )

    for src_path in reversed(src_paths):
        src_str = str(src_path)
        if src_str not in sys.path:
            sys.path.insert(0, src_str)


_add_workspace_src_paths()
