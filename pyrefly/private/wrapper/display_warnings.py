"""Display warning reports produced by Pyrefly checks."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from opentelemetry import trace

if TYPE_CHECKING:
    from .cli import DisplayWarningsOptions

tracer = trace.get_tracer(__name__)


def run(args: DisplayWarningsOptions) -> int:
    """Print a warning report and create the action's output marker."""
    with tracer.start_as_current_span("pyrefly.wrapper.display-warnings.read") as span:
        warning = args.warning_file.read_text(encoding="utf-8").strip()
        span.set_attribute("pyrefly.warning.present", bool(warning))
        span.set_attribute("pyrefly.warning.size", len(warning))
    with tracer.start_as_current_span("pyrefly.wrapper.display-warnings.print"):
        if warning:
            print(warning, file=sys.stderr)

    with tracer.start_as_current_span("pyrefly.wrapper.display-warnings.write-marker"):
        args.output_marker.parent.mkdir(parents=True, exist_ok=True)
        args.output_marker.touch()
    return 0
