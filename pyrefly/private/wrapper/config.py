"""Construction and serialization of hermetic Pyrefly configurations."""

from __future__ import annotations

import logging
import os
import re
import shutil
import tempfile
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import tomli_w

from .input_context import DependencyContext, DirectInputs
from .transformed import (
    IMPORT_ROOTS_MANIFEST,
    MAPPED_STUB_DEPENDENCY_ROOT,
    MAPPED_STUB_ROOT,
)
from .utils import deduplicate_paths

logger = logging.getLogger(__name__)


class ConfigError(ValueError):
    """Raised for an invalid consumer configuration."""


@dataclass(frozen=True)
class SourceLayout:
    """Declared and effective import roots for one direct source set."""

    declared_roots: tuple[Path, ...]
    effective_roots: tuple[Path, ...]


_BAZEL_OWNED_SETTINGS = frozenset(
    {
        "baseline",
        "project-includes",
        "search-path",
        "site-package-path",
        "python-version",
        "python-platform",
        "skip-interpreter-query",
        "disable-project-excludes-heuristics",
        "disable-search-path-heuristics",
        "use-ignore-files",
    }
)
_SKIP_MERGE_NAMES = frozenset(
    {
        "__pycache__",
        IMPORT_ROOTS_MANIFEST,
        MAPPED_STUB_DEPENDENCY_ROOT.name,
        MAPPED_STUB_ROOT.name,
    }
)
_SKIP_MERGE_SUFFIXES = (".dist-info", ".data")


def load_base_config(path: Path | None) -> dict[str, Any]:
    """Load Pyrefly settings from pyrefly.toml or pyproject.toml."""
    if path is None:
        return {}
    if path.name not in {"pyrefly.toml", "pyproject.toml"}:
        raise ConfigError(
            "The base configuration must be named pyrefly.toml or pyproject.toml, "
            f"not {path.name!r}"
        )
    try:
        with path.open("rb") as config_file:
            document = tomllib.load(config_file)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ConfigError(f"Unable to read {path}: {error}") from error

    if path.name == "pyrefly.toml":
        settings = document
    else:
        tool = document.get("tool")
        settings = tool.get("pyrefly") if isinstance(tool, dict) else None
        if not isinstance(settings, dict):
            raise ConfigError(f"{path} does not contain a [tool.pyrefly] table")
    return _copy_mapping(settings)


def build_config(
    *,
    source_files: Sequence[Path],
    search_paths: Sequence[Path],
    site_package_paths: Sequence[str],
    python_platform: str,
    python_version: str,
    base_config: Path | None = None,
    baseline: Path | None = None,
) -> dict[str, Any]:
    """Overlay Bazel-owned paths and interpreter settings on consumer policy."""
    settings = load_base_config(base_config)
    for key in _BAZEL_OWNED_SETTINGS:
        settings.pop(key, None)

    settings.update(
        {
            "project-includes": _filter_project_includes(source_files, settings),
            "search-path": [str(path) for path in search_paths],
            "site-package-path": list(site_package_paths),
            "python-version": python_version,
            "python-platform": python_platform,
            "skip-interpreter-query": True,
            "disable-project-excludes-heuristics": True,
            "disable-search-path-heuristics": True,
            "use-ignore-files": False,
        }
    )
    if baseline is not None:
        settings["baseline"] = str(baseline)
    return settings


def materialize_bundled_stub_overlay(
    direct_inputs: DirectInputs,
    dependencies: DependencyContext,
    destination: Path,
    *,
    bazel_bin_dir: Path,
) -> bool:
    """Discover bundled stubs in declared inputs and build an import overlay."""
    import_roots = resolve_import_paths(
        direct_inputs.import_roots,
        bazel_bin_dir,
    )
    excluded_roots = frozenset(
        path.absolute()
        for path in [
            *resolve_import_paths(
                dependencies.stub_roots,
                bazel_bin_dir,
            ),
            *(path for path in dependencies.transformed_trees if path.is_dir()),
        ]
    )
    copied = False
    for input_path in deduplicate_paths(direct_inputs.paths):
        if input_path.is_dir():
            if _path_is_within_any(input_path, excluded_roots):
                continue
            candidates = input_path.rglob("*.pyi")
            candidate_root = input_path
        elif input_path.suffix == ".pyi" and input_path.is_file():
            candidates = (input_path,)
            candidate_root = None
        else:
            continue
        for source in candidates:
            if _path_is_within_any(source, excluded_roots):
                continue
            relative = _bundled_stub_relative_path(
                source,
                import_roots,
                candidate_root=candidate_root,
                fallback_roots=[bazel_bin_dir, Path.cwd()],
            )
            output = destination / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            if not output.exists():
                shutil.copyfile(source, output)
            copied = True
    return copied


