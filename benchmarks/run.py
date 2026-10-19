"""Benchmark the Pyrefly aspect using Bazel execution-log action durations."""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import uuid
from collections import Counter, defaultdict
from collections.abc import Iterator, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SCENARIOS = ("small", "namespace", "web")
MNEMONICS = ("PyreflyCheck", "PyreflyStubgen", "PyreflyMinify")
TIMING_FIELDS = ("pyrefly_seconds", "wrapper_seconds")


@dataclass(frozen=True)
class Action:
    target: str
    mnemonic: str
    runner: str
    execution_seconds: float
    total_seconds: float
    outputs: tuple[str, ...]

    @property
    def identity(self) -> tuple[str, str, tuple[str, ...]]:
        return self.target, self.mnemonic, self.outputs


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def execution_records(path: Path) -> Iterator[dict[str, Any]]:
    """Read Bazel's stream of concatenated protobuf-JSON messages."""
    contents = path.read_text(encoding="utf-8")
    decoder = json.JSONDecoder()
    offset = 0
    while offset < len(contents):
        if contents[offset].isspace():
            offset += 1
            continue
        record, offset = decoder.raw_decode(contents, offset)
        if not isinstance(record, dict):
            raise ValueError(f"Invalid execution-log message in {path}")
        yield record


def duration_seconds(value: str = "0s") -> float:
    if not value.endswith("s"):
        raise ValueError(f"Invalid execution-log duration: {value!r}")
    result = float(value[:-1])
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"Invalid execution-log duration: {value!r}")
    return result


def read_actions(path: Path) -> list[Action]:
    actions = []
    for record in execution_records(path):
        if record.get("mnemonic") not in MNEMONICS:
            continue
        if record.get("cacheHit", False):
            raise RuntimeError(
                f"Cached Pyrefly action in {path}: {record['targetLabel']}"
            )
        if record.get("exitCode", 0) != 0 or record.get("status", "") not in (
            "",
            "SUCCESS",
        ):
            raise RuntimeError(
                f"Failed Pyrefly action in {path}: {record['targetLabel']}"
            )
        runner = record.get("runner", "")
        if "sandbox" not in runner:
            raise RuntimeError(
                f"Expected a local sandbox runner, got {runner!r} in {path}"
            )
        metrics = record.get("metrics", {})
        # Bazel omits duration fields when their measured millisecond value is zero.
        actions.append(
            Action(
                target=record["targetLabel"],
                mnemonic=record["mnemonic"],
                runner=runner,
                execution_seconds=duration_seconds(
                    metrics.get("executionWallTime", "0s")
                ),
                total_seconds=duration_seconds(metrics.get("totalTime", "0s")),
                outputs=tuple(sorted(record.get("listedOutputs", []))),
            )
        )
    return sorted(actions, key=lambda action: action.identity)


def build(
    bazel: Sequence[str],
    workspace: Path,
    scenario: str,
    jobs: int,
    directory: Path,
) -> tuple[list[Action], float]:
    target = f"//scenarios/{scenario}:{scenario}"
    directory.mkdir()
    execution_log = directory / "execution.json"
    build_log = directory / "build.log"
    command = [
        *bazel,
        "build",
        target,
        "--remote_executor=",
        "--remote_cache=",
        "--disk_cache=",
        "--noremote_accept_cached",
        "--noremote_upload_local_results",
        f"--jobs={jobs}",
        "--output_groups=+pyrefly_otlp_traces",
        f"--modify_execution_info=Pyrefly(Check|Stubgen|Minify)=+benchmark-{uuid.uuid4().hex}",
        f"--execution_log_json_file={execution_log}",
        "--noexecution_log_sort",
        *(f"--strategy={mnemonic}=sandboxed" for mnemonic in MNEMONICS),
    ]
    with build_log.open("wb") as log:
        started = time.perf_counter()
        result = subprocess.run(
            command, cwd=workspace, stdout=log, stderr=subprocess.STDOUT
        )
        wall_seconds = time.perf_counter() - started
    if result.returncode:
        raise RuntimeError(f"Bazel build failed ({result.returncode}); see {build_log}")
    actions = read_actions(execution_log)
    if not any(
        action.mnemonic == "PyreflyCheck" and action.target == target
        for action in actions
    ):
        raise RuntimeError(f"Missing executed check for {target}; see {execution_log}")
    if not any(action.mnemonic == "PyreflyStubgen" for action in actions):
        raise RuntimeError(f"No external stubgen actions executed; see {execution_log}")
    return actions, wall_seconds


