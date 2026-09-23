"""Run the Pyrefly aspect in baseline-update mode and copy its outputs."""

from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

_OUTPUT_GROUP = "pyrefly_updated_baseline"
_ASPECT_MODE = "update_baseline"


class BaselineUpdaterError(RuntimeError):
    """The requested baselines could not be copied into the workspace."""


@dataclass(frozen=True)
class UpdateSummary:
    created: int = 0
    updated: int = 0
    deleted: int = 0
    unchanged: int = 0


def _local_path(file: dict[str, Any]) -> Path:
    uri = file["uri"]
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        raise BaselineUpdaterError(f"Baseline output is not local: {uri}")
    return Path(unquote(parsed.path))


def _files_from_named_set(
    identifier: str,
    named_sets: dict[str, dict[str, Any]],
    seen: set[str],
) -> list[Path]:
    if identifier in seen:
        return []
    seen.add(identifier)
    named_set = named_sets[identifier]
    files = [_local_path(file) for file in named_set.get("files", [])]
    for child in named_set.get("fileSets", []):
        files.extend(_files_from_named_set(child["id"], named_sets, seen))
    return files


def read_updated_baselines(build_event_file: Path) -> dict[str, Path]:
    """Read target-to-output mappings from a line-delimited JSON BEP file."""
    events = [
        json.loads(line) for line in build_event_file.read_text().splitlines() if line
    ]
    named_sets = {
        event["id"]["namedSet"]["id"]: event["namedSetOfFiles"]
        for event in events
        if "namedSet" in event.get("id", {})
    }

    outputs: dict[str, Path] = {}
    for event in events:
        completed_id = event.get("id", {}).get("targetCompleted")
        if completed_id is None:
            continue
        for output_group in event.get("completed", {}).get("outputGroup", []):
            if output_group.get("name") != _OUTPUT_GROUP:
                continue
            files: list[Path] = []
            for file_set in output_group.get("fileSets", []):
                files.extend(_files_from_named_set(file_set["id"], named_sets, set()))
            if len(files) != 1:
                raise BaselineUpdaterError(
                    f"Expected one updated baseline for {completed_id['label']}, "
                    f"found {len(files)}"
                )
            outputs[completed_id["label"]] = files[0]
    return outputs


def baseline_source_path(
    workspace: Path,
    baselines_package: str,
    target_label: str,
) -> Path:
    """Map a first-party target label to its checked-in baseline path."""
    if target_label.startswith("@@//"):
        target_label = target_label[2:]
    elif target_label.startswith("@//"):
        target_label = target_label[1:]
    if not target_label.startswith("//") or ":" not in target_label:
        raise BaselineUpdaterError(
            f"Cannot update a baseline for external target {target_label}"
        )
    package, name = target_label[2:].split(":", 1)
    if not name or "/" in name:
        raise BaselineUpdaterError(
            f"Target names containing '/' are not supported: {target_label}"
        )
    return workspace / baselines_package / package / f"{name}.json"


def _atomic_write(destination: Path, content: bytes) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(destination.stat().st_mode) if destination.exists() else 0o644
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            prefix=f".{destination.name}.",
            delete=False,
        ) as temporary:
            temporary.write(content)
            temporary_path = Path(temporary.name)
        temporary_path.chmod(mode)
        temporary_path.replace(destination)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def copy_updated_baselines(
    workspace: Path,
    baselines_package: str,
    outputs: dict[str, Path],
) -> UpdateSummary:
    """Copy non-empty baselines and remove baselines for clean targets."""
    created = updated = deleted = unchanged = 0
    for target_label, output in sorted(outputs.items()):
        destination = baseline_source_path(
            workspace,
            baselines_package,
            target_label,
        )
        content = output.read_bytes()
        document = json.loads(content)
        errors = document["errors"]
        if not errors:
            if destination.exists():
                destination.unlink()
                deleted += 1
                print(f"Deleted {destination.relative_to(workspace)}")
            else:
                unchanged += 1
            continue
        if destination.exists() and destination.read_bytes() == content:
            unchanged += 1
            continue
        existed = destination.exists()
        _atomic_write(destination, content)
        if existed:
            updated += 1
            verb = "Updated"
        else:
            created += 1
            verb = "Created"
        print(f"{verb} {destination.relative_to(workspace)}")
    return UpdateSummary(created, updated, deleted, unchanged)


