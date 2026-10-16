"""Check benchmark output and failed-measurement handling without timing thresholds."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmarks import merge_import_view
from pyrefly.private.wrapper.config import MergeStats


@pytest.mark.parametrize("roots", [1, 2])
def test_reports_comparable_scenarios(
    roots: int, capsys: pytest.CaptureFixture[str]
) -> None:
    """All scenarios report the same distinct files and each repeat's merge work."""
    merge_import_view.main(
        ["--roots", str(roots), "--files-per-root", "3", "--repeats", "2"]
    )
    results = [json.loads(line) for line in capsys.readouterr().out.splitlines()]

    assert [result["scenario"] for result in results] == [
        "disjoint",
        "overlapping",
        "duplicate-physical-roots",
    ]
    for result in results:
        assert result["physical_roots"] == roots
        assert result["distinct_files"] == roots * 3
        assert result["files_per_root"] == 3
        aliases = roots if result["scenario"] == "duplicate-physical-roots" else 0
        assert result["alias_roots"] == aliases
        assert result["import_roots"] == roots + aliases
        assert result["repeats"] == 2
        assert isinstance(result["median_seconds"], float)
        assert len(result["samples"]) == 2
        for sample in result["samples"]:
            assert isinstance(sample["seconds"], float)
            assert isinstance(sample["entries_visited"], int)
            assert isinstance(sample["directory_collisions"], int)
            assert isinstance(sample["symlinks_created"], int)
            assert sample["fallback"] is False


def test_rejects_fallback_measurements(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failed merge cannot appear as a successful, fast benchmark sample."""

    def fallback(roots: list[Path], *, stats: MergeStats) -> list[str]:
        stats.fallback = True
        return [str(root) for root in roots]

    monkeypatch.setattr(merge_import_view, "merge_site_package_dirs", fallback)
    with pytest.raises(RuntimeError, match="merge fell back"):
        merge_import_view.main(
            ["--roots", "2", "--files-per-root", "1", "--repeats", "1"]
        )
