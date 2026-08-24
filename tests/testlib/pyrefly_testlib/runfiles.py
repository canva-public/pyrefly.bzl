"""Runfiles lookup helpers for integration assertions."""

import os
from pathlib import Path


def workspace_runfile(path: str) -> Path:
    """Return a runfile beneath the consuming test workspace."""
    return Path(os.environ["TEST_SRCDIR"], os.environ["TEST_WORKSPACE"], path)


def find_runfile(
    suffix: str,
    *,
    root: Path | None = None,
    exclude: Path | None = None,
    containing: str | None = None,
) -> Path:
    """Find one runfile whose path ends with the requested suffix."""
    search_root = root or Path(os.environ["TEST_SRCDIR"])
    for directory, _, filenames in os.walk(search_root, followlinks=True):
        for filename in filenames:
            candidate = Path(directory, filename)
            candidate_path = candidate.as_posix()
            if (
                candidate != exclude
                and candidate_path.endswith(suffix)
                and (containing is None or containing in candidate_path)
            ):
                return candidate
    raise AssertionError(f"Could not find runfile ending with {suffix!r}")
