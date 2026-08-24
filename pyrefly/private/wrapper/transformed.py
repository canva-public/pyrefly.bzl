"""Repository-relative layouts for transformed Python dependency trees."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING

from .utils import WrapperError, deduplicate_paths

if TYPE_CHECKING:
    from .cli import MinifyOptions, StubgenOptions
    from .input_context import MappedStubContext
    from .mapped_stubs import MappedStubOverlay

IMPORT_ROOTS_MANIFEST = ".pyrefly-import-roots"
MAPPED_STUB_ROOT = Path(".pyrefly-mapped-stubs")
MAPPED_STUB_DEPENDENCY_ROOT = Path(".pyrefly-mapped-stub-dependencies")


def repository_path(
    path: Path,
    repository_root: Path,
    bazel_bin_dir: Path,
) -> tuple[Path, Path]:
    """Return the physical repository root and repository-relative path."""
    absolute = path.absolute()
    candidates = deduplicate_paths(
        [
            bazel_bin_dir / repository_root,
            repository_root,
        ]
    )
    for candidate in candidates:
        root = candidate.absolute()
        if absolute == root or absolute.is_relative_to(root):
            return candidate, absolute.relative_to(root)
    raise WrapperError(
        f"{path} is not contained by source or generated repository root "
        f"{repository_root}"
    )


def repository_relative_path(
    path: Path,
    repository_root: Path,
    bazel_bin_dir: Path,
) -> Path:
    """Return a path relative to its logical Bazel repository."""
    return repository_path(path, repository_root, bazel_bin_dir)[1]


def repository_relative_roots(
    roots: Iterable[Path],
    repository_root: Path,
    bazel_bin_dir: Path,
) -> list[Path]:
    """Translate resolved physical import roots into repository-relative roots."""
    return deduplicate_paths(
        repository_relative_path(root, repository_root, bazel_bin_dir) for root in roots
    )


def finalize_transformed_tree(
    files: Iterable[Path],
    roots: Iterable[Path],
    mapped_stub: MappedStubOverlay | None,
    mapped_stub_context: MappedStubContext,
    args: MinifyOptions | StubgenOptions,
) -> None:
    """Materialize shared overlays, shims, and transformed-tree metadata."""
    # These modules use the repository path helpers above, so import them only
    # when finalizing a tree rather than introducing an import cycle.
    from .mapped_stubs import (
        materialize_mapped_stub_dependencies,
        materialize_mapped_stub_overlay,
    )
    from .source_utils import generate_native_shims

    materialize_mapped_stub_overlay(
        mapped_stub,
        args.output_dir / MAPPED_STUB_ROOT,
        args.input_root,
    )
    has_mapped_stub_dependencies = materialize_mapped_stub_dependencies(
        mapped_stub_context,
        args.bazel_bin_dir,
        args.input_root,
        args.output_dir / MAPPED_STUB_DEPENDENCY_ROOT,
    )
    generate_native_shims(
        files,
        args.repository_root,
        args.bazel_bin_dir,
        args.output_dir,
    )
    import_roots = []
    if mapped_stub is not None:
        import_roots.append(MAPPED_STUB_ROOT)
    if has_mapped_stub_dependencies:
        import_roots.append(MAPPED_STUB_DEPENDENCY_ROOT)
    import_roots.extend(
        repository_relative_roots(
            roots,
            args.repository_root,
            args.bazel_bin_dir,
        )
    )
    if args.retain_repository_root:
        import_roots.append(Path("."))
    write_import_roots(args.output_dir, import_roots)


def write_import_roots(output: Path, roots: Iterable[Path]) -> None:
    """Describe the ordered import roots contained by a transformed tree."""
    rendered = []
    for root in deduplicate_paths(roots):
        _validate_relative_root(root)
        rendered.append(root.as_posix())
    (output / IMPORT_ROOTS_MANIFEST).write_text(
        "".join(f"{root}\n" for root in rendered),
        encoding="utf-8",
    )


def transformed_import_roots(
    directory: Path,
) -> list[Path]:
    """Expand a transformed tree into its declared internal import roots."""
    manifest = directory / IMPORT_ROOTS_MANIFEST
    if not manifest.is_file():
        return [directory]
    roots = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        root = Path(line)
        _validate_relative_root(root)
        candidate = directory / root
        if candidate.is_dir():
            roots.append(candidate)
    return deduplicate_paths(roots)


def _validate_relative_root(root: Path) -> None:
    if root.is_absolute() or ".." in root.parts:
        raise WrapperError(f"Invalid transformed import root {root}")
