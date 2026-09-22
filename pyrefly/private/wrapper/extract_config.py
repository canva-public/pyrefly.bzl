"""Extract the Pyrefly table from a project configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from opentelemetry import trace

from .config import dump_toml, load_base_config

if TYPE_CHECKING:
    from .cli import ExtractConfigOptions

tracer = trace.get_tracer(__name__)


def run(args: ExtractConfigOptions) -> int:
    """Write an effective pyrefly.toml containing only Pyrefly settings."""
    input_config = args.input_config
    output_config = args.output_config
    with tracer.start_as_current_span("pyrefly.wrapper.extract-config.load") as span:
        settings = load_base_config(input_config)
        span.set_attribute("pyrefly.setting.count", len(settings))
    with tracer.start_as_current_span("pyrefly.wrapper.extract-config.write"):
        output_config.parent.mkdir(parents=True, exist_ok=True)
        output_config.write_text(dump_toml(settings), encoding="utf-8")
    return 0