def resolve_import_paths(
    paths: Sequence[Path],
    bazel_bin_dir: Path,
    *,
    excluded_roots: frozenset[Path] = frozenset(),
) -> list[Path]:
    """Resolve every PyInfo import using global Bazel layout precedence."""
    provided_paths = []
    for original in paths:
        path = Path(_strip_main_prefix(str(original)))
        if excluded_roots and any(
            candidate.is_dir() and candidate.absolute() in excluded_roots
            for candidate in _import_path_candidates(path, bazel_bin_dir)
        ):
            continue
        provided_paths.append(path)
    candidate_groups = (
        [bazel_bin_dir / path for path in provided_paths],
        [bazel_bin_dir / "external" / path for path in provided_paths],
        provided_paths,
        [Path("external") / path for path in provided_paths],
    )
    resolved = []
    for candidates in candidate_groups:
        for candidate in candidates:
            if candidate.is_dir():
                resolved.append(candidate)
    return deduplicate_paths(resolved)


def resolve_source_layout(
    source_files: Sequence[Path],
    import_paths: Sequence[Path],
    bazel_bin_dir: Path,
    fallback_root: Path,
    *,
    retained_roots: Sequence[Path] = (),
) -> SourceLayout:
    """Resolve all import-root views for one set of direct sources."""
    import_roots = resolve_import_paths(import_paths, bazel_bin_dir)
    roots_by_absolute_path = {root.absolute(): root for root in import_roots}
    selected_roots = set()
    fallback_roots = []
    absolute_bin_dir = bazel_bin_dir.absolute()
    absolute_fallback = fallback_root.absolute()

    for source in source_files:
        absolute_source = source.absolute()
        search = absolute_source if source.is_dir() else absolute_source.parent
        matched_root = False
        for candidate in (search, *search.parents):
            root = roots_by_absolute_path.get(candidate)
            if root is not None:
                selected_roots.add(root)
                matched_root = True
        if matched_root:
            continue

        if absolute_source.is_relative_to(absolute_bin_dir):
            fallback_roots.append(bazel_bin_dir)
        elif absolute_source.is_relative_to(absolute_fallback):
            fallback_roots.append(fallback_root)
        else:
            fallback_roots.append(source if source.is_dir() else source.parent)

    declared_roots = tuple(root for root in import_roots if root in selected_roots)
    return SourceLayout(
        declared_roots=declared_roots,
        effective_roots=tuple(
            deduplicate_paths([*declared_roots, *fallback_roots, *retained_roots])
        ),
    )


def merge_site_package_dirs(
    directories: Sequence[Path],
) -> list[str]:
    """Merge import roots with symlinks, retaining the list on any failure."""
    original = [str(path) for path in directories]
    if len(original) <= 1:
        return original
    try:
        merged = Path(tempfile.mkdtemp(prefix="pyrefly_merged_"))
        for directory in directories:
            if not directory.is_dir():
                continue
            _merge_tree(directory, merged)
        logger.debug(
            "Merged %d site-package dirs into %s (%d entries)",
            len(directories),
            merged,
            sum(1 for _ in merged.iterdir()),
        )
        return [str(merged)]
    except OSError:
        logger.warning(
            "Failed to merge site-package dirs via symlinks; "
            "falling back to original list",
            exc_info=True,
        )
        return original


def merge_matching_import_roots(
    directories: Sequence[Path],
    bazel_bin_dir: Path,
    repository_root: Path,
) -> list[Path]:
    """Merge source and generated instances of each logical import root."""
    physical_roots = [
        bazel_bin_dir / repository_root,
        repository_root,
    ]
    grouped: dict[Path, list[Path]] = {}
    for directory in directories:
        absolute = directory.absolute()
        logical = None
        for physical_root in physical_roots:
            root = physical_root.absolute()
            if absolute == root or absolute.is_relative_to(root):
                logical = absolute.relative_to(root)
                break
        grouped.setdefault(logical or absolute, []).append(directory)

    merged = []
    for roots in grouped.values():
        merged.extend(Path(path) for path in merge_site_package_dirs(roots))
    return merged


def _merge_tree(
    source: Path,
    destination: Path,
) -> None:
    for entry in source.iterdir():
        if entry.name in _SKIP_MERGE_NAMES or entry.name.endswith(_SKIP_MERGE_SUFFIXES):
            continue
        target = destination / entry.name
        if not target.exists():
            os.symlink(entry.resolve(), target)
        elif target.is_symlink() and entry.is_dir() and target.resolve().is_dir():
            existing = target.resolve()
            target.unlink()
            target.mkdir()
            _merge_tree(existing, target)
            _merge_tree(entry.resolve(), target)
        elif target.is_dir() and not target.is_symlink() and entry.is_dir():
            _merge_tree(entry.resolve(), target)


def dump_toml(settings: Mapping[str, Any]) -> str:
    """Serialize Pyrefly configuration with the locked TOML writer."""
    return tomli_w.dumps(dict(settings))


