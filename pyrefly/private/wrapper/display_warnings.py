"""Display warning reports produced by Pyrefly checks."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .cli import DisplayWarningsOptions


def run(args: DisplayWarningsOptions) -> int:
    """Print a warning report and create the action's output marker."""
    warning = args.warning_file.read_text(encoding="utf-8").strip()
    if warning:
        print(warning, file=sys.stderr)

    args.output_marker.parent.mkdir(parents=True, exist_ok=True)
    args.output_marker.touch()
    return 0
