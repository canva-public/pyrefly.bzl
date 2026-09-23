from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from pyrefly.private.baseline_updater import updater as baseline_updater


def _write_baseline(path: Path, errors: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"errors": errors}, indent=2) + "\n")


def test_run_build_selects_update_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The nested build selects update mode on the configured Pyrefly aspect."""
    observed: list[list[str]] = []

    def run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        observed.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(baseline_updater.subprocess, "run", run)
    assert (
        baseline_updater._run_build(
            "bazel",
            tmp_path,
            ["//app:lib"],
            tmp_path / "events.json",
        )
        == 0
    )

    assert "--aspects_parameters=pyrefly_mode=update_baseline" in observed[0]


def test_read_updated_baselines_resolves_nested_named_sets(tmp_path: Path) -> None:
    """BEP output groups map target labels to their downloaded artifacts."""
    output = tmp_path / "bazel-bin" / "updated.json"
    _write_baseline(output, [{"name": "bad-assignment"}])
    build_events = tmp_path / "build-events.json"
    events = [
        {
            "id": {"namedSet": {"id": "file"}},
            "namedSetOfFiles": {"files": [{"uri": output.as_uri()}]},
        },
        {
            "id": {"namedSet": {"id": "group"}},
            "namedSetOfFiles": {"fileSets": [{"id": "file"}]},
        },
        {
            "id": {"targetCompleted": {"label": "//app:lib"}},
            "completed": {
                "outputGroup": [
                    {
                        "name": "pyrefly_updated_baseline",
                        "fileSets": [{"id": "group"}],
                    }
                ]
            },
        },
    ]
    build_events.write_text("".join(json.dumps(event) + "\n" for event in events))

    assert baseline_updater.read_updated_baselines(build_events) == {
        "//app:lib": output
    }


def test_copy_updated_baselines_creates_target_path(tmp_path: Path) -> None:
    """A new non-empty action output is copied byte-for-byte."""
    workspace = tmp_path / "workspace"
    output = tmp_path / "output.json"
    _write_baseline(output, [{"name": "bad-assignment"}])
    original_output = output.read_bytes()

    summary = baseline_updater.copy_updated_baselines(
        workspace,
        "pyrefly_baselines",
        {"//app/models:library": output},
    )

    destination = workspace / "pyrefly_baselines/app/models/library.json"
    assert destination.read_bytes() == original_output
    assert output.read_bytes() == original_output
    assert summary == baseline_updater.UpdateSummary(created=1)


def test_copy_updated_baselines_updates_changed_content(tmp_path: Path) -> None:
    """A changed non-empty output atomically replaces the checked-in baseline."""
    workspace = tmp_path / "workspace"
    destination = workspace / "baselines/app.json"
    output = tmp_path / "output.json"
    _write_baseline(destination, [{"name": "old"}])
    _write_baseline(output, [{"name": "new"}])
    generated = output.read_bytes()

    summary = baseline_updater.copy_updated_baselines(
        workspace,
        "baselines",
        {"//:app": output},
    )

    assert destination.read_bytes() == generated
    assert summary == baseline_updater.UpdateSummary(updated=1)


def test_copy_updated_baselines_deletes_clean_target(tmp_path: Path) -> None:
    """An empty generated baseline removes the corresponding source baseline."""
    workspace = tmp_path / "workspace"
    destination = workspace / "baselines/app.json"
    output = tmp_path / "output.json"
    _write_baseline(destination, [{"name": "old"}])
    _write_baseline(output, [])

    summary = baseline_updater.copy_updated_baselines(
        workspace,
        "baselines",
        {"//:app": output},
    )

    assert not destination.exists()
    assert summary == baseline_updater.UpdateSummary(deleted=1)


def test_copy_updated_baselines_leaves_matching_content_unchanged(
    tmp_path: Path,
) -> None:
    """Matching output does not rewrite an existing source baseline."""
    workspace = tmp_path / "workspace"
    destination = workspace / "baselines/app.json"
    output = tmp_path / "output.json"
    _write_baseline(destination, [{"name": "same"}])
    _write_baseline(output, [{"name": "same"}])
    original_mtime = destination.stat().st_mtime_ns

    summary = baseline_updater.copy_updated_baselines(
        workspace,
        "baselines",
        {"//:app": output},
    )

    assert destination.stat().st_mtime_ns == original_mtime
    assert summary == baseline_updater.UpdateSummary(unchanged=1)
