from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path

from pyrefly.private.wrapper import cli, update_baseline_runner

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


def test_update_baseline_accepts_type_errors(tmp_path: Path) -> None:
    """Type errors produce a complete baseline instead of failing the action."""
    source = tmp_path / "app.py"
    source.write_text('value: int = "wrong"\n')
    args = _args(tmp_path, source)

    assert update_baseline_runner.run(args) == 0
    errors = json.loads(args.output_baseline.read_text())["errors"]
    assert len(errors) == 1
    assert errors[0]["name"] == "bad-assignment"


def test_update_baseline_does_not_seed_from_existing_output(tmp_path: Path) -> None:
    """An existing artifact is removed before Pyrefly regenerates from scratch."""
    source = tmp_path / "app.py"
    source.write_text("value: int = 1\n")
    args = _args(tmp_path, source)
    args.output_baseline.write_text(json.dumps({"errors": [{"name": "stale-error"}]}))

    assert update_baseline_runner.run(args) == 0
    assert json.loads(args.output_baseline.read_text()) == {"errors": []}


def test_update_baseline_removes_inherited_baseline(tmp_path: Path) -> None:
    """A shared baseline setting cannot affect fresh per-target generation."""
    source = tmp_path / "app.py"
    source.write_text("value: int = 1\n")
    base_config = tmp_path / "pyrefly.toml"
    base_config.write_text('baseline = "missing-shared-baseline.json"\n')
    args = replace(_args(tmp_path, source), base_config=base_config)

    assert update_baseline_runner.run(args) == 0
    assert json.loads(args.output_baseline.read_text()) == {"errors": []}


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
    assert json.loads(args.output_baseline.read_text()) == {"errors": []}
