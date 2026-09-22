from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path

import pytest

from pyrefly.private.wrapper import check_runner, cli, update_baseline_runner
from pyrefly.private.wrapper.utils import CommandResult

_PYREFLY_EXECUTABLE = str(
    (Path.cwd() / os.environ["PYREFLY_TEST_EXECUTABLE"]).absolute()
)


def _args(tmp_path: Path, source: Path) -> cli.UpdateBaselineOptions:
    return cli.UpdateBaselineOptions(
        pyrefly_executable=_PYREFLY_EXECUTABLE,
        base_config=None,
        source_file=[source],
        import_path=[],
        stub_import_path=[],
        transformed_dependency_path=[],
        bazel_bin_dir=tmp_path / "bin",
        python_platform="linux",
        python_version="3.13.11",
        output_baseline=tmp_path / "baseline.json",
        target_label="//app:lib",
        timeout=30,
    )


def _command_path(command: list[str | Path], option: str) -> Path:
    return Path(command[command.index(option) + 1])


def test_update_baseline_accepts_findings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A findings exit code still produces a successful update action."""
    source = tmp_path / "app.py"
    source.write_text("value = 1\n")
    args = _args(tmp_path, source)
    generated = b"generated baseline\n"

    def run_command(
        command: list[str | Path],
        **_kwargs: object,
    ) -> CommandResult:
        _command_path(command, "--baseline").write_bytes(generated)
        return CommandResult(1, "findings")

    monkeypatch.setattr(check_runner, "run_command", run_command)

    assert update_baseline_runner.run(args) == 0
    assert args.output_baseline.read_bytes() == generated


def test_update_baseline_does_not_seed_from_existing_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An existing artifact is removed before Pyrefly regenerates from scratch."""
    source = tmp_path / "app.py"
    source.write_text("value: int = 1\n")
    args = _args(tmp_path, source)
    args.output_baseline.write_text(json.dumps({"errors": [{"name": "stale-error"}]}))
    generated = b"generated baseline\n"

    def run_command(
        command: list[str | Path],
        **_kwargs: object,
    ) -> CommandResult:
        output = _command_path(command, "--baseline")
        assert not output.exists()
        output.write_bytes(generated)
        return CommandResult(0, "")

    monkeypatch.setattr(check_runner, "run_command", run_command)

    assert update_baseline_runner.run(args) == 0
    assert args.output_baseline.read_bytes() == generated


def test_update_baseline_writes_empty_output_for_excluded_sources(
    tmp_path: Path,
) -> None:
    """A skipped check still supplies the action's declared baseline output."""
    source = tmp_path / "app.py"
    source.write_text("value: int = 1\n")
    base_config = tmp_path / "pyrefly.toml"
    base_config.write_text(f'project-excludes = ["{source.as_posix()}"]\n')
    args = replace(
        _args(tmp_path, source),
        base_config=base_config,
        pyrefly_executable=str(tmp_path / "missing"),
    )

    assert update_baseline_runner.run(args) == 0
    assert args.output_baseline.read_text() == '{\n  "errors": []\n}\n'
