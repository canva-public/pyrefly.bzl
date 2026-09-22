"""Display warning reports produced by Pyrefly checks."""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING

from opentelemetry import trace

if TYPE_CHECKING:
    from .cli import DisplayWarningsOptions

tracer = trace.get_tracer(__name__)


def run(args: DisplayWarningsOptions) -> int:
    """Print relevant findings and create the action's output marker."""
    with tracer.start_as_current_span("pyrefly.wrapper.display-warnings.read") as span:
        metadata = json.loads(args.check_marker.read_text(encoding="utf-8"))
        should_display = (
            metadata["expected_failure"] and metadata["exit_code"] != 0
        ) or metadata["has_warnings"]
        output = (
            args.fulltext_output.read_text(encoding="utf-8").strip()
            if should_display
            else ""
        )
        span.set_attribute("pyrefly.warning.present", bool(output))
        span.set_attribute("pyrefly.warning.size", len(output))
    with tracer.start_as_current_span("pyrefly.wrapper.display-warnings.print"):
        if output:
            print(output, file=sys.stdout)

    with tracer.start_as_current_span("pyrefly.wrapper.display-warnings.write-marker"):
        args.output_marker.parent.mkdir(parents=True, exist_ok=True)
        args.output_marker.touch()
    return 0
