"""Implementation of the wrapper's ``check`` subcommand."""

from __future__ import annotations

import logging
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
from .source_utils import collect_type_relevant_files
from .utils import (
    INFRASTRUCTURE_EXIT_CODE,
    CommandResult,
    CommandTimeout,
    WrapperError,
    resolve_executable,
    run_command,
)

if TYPE_CHECKING:
    from .cli import CheckOptions, UpdateBaselineOptions


DEFAULT_TIMEOUT_SECONDS = 5 * 60
logger = logging.getLogger(__name__)


def _record_expected_failure(message: str, warning_output: Path | None) -> None:
    """Log an expected failure and persist it for optional later display."""
    logger.warning(message)
    if warning_output is not None:
        with warning_output.open("a", encoding="utf-8") as output:
            output.write(f"[PYREFLY] [WARNING] {message.rstrip()}\n")


def invoke(
    args: CheckOptions | UpdateBaselineOptions,
    *,
    baseline: Path | None,
    update_baseline: bool,
) -> CommandResult | None:
    """Run Pyrefly with the common hermetic check environment."""
    direct_inputs = args.direct_inputs()
    dependencies = args.dependency_context()
    if not args.source_file:
        raise WrapperError("At least one --source-file is required")
    operation = "Pyrefly baseline update" if update_baseline else "Pyrefly check"
    direct_files = collect_type_relevant_files(direct_inputs.paths)
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
        direct_search_paths = resolve_source_layout(
            direct_files,
            direct_inputs.import_roots,
            args.bazel_bin_dir,
            Path.cwd(),
            retained_roots=[Path.cwd()],
        ).effective_roots
        import_view = plan_import_view(
            dependencies,
            bundled_stub_dirs=[bundled_stubs] if has_bundled_stubs else [],
            bazel_bin_dir=args.bazel_bin_dir,
            excluded_runtime_roots=direct_search_paths,
        )
        site_package_paths = materialize_import_view(import_view)
        settings = build_config(
            source_files=args.source_file,
            search_paths=merge_matching_import_roots(
                direct_search_paths,
                args.bazel_bin_dir,
                Path("."),
            ),
            site_package_paths=site_package_paths,
            python_platform=args.python_platform,
            python_version=args.python_version,
            base_config=args.base_config,
            baseline=None if update_baseline else baseline,
        )
        if not settings["project-includes"]:
            logger.debug(
                "Skipping %s for %s because project-excludes match every source",
                operation,
                args.target_label,
            )
            return None

        executable = resolve_executable(args.pyrefly_executable)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=".pyrefly-bazel-",
            suffix=".toml",
            dir=Path.cwd(),
        ) as config_file:
            config_file.write(dump_toml(settings))
            config_file.flush()
            command: list[str | Path] = [
                executable,
                "check",
                "--config",
                Path(config_file.name),
            ]
            if update_baseline:
                if baseline is None:
                    raise WrapperError("A baseline output is required for an update")
                command.extend(["--baseline", baseline, "--update-baseline"])
            return run_command(
                command,
                cwd=Path.cwd(),
                timeout=args.timeout,
            )


def run(args: CheckOptions) -> int:
    args.output_marker.parent.mkdir(parents=True, exist_ok=True)
    args.output_marker.touch()
    if args.warning_output is not None:
        args.warning_output.parent.mkdir(parents=True, exist_ok=True)
        args.warning_output.write_text("", encoding="utf-8")
    try:
        result = invoke(
            args,
            baseline=args.baseline,
            update_baseline=False,
        )
    except CommandTimeout as error:
        logger.error(
            "Pyrefly infrastructure failure for %s: %s",
            args.target_label,
            error,
        )
        return INFRASTRUCTURE_EXIT_CODE
    if result is None:
        return 0
    if result.output:
        output = result.output.rstrip("\n")
        if result.returncode == 1 and args.expected_to_fail:
            _record_expected_failure(output, args.warning_output)
        elif result.returncode != 0:
            logger.error(output)
        else:
            logger.debug(output)
    logger.debug(
        "Pyrefly check for %s completed with exit code %d",
        args.target_label,
        result.returncode,
    )
    if result.returncode not in (0, 1):
        logger.error(
            "Pyrefly infrastructure failure for %s (exit code %d)",
            args.target_label,
            result.returncode,
        )
        return INFRASTRUCTURE_EXIT_CODE
    if result.returncode == 0 and args.expected_to_fail:
        if args.stale_message is None:
            raise WrapperError("--stale-message is required with --expected-to-fail")
        stale_target_label = (
            args.target_label[2:]
            if args.target_label.startswith("@@//")
            else args.target_label
        )
        logger.error(args.stale_message.replace("%s", stale_target_label))
        return 1
    if result.returncode == 1 and not args.expected_to_fail:
        logger.error("Pyrefly type checking failed for %s", args.target_label)
        return 1

    if result.returncode == 1:
        _record_expected_failure(
            f"Pyrefly type checking failed for {args.target_label} as expected",
            args.warning_output,
        )
    return 0
