"""Implementation of the wrapper's ``stubgen`` subcommand."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from .config import (
    build_config,
    dump_toml,
    materialize_bundled_stub_overlay,
    merge_matching_import_roots,
    resolve_source_layout,
)
from .import_view import materialize_import_view, plan_import_view
from .mapped_stubs import (
    inspect_mapped_stub_overlay,
    runtime_supplements,
)
from .source_utils import (
    collect_type_relevant_files,
    copy_file,
    output_relative_path,
    owning_root,
)
from .transformed import (
    finalize_transformed_tree,
    repository_relative_path,
)
from .utils import (
    WrapperError,
    resolve_executable,
    run_command,
)

if TYPE_CHECKING:
    from .cli import StubgenOptions


_BASE_TIMEOUT_SECONDS = 420
_PER_FILE_TIMEOUT_SECONDS = 0.5
logger = logging.getLogger(__name__)


def run(args: StubgenOptions) -> int:
    direct_inputs = args.direct_inputs()
    mapped_stub_context = args.mapped_stub_context()
    dependencies = args.dependency_context(
        additional_stub_roots=mapped_stub_context.dependency_import_roots,
    )
    timeout = max(
        _BASE_TIMEOUT_SECONDS,
        len(direct_inputs.paths) * _PER_FILE_TIMEOUT_SECONDS,
    )
    stubgen_flags = []
    if args.include_docstrings:
        stubgen_flags.append("--include-docstrings")
    if args.include_private:
        stubgen_flags.append("--include-private")
    executable = resolve_executable(args.pyrefly_executable)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    direct_files = collect_type_relevant_files(direct_inputs.paths)
    direct_layout = resolve_source_layout(
        direct_files,
        direct_inputs.import_roots,
        args.bazel_bin_dir,
        args.repository_root,
    )
    mapped_stub = inspect_mapped_stub_overlay(
        mapped_stub_context,
        args.bazel_bin_dir,
        args.input_root,
    )
    direct_files = runtime_supplements(
        direct_files,
        direct_layout.effective_roots,
        args.input_root,
        mapped_stub,
    )
    generation_sources = [
        source
        for source in direct_files
        if source.suffix == ".py" and not source.with_suffix(".pyi").is_file()
    ]
    search_paths = resolve_source_layout(
        generation_sources,
        direct_inputs.import_roots,
        args.bazel_bin_dir,
        args.repository_root,
        retained_roots=(args.repository_root,) if args.retain_repository_root else (),
    ).effective_roots
    with tempfile.TemporaryDirectory(
        prefix=".pyrefly-bundled-",
        dir=Path.cwd(),
    ) as bundled_directory:
        bundled_stubs = Path(bundled_directory)
        has_bundled_stubs = materialize_bundled_stub_overlay(
            direct_inputs,
            dependencies,
            bundled_stubs,
            bazel_bin_dir=args.bazel_bin_dir,
        )
        import_view = plan_import_view(
            dependencies,
            bundled_stub_dirs=[bundled_stubs] if has_bundled_stubs else [],
            bazel_bin_dir=args.bazel_bin_dir,
            excluded_runtime_roots=search_paths,
        )
        site_package_paths = materialize_import_view(import_view)
        settings = build_config(
            source_files=generation_sources,
            search_paths=merge_matching_import_roots(
                search_paths,
                args.bazel_bin_dir,
                args.repository_root,
            ),
            site_package_paths=site_package_paths,
            python_platform=args.python_platform,
            python_version=args.python_version,
            base_config=args.base_config,
        )
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=".pyrefly-bazel-",
            suffix=".toml",
            dir=Path.cwd(),
        ) as config_file:
            config_file.write(dump_toml(settings))
            config_file.flush()
            config_path = Path(config_file.name)
            _process_python_files(
                executable,
                generation_sources,
                search_paths,
                args.input_root,
                args.repository_root,
                args.bazel_bin_dir,
                args.output_dir,
                config_path,
                stubgen_flags,
                timeout,
            )

    # Bundled stubs are authoritative over anything stubgen emitted for the
    # same module, so copy direct typed assets only after generation finishes.
    for path in direct_files:
        if path.suffix == ".pyi" or path.name == "py.typed":
            copy_file(
                path,
                args.output_dir
                / repository_relative_path(
                    path,
                    args.repository_root,
                    args.bazel_bin_dir,
                ),
            )
    finalize_transformed_tree(
        direct_files,
        direct_layout.declared_roots,
        mapped_stub,
        mapped_stub_context,
        args,
    )
    return 0


def _process_python_files(
    executable: Path,
    python_files: list[Path],
    search_paths: tuple[Path, ...],
    input_root: Path,
    repository_root: Path,
    bazel_bin_dir: Path,
    output: Path,
    config_path: Path,
    stubgen_flags: list[str],
    timeout: float,
) -> None:
    if not python_files:
        logger.debug("SKIP no uncovered Python files")
        return
    by_root: dict[Path, list[Path]] = {}
    for path in python_files:
        root = owning_root(path, search_paths, input_root)
        by_root.setdefault(root, []).append(path)

    with tempfile.TemporaryDirectory(
        prefix=".pyrefly-generated-",
        dir=Path.cwd(),
    ) as generated_directory:
        generated = Path(generated_directory)
        for root, grouped in by_root.items():
            prefix = _common_package_prefix(grouped, root)
            destination = generated / prefix if prefix != Path(".") else generated
            _run_stubgen(
                executable,
                grouped,
                root,
                destination,
                config_path,
                stubgen_flags,
                timeout,
            )
            for path in grouped:
                relative_output = repository_relative_path(
                    path,
                    repository_root,
                    bazel_bin_dir,
                )
                generated_stub = (
                    generated / output_relative_path(path, search_paths, input_root)
                ).with_suffix(".pyi")
                if not generated_stub.is_file():
                    raise WrapperError(f"Pyrefly did not generate a stub for {path}")
                copy_file(
                    generated_stub,
                    (output / relative_output).with_suffix(".pyi"),
                )


def _run_stubgen(
    executable: Path,
    python_files: list[Path],
    cwd: Path,
    output: Path,
    config_path: Path,
    stubgen_flags: list[str],
    timeout: float,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    relative_files = [
        str(path.absolute().relative_to(cwd.absolute())) for path in python_files
    ]
    result = run_command(
        [
            executable,
            "stubgen",
            "--config",
            config_path,
            "--output-dir",
            output.resolve(),
            *stubgen_flags,
            *relative_files,
        ],
        cwd=cwd,
        timeout=timeout,
    )
    if result.output:
        logger.debug("%s", result.output.rstrip("\n"))
    if result.returncode == 0:
        logger.debug("OK generated %d files from %s", len(python_files), cwd)
        return
    raise WrapperError(
        f"Pyrefly stubgen failed with exit code {result.returncode} in {cwd}"
    )


def _common_package_prefix(files: list[Path], base: Path) -> Path:
    parents = [
        str(path.absolute().relative_to(base.absolute()).parent) for path in files
    ]
    try:
        common = os.path.commonpath(parents)
    except ValueError:
        return Path(".")
    return Path(common) if common and common != "." else Path(".")
