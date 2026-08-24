"""Structured input groups derived from the wrapper CLI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DirectInputs:
    """Files and import roots owned directly by the current target."""

    paths: tuple[Path, ...]
    import_roots: tuple[Path, ...]


@dataclass(frozen=True)
class DependencyContext:
    """Dependency roots grouped by their role in import resolution."""

    runtime_import_roots: tuple[Path, ...]
    stub_roots: tuple[Path, ...]
    transformed_trees: tuple[Path, ...]


@dataclass(frozen=True)
class MappedStubContext:
    """A mapped-stub overlay and the dependencies needed to expose it."""

    overlay_paths: tuple[Path, ...]
    overlay_import_roots: tuple[Path, ...]
    dependency_paths: tuple[Path, ...]
    dependency_import_roots: tuple[Path, ...]
