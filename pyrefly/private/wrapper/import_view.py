"""Planning and materialisation of the hermetic Pyrefly import view."""

from __future__ import annotations

import sysconfig
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .config import merge_site_package_dirs, resolve_import_paths
from .input_context import DependencyContext
from .transformed import transformed_import_roots
from .utils import deduplicate_paths


@dataclass(frozen=True)
class ImportViewPlan:
    """Resolved import roots grouped by their precedence tier."""

    standard_library_roots: tuple[Path, ...]
    configured_stub_roots: tuple[Path, ...]
    bundled_stub_roots: tuple[Path, ...]
    transformed_dependency_roots: tuple[Path, ...]
    runtime_roots: tuple[Path, ...]

    @property
    def ordered_roots(self) -> tuple[Path, ...]:
        """Return deduplicated roots in the order used to resolve imports."""
        return tuple(
            deduplicate_paths(
                [
                    *self.standard_library_roots,
                    *self.configured_stub_roots,
                    *self.bundled_stub_roots,
                    *self.transformed_dependency_roots,
                    *self.runtime_roots,
                ]
            )
        )


def plan_import_view(
    dependencies: DependencyContext,
    *,
    bundled_stub_dirs: Sequence[Path],
    bazel_bin_dir: Path,
    excluded_runtime_roots: Sequence[Path] = (),
) -> ImportViewPlan:
    """Resolve import roots into the precedence required by Bazel actions."""
    configured_stubs = resolve_import_paths(
        dependencies.stub_roots,
        bazel_bin_dir,
    )
    bundled_stubs = deduplicate_paths(
        path for path in bundled_stub_dirs if path.is_dir()
    )
    generated_stubs = deduplicate_paths(
        root
        for path in dependencies.transformed_trees
        if path.is_dir()
        for root in transformed_import_roots(path)
    )
    excluded_roots = frozenset(path.absolute() for path in excluded_runtime_roots)
    runtime_paths = (
        []
        if bazel_bin_dir.absolute() in excluded_roots or not bazel_bin_dir.is_dir()
        else [bazel_bin_dir]
    )
    runtime_paths.extend(
        resolve_import_paths(
            dependencies.runtime_import_roots,
            bazel_bin_dir,
            excluded_roots=excluded_roots,
        )
    )

    return ImportViewPlan(
        standard_library_roots=tuple(_stdlib_paths()),
        configured_stub_roots=tuple(configured_stubs),
        bundled_stub_roots=tuple(bundled_stubs),
        transformed_dependency_roots=tuple(generated_stubs),
        runtime_roots=tuple(runtime_paths),
    )


def materialize_import_view(plan: ImportViewPlan) -> list[str]:
    """Materialize a planned import view as Pyrefly site-package paths."""
    return merge_site_package_dirs(plan.ordered_roots)


def _stdlib_paths() -> list[Path]:
    stdlib = Path(sysconfig.get_path("stdlib"))
    paths = [stdlib]
    dynload = stdlib / "lib-dynload"
    if dynload.is_dir():
        paths.append(dynload)
    return paths