def _copy_mapping(values: Mapping[str, Any]) -> dict[str, Any]:
    copied: dict[str, Any] = {}
    for key, value in values.items():
        if isinstance(value, Mapping):
            copied[key] = _copy_mapping(value)
        elif isinstance(value, list):
            copied[key] = list(value)
        else:
            copied[key] = value
    return copied


def _strip_main_prefix(path: str) -> str:
    return path.removeprefix("_main/")


def _import_path_candidates(path: Path, bazel_bin_dir: Path) -> tuple[Path, ...]:
    if path.is_absolute():
        return (path,)
    return (
        bazel_bin_dir / path,
        bazel_bin_dir / "external" / path,
        path,
        Path("external") / path,
    )


def _bundled_stub_relative_path(
    path: Path,
    roots: Sequence[Path],
    *,
    candidate_root: Path | None,
    fallback_roots: Sequence[Path],
) -> Path:
    absolute = path.absolute()
    matches: list[tuple[int, Path]] = []
    for root in roots:
        try:
            relative = absolute.relative_to(root.absolute())
        except ValueError:
            continue
        matches.append((len(root.absolute().parts), relative))
    if matches:
        return max(matches, key=lambda match: match[0])[1]
    if candidate_root is not None:
        try:
            return absolute.relative_to(candidate_root.absolute())
        except ValueError:
            pass
    for root in fallback_roots:
        try:
            return absolute.relative_to(root.absolute())
        except ValueError:
            continue
    raise ConfigError(f"{path} is not contained by a declared import root")


def _path_is_within_any(path: Path, roots: frozenset[Path]) -> bool:
    absolute = path.absolute()
    return absolute in roots or any(parent in roots for parent in absolute.parents)


def _filter_project_includes(
    source_files: Sequence[Path],
    settings: Mapping[str, Any],
) -> list[str]:
    includes = [str(path) for path in source_files]
    project_excludes = settings.get("project-excludes")
    if (
        not isinstance(project_excludes, list)
        or not project_excludes
        or not all(isinstance(pattern, str) for pattern in project_excludes)
    ):
        return includes
    try:
        return [
            str(source)
            for source in source_files
            if not any(
                _matches_pyrefly_glob(pattern, source) for pattern in project_excludes
            )
        ]
    except ValueError:
        # Let Pyrefly report malformed glob syntax instead of silently
        # removing includes based on a partially applied configuration.
        return includes


def _matches_pyrefly_glob(pattern: str, path: Path) -> bool:
    if os.path.isabs(pattern):
        candidate = os.path.abspath(path)
    elif path.is_absolute():
        candidate = os.path.relpath(path, Path.cwd())
    else:
        candidate = str(path)
    candidate = os.path.normpath(candidate).replace(os.sep, "/")
    normalized_pattern = os.path.normpath(pattern).replace(os.sep, "/")

    base_pattern = normalized_pattern
    if base_pattern.endswith("**"):
        base_pattern += "/*"
    elif base_pattern.endswith("**/"):
        base_pattern += "*"
    if _compile_pyrefly_glob(base_pattern).fullmatch(candidate):
        return True
    if base_pattern.endswith("**/*"):
        return False
    directory_pattern = base_pattern
    if not directory_pattern.endswith("/"):
        directory_pattern += "/"
    directory_pattern += "**"
    return _compile_pyrefly_glob(directory_pattern).fullmatch(candidate) is not None


@lru_cache(maxsize=None)
def _compile_pyrefly_glob(pattern: str) -> re.Pattern[str]:
    """Compile the subset of glob syntax accepted by Pyrefly's glob crate."""
    expression = []
    index = 0
    while index < len(pattern):
        character = pattern[index]
        if character == "*":
            closing = index
            while closing < len(pattern) and pattern[closing] == "*":
                closing += 1
            count = closing - index
            if count > 2:
                raise ValueError("invalid consecutive wildcards")
            if count == 2:
                begins_component = index == 0 or pattern[index - 1] == "/"
                ends_component = closing == len(pattern) or pattern[closing] == "/"
                if not begins_component or not ends_component:
                    raise ValueError("recursive wildcards must form a path component")
                if closing < len(pattern):
                    expression.append("(?:.*/)?")
                    index = closing + 1
                else:
                    expression.append(".*")
                    index = closing
            else:
                expression.append(".*")
                index = closing
        elif character == "?":
            expression.append(".")
            index += 1
        elif character == "[":
            closing = pattern.find("]", index + 1)
            if closing == -1:
                expression.append(r"\[")
                index += 1
                continue
            contents = pattern[index + 1 : closing]
            if contents.startswith("!"):
                contents = "^" + contents[1:]
            elif contents.startswith("^"):
                contents = r"\^" + contents[1:].replace("\\", r"\\")
            else:
                contents = contents.replace("\\", r"\\")
            expression.append("[" + contents + "]")
            index = closing + 1
        else:
            expression.append(re.escape(character))
            index += 1
    return re.compile("".join(expression))
