"""Shared materialization helpers for Python dependency inputs."""

from __future__ import annotations

import importlib.machinery
from collections.abc import Iterable, Sequence
from pathlib import Path

from .transformed import repository_relative_path
from .utils import WrapperError

EXTENSION_SUFFIXES = tuple(importlib.machinery.EXTENSION_SUFFIXES)


def native_extension_suffix(path: Path) -> str | None:
    """Return the importable native-extension suffix for a path, if any."""
    return next(
        (suffix for suffix in EXTENSION_SUFFIXES if path.name.endswith(suffix)),
        None,
    )


def is_type_relevant(path: Path) -> bool:
    """Whether a file can contribute information to Python import resolution."""
    return (
        path.suffix in {".py", ".pyi", ".ipynb"}
        or path.name == "py.typed"
        or native_extension_suffix(path) is not None
    )


def collect_type_relevant_files(
    input_paths: Sequence[Path],
) -> list[Path]:
    """Expand input trees while discarding files irrelevant to type checking."""
    files: list[Path] = []
    for path in input_paths:
        if path.is_dir():
            for candidate in path.rglob("*"):
                if candidate.is_file() and is_type_relevant(candidate):
                    files.append(candidate)
        elif path.is_file() and is_type_relevant(path):
            files.append(path)
    return list(dict.fromkeys(files))


def generate_native_shims(
    paths: Iterable[Path],
    repository_root: Path,
    bazel_bin_dir: Path,
    output: Path,
) -> None:
    """Represent native modules with empty stubs without retaining binaries."""
    for path in paths:
        suffix = native_extension_suffix(path)
        if suffix is None:
            continue
        module_name = path.name[: -len(suffix)] + ".pyi"
        relative_parent = repository_relative_path(
            path,
            repository_root,
            bazel_bin_dir,
        ).parent
        shim = output / relative_parent / module_name
        if not shim.exists():
            shim.parent.mkdir(parents=True, exist_ok=True)
            shim.touch()


def owning_root(
    path: Path,
    roots: Iterable[Path],
    input_root: Path,
) -> Path:
    """Return the most specific declared import root containing a file."""
    absolute = path.absolute()
    matches = [
        root
        for root in roots
        if absolute == root.absolute() or absolute.is_relative_to(root.absolute())
    ]
    if matches:
        return max(matches, key=lambda root: len(root.absolute().parts))
    if absolute.is_relative_to(input_root.absolute()):
        return input_root
    raise WrapperError(
        f"{path} is not contained by a resolved import root or {input_root}"
    )


def output_relative_path(
    path: Path,
    roots: Iterable[Path],
    input_root: Path,
) -> Path:
    """Locate a file beneath its owning import root."""
    root = owning_root(path, roots, input_root)
    return path.absolute().relative_to(root.absolute())


def copy_file(
    source: Path,
    destination: Path,
) -> None:
    """Copy one declared input to its materialized destination."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes())