def copy_traces(
    actions: Sequence[Action], execution_root: Path, directory: Path
) -> list[str]:
    """Preserve trace files for inspection without reading their contents."""
    copies = []
    for action in actions:
        for output in action.outputs:
            if not output.endswith("_otlp_trace.jsonl"):
                continue
            source = execution_root / output
            if source.is_file():
                destination = directory / "traces" / output
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
                copies.append(str(destination))
    return copies


def action_report(
    action: Action, execution_root: Path, directory: Path
) -> dict[str, Any]:
    traces = copy_traces([action], execution_root, directory)
    pyrefly_seconds = None
    if action.mnemonic == "PyreflyMinify":
        pyrefly_seconds = 0.0
    elif len(traces) == 1:
        pyrefly_seconds = read_pyrefly_seconds(Path(traces[0]))
    if (
        pyrefly_seconds is not None
        and not 0 <= pyrefly_seconds <= action.execution_seconds
    ):
        pyrefly_seconds = None
    return {
        **asdict(action),
        "traces": traces,
        "pyrefly_seconds": pyrefly_seconds,
        "wrapper_seconds": action.execution_seconds - pyrefly_seconds
        if pyrefly_seconds is not None
        else None,
    }


def read_pyrefly_seconds(path: Path) -> float | None:
    """Sum Pyrefly subprocess spans, raising on malformed trace data."""
    durations = []
    try:
        with path.open(encoding="utf-8") as source:
            for line in source:
                if not line.strip():
                    continue
                for resource in json.loads(line)["resourceSpans"]:
                    for scope in resource["scopeSpans"]:
                        for span in scope["spans"]:
                            if span.get("name") in {
                                "pyrefly.wrapper.check.run-pyrefly",
                                "pyrefly.wrapper.stubgen.run-pyrefly",
                            }:
                                duration = int(span["endTimeUnixNano"]) - int(
                                    span["startTimeUnixNano"]
                                )
                                if duration < 0:
                                    raise ValueError(
                                        "Pyrefly span ends before it starts"
                                    )
                                durations.append(duration)
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        raise ValueError(f"Cannot parse OTLP trace {path}: {error}") from error
    return sum(durations) / 1_000_000_000 if durations else None


def timing_totals(actions: Sequence[dict[str, Any]]) -> dict[str, float | None]:
    """Leave totals unavailable when any action lacks its timing component."""
    return {
        field: sum(action[field] for action in actions)
        if all(action[field] is not None for action in actions)
        else None
        for field in TIMING_FIELDS
    }


def timing_statistics(samples: Sequence[dict[str, Any]]) -> dict[str, float | None]:
    return {
        f"{name}_{field}": calculate(sample[field] for sample in samples)
        if all(sample[field] is not None for sample in samples)
        else None
        for field in TIMING_FIELDS
        for name, calculate in (
            ("median", statistics.median),
            ("min", min),
            ("max", max),
            ("stddev", statistics.pstdev),
        )
    }


