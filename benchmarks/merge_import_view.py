"""Measure import-root merging with synthetic dependency package layouts."""

from __future__ import annotations

import argparse
import json
import shutil
import statistics
import tempfile
import time
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from pyrefly.private.wrapper.config import MergeStats, merge_site_package_dirs

_SCENARIOS = ("disjoint", "overlapping", "duplicate-physical-roots")


def _positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def _create_roots(
    directory: Path,
    scenario: str,
    root_count: int,
    files_per_root: int,
) -> list[Path]:
    roots = []
    aliases = []
    for root_index in range(root_count):
        root = directory / f"root_{root_index}"
        package = "shared" if scenario == "overlapping" else f"package_{root_index}"
        source = root / package / "nested"
        source.mkdir(parents=True)
        for file_index in range(files_per_root):
            (source / f"module_{root_index}_{file_index}.pyi").write_text(
                "value: int\n"
            )
        roots.append(root)
        if scenario == "duplicate-physical-roots":
            alias = directory / f"alias_{root_index}"
            alias.symlink_to(root, target_is_directory=True)
            aliases.append(alias)
    return roots + aliases


def benchmark_case(
    scenario: str,
    root_count: int,
    files_per_root: int,
    repeats: int,
) -> dict[str, object]:
    """Time only merging, with unchanged inputs and a new destination each time."""
    with tempfile.TemporaryDirectory(prefix="pyrefly_merge_benchmark_") as temporary:
        roots = _create_roots(Path(temporary), scenario, root_count, files_per_root)
        original_roots = {str(root) for root in roots}
        samples = []
        elapsed_times = []
        for _ in range(repeats):
            stats = MergeStats()
            started = time.perf_counter()
            merged = merge_site_package_dirs(roots, stats=stats)
            elapsed = time.perf_counter() - started
            try:
                if stats.fallback:
                    raise RuntimeError(
                        f"{scenario}: merge fell back to the original roots"
                    )
                samples.append({"seconds": elapsed, **asdict(stats)})
                elapsed_times.append(elapsed)
            finally:
                for path in merged:
                    if path not in original_roots:
                        shutil.rmtree(path)

        return {
            "scenario": scenario,
            "physical_roots": root_count,
            "alias_roots": len(roots) - root_count,
            "import_roots": len(roots),
            "files_per_root": files_per_root,
            "distinct_files": root_count * files_per_root,
            "repeats": repeats,
            "median_seconds": statistics.median(elapsed_times),
            "samples": samples,
        }


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roots", type=_positive_int, default=500)
    parser.add_argument("--files-per-root", type=_positive_int, default=40)
    parser.add_argument("--repeats", type=_positive_int, default=5)
    parser.add_argument("--scenario", choices=("all", *_SCENARIOS), default="all")
    args = parser.parse_args(argv)
    scenarios = _SCENARIOS if args.scenario == "all" else (args.scenario,)
    for scenario in scenarios:
        result = benchmark_case(scenario, args.roots, args.files_per_root, args.repeats)
        print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