def _run_build(
    bazel: str,
    workspace: Path,
    target_patterns: list[str],
    build_event_file: Path,
    target_pattern_file: Path | None = None,
) -> int:
    command = [
        bazel,
        "build",
        f"--aspects_parameters=pyrefly_mode={_ASPECT_MODE}",
        f"--output_groups={_OUTPUT_GROUP}",
        "--run_validations=false",
        "--remote_download_outputs=toplevel",
        f"--build_event_json_file={build_event_file}",
        "--build_event_json_file_path_conversion=no",
    ]
    if target_pattern_file is not None:
        command.append(f"--target_pattern_file={target_pattern_file}")
    command.extend(target_patterns)
    try:
        return subprocess.run(command, cwd=workspace, check=False).returncode
    except OSError as error:
        raise BaselineUpdaterError(f"Unable to run {bazel!r}: {error}") from error


def _parse_arguments(argv: list[str]) -> tuple[list[str], Path | None]:
    parser = argparse.ArgumentParser(
        description="Update per-target Pyrefly baselines",
    )
    parser.add_argument(
        "--target_pattern_file",
        type=Path,
        help="Read Bazel target patterns from this file",
    )
    parser.add_argument("target_patterns", nargs="*")
    arguments = parser.parse_args(argv)
    if arguments.target_pattern_file is not None and arguments.target_patterns:
        parser.error(
            "--target_pattern_file cannot be combined with positional target patterns"
        )
    if arguments.target_pattern_file is None and not arguments.target_patterns:
        parser.error("provide target patterns or --target_pattern_file")
    return arguments.target_patterns, arguments.target_pattern_file


def main(argv: list[str] | None = None) -> int:
    target_patterns, target_pattern_file = _parse_arguments(
        list(sys.argv[1:] if argv is None else argv)
    )
    try:
        workspace_value = os.environ.get("BUILD_WORKSPACE_DIRECTORY")
        if workspace_value is None:
            raise BaselineUpdaterError(
                "BUILD_WORKSPACE_DIRECTORY is not set; run this target with bazel run"
            )
        baselines_package = os.environ["PYREFLY_BASELINES_PACKAGE"]
        workspace = Path(workspace_value)
        working_directory = Path(
            os.environ.get("BUILD_WORKING_DIRECTORY", workspace_value)
        )
        if target_pattern_file is not None and not target_pattern_file.is_absolute():
            target_pattern_file = working_directory / target_pattern_file
        bazel = os.environ.get("BAZEL", "bazel")

        with tempfile.TemporaryDirectory(prefix="pyrefly-baselines-") as directory:
            build_event_file = Path(directory) / "build-events.json"
            returncode = _run_build(
                bazel,
                workspace,
                target_patterns,
                build_event_file,
                target_pattern_file,
            )
            if returncode != 0:
                return returncode
            outputs = read_updated_baselines(build_event_file)
            if not outputs:
                raise BaselineUpdaterError(
                    "The build produced no eligible Pyrefly baseline outputs"
                )
            summary = copy_updated_baselines(
                workspace,
                baselines_package,
                outputs,
            )
        print(
            "Pyrefly baselines: "
            f"{summary.created} created, {summary.updated} updated, "
            f"{summary.deleted} deleted, {summary.unchanged} unchanged"
        )
        return 0
    except (BaselineUpdaterError, KeyError, json.JSONDecodeError, OSError) as error:
        print(f"Pyrefly baseline update failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
