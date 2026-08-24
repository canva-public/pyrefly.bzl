"""PEP 561 mapped-stub overlays for dependency materialization actions."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .config import resolve_source_layout
from .input_context import MappedStubContext
from .source_utils import (
    collect_type_relevant_files,
    copy_file,
    native_extension_suffix,
    output_relative_path,
)


@dataclass(frozen=True)
class MappedStubOverlay:
    """A mapped stub distribution and the runtime interfaces it covers."""

    files: tuple[Path, ...]
    roots: tuple[Path, ...]
    partial: bool
    covered_runtime_stubs: frozenset[Path]


def inspect_mapped_stub_overlay(
    context: MappedStubContext,
    bazel_bin_dir: Path,
    input_root: Path,
) -> MappedStubOverlay | None:
    """Inspect a mapped distribution without traversing transitive packages."""
    files = collect_type_relevant_files(context.overlay_paths)
    if not files:
        return None
    roots = resolve_source_layout(
        files,
        context.overlay_import_roots,
        bazel_bin_dir,
        input_root,
    ).effective_roots
    partial = any(
        path.name == "py.typed" and _is_partial_marker(path) for path in files
    )
    covered_runtime_stubs = frozenset(
        _runtime_stub_path(output_relative_path(path, roots, input_root))
        for path in files
        if path.suffix == ".pyi"
    )
    return MappedStubOverlay(
        files=tuple(files),
        roots=roots,
        partial=partial,
        covered_runtime_stubs=covered_runtime_stubs,
    )


def runtime_supplements(
    files: list[Path],
    roots: Sequence[Path],
    input_root: Path,
    overlay: MappedStubOverlay | None,
) -> list[Path]:
    """Retain runtime files only where a partial mapped package has gaps."""
    if overlay is None:
        return files
    if not overlay.partial:
        return []

    supplements = []
    for path in files:
        expected_stub = _expected_stub_path(
            output_relative_path(path, roots, input_root),
            path,
        )
        if expected_stub is None or expected_stub not in overlay.covered_runtime_stubs:
            supplements.append(path)
    return supplements


def materialize_mapped_stub_overlay(
    overlay: MappedStubOverlay | None,
    destination: Path,
    input_root: Path,
) -> None:
    """Copy mapped stubs into the combined dependency output."""
    if overlay is None:
        return
    for source in overlay.files:
        if source.suffix != ".pyi" and source.name != "py.typed":
            continue
        copy_file(
            source,
            destination / output_relative_path(source, overlay.roots, input_root),
        )


def materialize_mapped_stub_dependencies(
    context: MappedStubContext,
    bazel_bin_dir: Path,
    input_root: Path,
    destination: Path,
) -> bool:
    """Materialize type-relevant dependencies of a mapped stub package."""
    files = collect_type_relevant_files(context.dependency_paths)
    if not files:
        return False
    roots = resolve_source_layout(
        files,
        context.dependency_import_roots,
        bazel_bin_dir,
        input_root,
    ).effective_roots
    for source in files:
        relative = output_relative_path(source, roots, input_root)
        suffix = native_extension_suffix(source)
        if suffix is not None:
            relative = relative.with_name(source.name[: -len(suffix)] + ".pyi")
            destination_path = destination / relative
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            destination_path.touch()
        else:
            copy_file(source, destination / relative)
    return True


def _is_partial_marker(path: Path) -> bool:
    return "partial" in {
        line.strip() for line in path.read_text(encoding="utf-8").splitlines()
    }


def _expected_stub_path(relative: Path, source: Path) -> Path | None:
    if source.suffix in {".py", ".pyi", ".ipynb"}:
        return relative.with_suffix(".pyi")
    suffix = native_extension_suffix(source)
    if suffix is not None:
        return relative.with_name(source.name[: -len(suffix)] + ".pyi")
    return None


def _runtime_stub_path(path: Path) -> Path:
    parts = list(path.parts)
    if parts and parts[0].endswith("-stubs"):
        parts[0] = parts[0][: -len("-stubs")]
    return Path(*parts)
