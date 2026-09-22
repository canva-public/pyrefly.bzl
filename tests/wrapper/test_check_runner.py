from __future__ import annotations

import logging
import os
from dataclasses import replace
from pathlib import Path

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from pyrefly.private.wrapper import check_runner, cli
from pyrefly.private.wrapper.utils import WrapperError

_PYREFLY_EXECUTABLE = str(
    (Path.cwd() / os.environ["PYREFLY_TEST_EXECUTABLE"]).absolute()
)


def _args(
    tmp_path: Path,
    source: Path,
    *,
    expected: bool = False,
) -> cli.CheckOptions:
    return cli.CheckOptions(
        pyrefly_executable=_PYREFLY_EXECUTABLE,
        base_config=None,
        source_file=[source],
        import_path=[],
        stub_import_path=[],
        transformed_dependency_path=[],
        bazel_bin_dir=tmp_path / "bin",
        python_platform="linux",
        python_version="3.13.11",
        output_marker=tmp_path / "result.marker",
        warning_output=None,
        target_label="//app:lib",
        expected_to_fail=expected,
        stale_message="Remove stale expected failure for %s" if expected else None,
        timeout=30,
    )


def _source(tmp_path: Path, content: str) -> Path:
    source = tmp_path / "app.py"
    source.write_text(content)
    return source


@pytest.mark.parametrize(
    ("content", "expected", "wrapper_code"),
    [
        ("value: int = 1\n", False, 0),
        ('value: int = "wrong"\n', False, 1),
        ('value: int = "wrong"\n', True, 0),
        ("value: int = 1\n", True, 1),
    ],
)
def test_expected_failure_state_machine_uses_real_pyrefly(
    tmp_path: Path,
    content: str,
    expected: bool,
    wrapper_code: int,
) -> None:
    """Check results implement the strict expected-failure ratchet."""
    args = _args(tmp_path, _source(tmp_path, content), expected=expected)

    assert check_runner.run(args) == wrapper_code
    assert args.output_marker.is_file()


def test_check_trace_separates_preparation_from_pyrefly_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Check traces expose preparation phases and the Pyrefly subprocess."""
    args = _args(tmp_path, _source(tmp_path, "value: int = 1\n"))
    provider = TracerProvider()
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer(__name__)
    monkeypatch.setattr(check_runner, "tracer", tracer)

    with tracer.start_as_current_span("pyrefly.wrapper.check"):
        assert check_runner.run(args) == 0

    spans_by_name = {span.name: span for span in exporter.get_finished_spans()}
    assert set(spans_by_name) == {
        "pyrefly.wrapper.check",
        "pyrefly.wrapper.check.build-config",
        "pyrefly.wrapper.check.collect-inputs",
        "pyrefly.wrapper.check.materialize-bundled-stubs",
        "pyrefly.wrapper.check.materialize-import-view",
        "pyrefly.wrapper.check.plan-import-view",
        "pyrefly.wrapper.check.resolve-executable",
        "pyrefly.wrapper.check.resolve-source-layout",
        "pyrefly.wrapper.check.run-pyrefly",
        "pyrefly.wrapper.check.write-config",
    }
    subprocess = spans_by_name["pyrefly.wrapper.check.run-pyrefly"]
    assert subprocess.attributes is not None
    assert dict(subprocess.attributes) == {
        "pyrefly.source.count": 1,
        "pyrefly.timeout.seconds": 30,
        "pyrefly.wrapper.exit_code": 0,
    }
    provider.shutdown()


def test_marker_is_created_before_check_validation(tmp_path: Path) -> None:
    """The marker exists even when invalid arguments make the check fail."""
    args = replace(
        _args(tmp_path, _source(tmp_path, "value: int = 1\n")),
        source_file=[],
    )

    with pytest.raises(WrapperError, match="source-file"):
        check_runner.run(args)
    assert args.output_marker.is_file()


def test_stale_expected_failure_uses_custom_message(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A passing expected failure reports its label through the custom message."""
    args = replace(
        _args(
            tmp_path,
            _source(tmp_path, "value: int = 1\n"),
            expected=True,
        ),
        stale_message="Remove %s, then check %s again",
        target_label="@@//app:lib",
    )

    with caplog.at_level(
        logging.ERROR,
        logger="pyrefly.private.wrapper.check_runner",
    ):
        assert check_runner.run(args) == 1
    assert "Remove //app:lib, then check //app:lib again" in caplog.messages
    assert args.output_marker.is_file()


def test_expected_failure_writes_warning_report_at_error_log_level(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Ratcheted diagnostics are recorded independently of configured logging."""
    warning_output = tmp_path / "warnings" / "expected_failure.txt"
    args = replace(
        _args(
            tmp_path,
            _source(tmp_path, 'value: int = "wrong"\n'),
            expected=True,
        ),
        warning_output=warning_output,
    )

    with caplog.at_level(
        logging.ERROR,
        logger="pyrefly.private.wrapper.check_runner",
    ):
        assert check_runner.run(args) == 0

    warning = warning_output.read_text()
    assert "bad-assignment" in warning
    assert "Pyrefly type checking failed for //app:lib as expected" in warning


def test_all_configured_sources_excluded_is_a_noop(tmp_path: Path) -> None:
    """A target with every source excluded succeeds without invoking Pyrefly."""
    source = _source(tmp_path, "value: int = 1\n")
    base_config = tmp_path / "pyrefly.toml"
    base_config.write_text(f'project-excludes = ["{source.as_posix()}"]\n')
    args = replace(
        _args(tmp_path, source),
        base_config=base_config,
        pyrefly_executable=str(tmp_path / "missing"),
    )

    assert check_runner.run(args) == 0
    assert args.output_marker.is_file()
