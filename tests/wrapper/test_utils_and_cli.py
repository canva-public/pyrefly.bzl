from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import pytest

from pyrefly.private.wrapper import (
    check_runner,
    cli,
    display_warnings,
    extract_config,
    minify_runner,
    stubgen_runner,
    update_baseline_runner,
    utils,
)


def test_cli_dispatches_all_subcommands(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each subcommand parses its flags and invokes the corresponding operation."""
    checks: list[cli.CheckOptions] = []
    displays: list[cli.DisplayWarningsOptions] = []
    extracts: list[cli.ExtractConfigOptions] = []
    minifies: list[cli.MinifyOptions] = []
    stubgens: list[cli.StubgenOptions] = []
    updates: list[cli.UpdateBaselineOptions] = []
    monkeypatch.setattr(
        check_runner,
        "run",
        lambda options: checks.append(options) or 0,
    )
    monkeypatch.setattr(
        display_warnings,
        "run",
        lambda options: displays.append(options) or 0,
    )
    monkeypatch.setattr(
        extract_config,
        "run",
        lambda options: extracts.append(options) or 0,
    )
    monkeypatch.setattr(
        minify_runner,
        "run",
        lambda options: minifies.append(options) or 0,
    )
    monkeypatch.setattr(
        stubgen_runner,
        "run",
        lambda options: stubgens.append(options) or 0,
    )
    monkeypatch.setattr(
        update_baseline_runner,
        "run",
        lambda options: updates.append(options) or 0,
    )

    assert (
        cli.main(
            [
                "extract-config",
                "--input-config",
                "pyproject.toml",
                "--output-config",
                "pyrefly.toml",
            ]
        )
        == 0
    )
    assert (
        cli.main(
            [
                "display-warnings",
                "--output-marker",
                "display.marker",
                "--check-marker",
                "check.marker",
                "--fulltext-output",
                "fulltext.txt",
            ]
        )
        == 0
    )
    assert (
        cli.main(
            [
                "update-baseline",
                "--pyrefly-executable",
                "tool",
                "--source-file",
                "app.py",
                "--bazel-bin-dir",
                "bin",
                "--python-platform",
                "linux",
                "--python-version",
                "3.12.7",
                "--output-baseline",
                "baseline.json",
                "--target-label",
                "//app:lib",
            ]
        )
        == 0
    )
    assert (
        cli.main(
            [
                "check",
                "--pyrefly-executable",
                "tool",
                "--source-file",
                "app.py",
                "--bazel-bin-dir",
                "bin",
                "--python-platform",
                "linux",
                "--python-version",
                "3.12.7",
                "--output-marker",
                "marker",
                "--output-fulltext",
                "fulltext.txt",
                "--output-json",
                "report.json",
                "--output-sarif",
                "report.sarif",
                "--target-label",
                "//app:lib",
                "--stale-message",
                "remove %s",
            ]
        )
        == 0
    )
    assert (
        cli.main(
            [
                "minify",
                "--output-dir",
                "minified",
                "--bazel-bin-dir",
                "bin",
                "--repository-root",
                ".",
                "--input-path",
                "dependency.py",
                "--mapped-stub-path",
                "mapped",
                "--mapped-stub-import-path",
                "mapped/site-packages",
            ]
        )
        == 0
    )
    assert (
        cli.main(
            [
                "stubgen",
                "--pyrefly-executable",
                "tool",
                "--output-dir",
                "stubs",
                "--bazel-bin-dir",
                "bin",
                "--python-platform",
                "linux",
                "--python-version",
                "3.12.7",
                "--repository-root",
                ".",
                "--retain-repository-root",
                "--mapped-stub-path",
                "mapped",
                "--mapped-stub-import-path",
                "mapped/site-packages",
            ]
        )
        == 0
    )

    assert len(checks) == 1
    assert checks[0].pyrefly_executable == "tool"
    assert checks[0].source_file == [Path("app.py")]
    assert checks[0].bazel_bin_dir == Path("bin")
    assert checks[0].output_marker == Path("marker")
    assert checks[0].output_fulltext == Path("fulltext.txt")
    assert checks[0].output_json == Path("report.json")
    assert checks[0].output_sarif == Path("report.sarif")
    assert checks[0].python_platform == "linux"
    assert checks[0].python_version == "3.12.7"
    assert checks[0].target_label == "//app:lib"
    assert checks[0].stale_message == "remove %s"
    assert len(displays) == 1
    assert displays[0].output_marker == Path("display.marker")
    assert displays[0].check_marker == Path("check.marker")
    assert displays[0].fulltext_output == Path("fulltext.txt")
    assert len(extracts) == 1
    assert extracts[0].input_config == Path("pyproject.toml")
    assert extracts[0].output_config == Path("pyrefly.toml")
    assert len(updates) == 1
    assert updates[0].output_baseline == Path("baseline.json")
    assert updates[0].source_file == [Path("app.py")]
    assert updates[0].target_label == "//app:lib"
    assert len(minifies) == 1
    assert minifies[0].output_dir == Path("minified")
    assert minifies[0].repository_root == Path(".")
    assert minifies[0].input_path == [Path("dependency.py")]
    assert minifies[0].mapped_stub_path == [Path("mapped")]
    assert minifies[0].mapped_stub_import_path == [Path("mapped/site-packages")]
    assert len(stubgens) == 1
    assert stubgens[0].pyrefly_executable == "tool"
    assert stubgens[0].output_dir == Path("stubs")
    assert stubgens[0].bazel_bin_dir == Path("bin")
    assert stubgens[0].python_platform == "linux"
    assert stubgens[0].python_version == "3.12.7"
    assert stubgens[0].repository_root == Path(".")
    assert stubgens[0].retain_repository_root is True
    assert stubgens[0].mapped_stub_path == [Path("mapped")]
    assert stubgens[0].mapped_stub_import_path == [Path("mapped/site-packages")]


def test_cli_accepts_configured_log_level(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI logging honors the requested level and optional destination file."""
    log_file = tmp_path / "logs" / "wrapper.log"

    def run(_options: cli.StubgenOptions) -> int:
        stubgen_runner.logger.info("stubgen ran")
        return 0

    monkeypatch.setattr(stubgen_runner, "run", run)

    assert (
        cli.main(
            [
                "stubgen",
                "--log-level",
                "info",
                "--log-file",
                str(log_file),
                "--pyrefly-executable",
                "tool",
                "--output-dir",
                "stubs",
                "--bazel-bin-dir",
                "bin",
                "--python-platform",
                "linux",
                "--python-version",
                "3.13.11",
                "--repository-root",
                ".",
            ]
        )
        == 0
    )

    assert logging.getLogger("pyrefly").level == logging.INFO
    assert "stubgen ran" in log_file.read_text()


def test_cli_serialises_operation_trace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A trace contains related root and phase spans for the wrapper operation."""
    trace_file = tmp_path / "traces" / "minify.jsonl"
    source = tmp_path / "package.py"
    source.write_text("value = 1\n")
    monkeypatch.chdir(tmp_path)

    assert (
        cli.main(
            [
                "minify",
                "--otlp-trace-output",
                str(trace_file),
                "--output-dir",
                "minified",
                "--bazel-bin-dir",
                "bin",
                "--repository-root",
                ".",
                "--input-path",
                "package.py",
            ]
        )
        == 0
    )

    requests = [json.loads(line) for line in trace_file.read_text().splitlines()]
    resource_spans = [
        resource_spans
        for request in requests
        for resource_spans in request["resourceSpans"]
    ]
    traces = [
        span
        for resource in resource_spans
        for scope_spans in resource["scopeSpans"]
        for span in scope_spans["spans"]
    ]
    traces_by_name = {trace["name"]: trace for trace in traces}
    assert set(traces_by_name) == {
        "pyrefly.wrapper.minify",
        "pyrefly.wrapper.minify.collect-inputs",
        "pyrefly.wrapper.minify.copy-files",
        "pyrefly.wrapper.minify.finalize-output",
        "pyrefly.wrapper.minify.inspect-mapped-stubs",
        "pyrefly.wrapper.minify.resolve-source-layout",
    }

    root = traces_by_name["pyrefly.wrapper.minify"]
    assert {
        attribute["key"]: next(iter(attribute["value"].values()))
        for attribute in root["attributes"]
    } == {
        "pyrefly.wrapper.exit_code": "0",
        "pyrefly.wrapper.operation": "minify",
    }
    assert {
        attribute["key"]: next(iter(attribute["value"].values()))
        for attribute in resource_spans[0]["resource"]["attributes"]
    }["service.name"] == "pyrefly-bazel-wrapper"
    trace_ids = {trace["traceId"] for trace in traces}
    assert len(trace_ids) == 1
    assert "parentSpanId" not in root
    assert all(
        trace["parentSpanId"] == root["spanId"] for trace in traces if trace is not root
    )
    input_collection = traces_by_name["pyrefly.wrapper.minify.collect-inputs"]
    assert {
        attribute["key"]: next(iter(attribute["value"].values()))
        for attribute in input_collection["attributes"]
    } == {
        "pyrefly.file.count": "1",
        "pyrefly.input.count": "1",
    }


def test_cli_accepts_repeated_options_from_bazel_parameter_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bazel parameter files preserve repeated command-line options."""
    observed: list[cli.StubgenOptions] = []
    monkeypatch.setattr(
        stubgen_runner,
        "run",
        lambda options: observed.append(options) or 0,
    )
    parameter_file = tmp_path / "wrapper.params"
    parameter_file.write_text(
        "\n".join(
            [
                "stubgen",
                "--pyrefly-executable",
                "tool",
                "--output-dir",
                "stubs",
                "--bazel-bin-dir",
                "bin",
                "--python-platform",
                "linux",
                "--python-version",
                "3.13.11",
                "--repository-root",
                ".",
                "--input-path",
                "package.py",
                "--input-path",
                "other.py",
            ]
        )
    )

    assert cli.main([f"@{parameter_file}"]) == 0

    assert observed[0].input_path == [Path("package.py"), Path("other.py")]


def test_resolve_executable_expands_relative_path_inside_spawn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An execroot-relative tool path resolves after the action starts."""
    executable = tmp_path / "bazel-out" / "exec" / "pyrefly"
    executable.parent.mkdir(parents=True)
    executable.write_text("#!/bin/sh\nexit 0\n")
    executable.chmod(0o755)
    monkeypatch.chdir(tmp_path)

    assert utils.resolve_executable("bazel-out/exec/pyrefly") == executable


def test_run_command_preserves_shell_metacharacters() -> None:
    """Subcommand arguments are passed literally without shell interpretation."""
    argument = "$HOME; echo injected"
    result = utils.run_command(
        [
            sys.executable,
            "-c",
            "import sys; print(sys.argv[1])",
            argument,
        ],
        timeout=5,
    )

    assert result.returncode == 0
    assert result.output == argument + "\n"


def test_run_command_splices_stderr_into_stdout() -> None:
    """Subprocess stdout and stderr retain order in one diagnostics stream."""
    result = utils.run_command(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "sys.stdout.write('stdout\\n'); sys.stdout.flush(); "
                "sys.stderr.write('stderr\\n'); sys.stderr.flush()"
            ),
        ],
        timeout=5,
    )

    assert result.output == "stdout\nstderr\n"
