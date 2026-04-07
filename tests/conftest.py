from pathlib import Path
import sys


def _add_workspace_src_paths() -> None:
    root = Path(__file__).resolve().parents[1]
    for src_path in root.glob("**/src"):
        src_str = str(src_path)
        if src_str not in sys.path:
            sys.path.insert(0, src_str)


_add_workspace_src_paths()
