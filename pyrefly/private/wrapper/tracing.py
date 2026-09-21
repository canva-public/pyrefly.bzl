"""OpenTelemetry tracing for wrapper operations."""

from __future__ import annotations

from pathlib import Path

from opentelemetry import trace
from opentelemetry.exporter.otlp.json.file import FileSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

_SERVICE_NAME = "pyrefly-bazel-wrapper"


def configure_tracing(output: Path | None) -> None:
    """Configure the process-wide tracer provider and OTLP/JSONL exporter."""
    if output is None:
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    provider = TracerProvider(resource=Resource.create({"service.name": _SERVICE_NAME}))
    provider.add_span_processor(SimpleSpanProcessor(FileSpanExporter(output)))
    trace.set_tracer_provider(provider)