def benchmark(
    bazel: Sequence[str],
    workspace: Path,
    execution_root: Path,
    scenario: str,
    repeats: int,
    jobs: int,
    directory: Path,
) -> dict[str, object]:
    target = f"//scenarios/{scenario}:{scenario}"
    directory.mkdir()
    print(f"Warming up {target}; artifacts: {directory}", file=sys.stderr, flush=True)
    warmup, _ = build(bazel, workspace, scenario, jobs, directory / "warmup")
    copy_traces(warmup, execution_root, directory / "warmup")
    expected = Counter(action.identity for action in warmup)
    samples = []
    elapsed_times = []
    per_action: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for repetition in range(repeats):
        output = directory / f"sample_{repetition + 1}"
        print(
            f"Measuring {target} ({repetition + 1}/{repeats})",
            file=sys.stderr,
            flush=True,
        )
        actions, wall_seconds = build(bazel, workspace, scenario, jobs, output)
        if Counter(action.identity for action in actions) != expected:
            raise RuntimeError(
                f"Executed Pyrefly actions differ from warm-up; see {output / 'execution.json'}"
            )
        action_seconds = sum(action.execution_seconds for action in actions)
        elapsed_times.append(action_seconds)
        reports = [action_report(action, execution_root, output) for action in actions]
        for action in reports:
            per_action[action["target"], action["mnemonic"]].append(action)
        samples.append(
            {
                "action_seconds": action_seconds,
                **timing_totals(reports),
                "command_wall_seconds": wall_seconds,
                "execution_log": str(output / "execution.json"),
                "build_log": str(output / "build.log"),
                "actions": reports,
            }
        )
    return {
        "scenario": scenario,
        "target": target,
        "jobs": jobs,
        "repeats": repeats,
        "median_action_seconds": statistics.median(elapsed_times),
        "min_action_seconds": min(elapsed_times),
        "max_action_seconds": max(elapsed_times),
        "stddev_action_seconds": statistics.pstdev(elapsed_times),
        **timing_statistics(samples),
        "per_action": [
            {
                "target": target,
                "mnemonic": mnemonic,
                "median_seconds": statistics.median(
                    action["execution_seconds"] for action in values
                ),
                "min_seconds": min(action["execution_seconds"] for action in values),
                "max_seconds": max(action["execution_seconds"] for action in values),
                "stddev_seconds": statistics.pstdev(
                    action["execution_seconds"] for action in values
                ),
                **timing_statistics(values),
            }
            for (target, mnemonic), values in sorted(per_action.items())
        ],
        "samples": samples,
    }


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=("all", *SCENARIOS), default="all")
    parser.add_argument("--repeats", type=positive_int, default=5)
    parser.add_argument("--jobs", type=positive_int, default=1)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--bazel", default="bazel")
    args = parser.parse_args(argv)
    try:
        repository = Path(
            os.environ.get(
                "BUILD_WORKSPACE_DIRECTORY", Path(__file__).absolute().parent.parent
            )
        )
        workspace = repository / "benchmarks/workspace"
        if not (workspace / "MODULE.bazel").is_file():
            raise ValueError(
                "Benchmark workspace not found; run from the source checkout with bazel run //benchmarks:run"
            )
        executable = shutil.which(args.bazel)
        if executable is None:
            raise ValueError(f"Bazel executable not found: {args.bazel}")
        bazel = [str(Path(executable).absolute()), "--nohome_rc", "--nosystem_rc"]
        execution_root = Path(
            subprocess.check_output(
                [*bazel, "info", "execution_root"], cwd=workspace, text=True
            ).strip()
        )
        if args.output_dir is None:
            output = Path(tempfile.mkdtemp(prefix="pyrefly_aspect_benchmark_"))
        else:
            output = args.output_dir.absolute()
            output.mkdir(parents=True)
        scenarios = SCENARIOS if args.scenario == "all" else (args.scenario,)
        for scenario in scenarios:
            result = benchmark(
                bazel,
                workspace,
                execution_root,
                scenario,
                args.repeats,
                args.jobs,
                output / scenario,
            )
            report = output / scenario / "summary.json"
            report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            print(
                json.dumps(
                    {
                        "scenario": scenario,
                        **{
                            key: value
                            for key, value in result.items()
                            if key.startswith(("median_", "min_", "max_", "stddev_"))
                        },
                        "summary": str(report),
                    }
                ),
                flush=True,
            )
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
