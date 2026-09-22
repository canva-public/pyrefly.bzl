"""Implementation of the wrapper's ``check`` subcommand."""

from __future__ import annotations

import json
import logging
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

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
tracer = trace.get_tracer(__name__)


def _write_json(path: Path, document: object) -> None:
    path.write_text(f"{json.dumps(document, indent=2)}\n", encoding="utf-8")


def _write_empty_outputs(args: CheckOptions) -> None:
    args.output_fulltext.write_text("", encoding="utf-8")
    _write_json(args.output_json, {"errors": []})
    _write_json(
        args.output_sarif,
        {
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "version": "2.1.0",
            "runs": [],
        },
    )


def _read_findings(path: Path) -> list[dict[str, object]]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise WrapperError(
            f"Unable to read Pyrefly JSON output {path}: {error}"
        ) from error
    if not isinstance(document, dict) or not isinstance(document.get("errors"), list):
        raise WrapperError(f"Invalid Pyrefly JSON output in {path}")
    findings = document["errors"]
    if not all(isinstance(finding, dict) for finding in findings):
        raise WrapperError(f"Invalid Pyrefly findings in {path}")
    return findings


def _write_marker(
    args: CheckOptions,
    *,
    exit_code: int,
    has_warnings: bool,
) -> None:
    _write_json(
        args.output_marker,
        {
            "expected_failure": args.expected_to_fail,
            "exit_code": exit_code,
            "has_warnings": has_warnings,
        },
    )


def invoke(
    args: CheckOptions | UpdateBaselineOptions,
    *,
    baseline: Path | None,
    diagnostic_outputs: Sequence[tuple[str, Path]] = (),
    update_baseline: bool,
) -> CommandResult | None:
    """Run Pyrefly with the common hermetic check environment."""
    trace_prefix = "update-baseline" if update_baseline else "check"
    with tracer.start_as_current_span(
        f"pyrefly.wrapper.{trace_prefix}.collect-inputs"
    ) as span:
        direct_inputs = args.direct_inputs()
        dependencies = args.dependency_context()
        direct_files = collect_type_relevant_files(direct_inputs.paths)
        span.set_attribute("pyrefly.input.count", len(direct_inputs.paths))
        span.set_attribute("pyrefly.file.count", len(direct_files))
    if not args.source_file:
        raise WrapperError("At least one --source-file is required")
    operation = "Pyrefly baseline update" if update_baseline else "Pyrefly check"
    with tempfile.TemporaryDirectory(
        prefix=".pyrefly-bundled-",
        dir=Path.cwd(),
    ) as bundled_directory:
        bundled_stubs = Path(bundled_directory)
        with tracer.start_as_current_span(
            f"pyrefly.wrapper.{trace_prefix}.materialize-bundled-stubs"
        ) as span:
            has_bundled_stubs = materialize_bundled_stub_overlay(
                direct_inputs,
                dependencies,
                bundled_stubs,
                bazel_bin_dir=args.bazel_bin_dir,
            )
            span.set_attribute(
                "pyrefly.bundled_stubs.present",
                has_bundled_stubs,
            )
        with tracer.start_as_current_span(
            f"pyrefly.wrapper.{trace_prefix}.resolve-source-layout"
        ) as span:
            direct_search_paths = resolve_source_layout(
                direct_files,
                direct_inputs.import_roots,
                args.bazel_bin_dir,
                Path.cwd(),
                retained_roots=[Path.cwd()],
            ).effective_roots
            span.set_attribute(
                "pyrefly.search_path.count",
                len(direct_search_paths),
            )
        with tracer.start_as_current_span(
            f"pyrefly.wrapper.{trace_prefix}.plan-import-view"
        ) as span:
            import_view = plan_import_view(
                dependencies,
                bundled_stub_dirs=[bundled_stubs] if has_bundled_stubs else [],
                bazel_bin_dir=args.bazel_bin_dir,
                excluded_runtime_roots=direct_search_paths,
            )
            span.set_attribute(
                "pyrefly.import_root.count",
                len(import_view.ordered_roots),
            )
        with tracer.start_as_current_span(
            f"pyrefly.wrapper.{trace_prefix}.materialize-import-view"
        ) as span:
            site_package_paths = materialize_import_view(import_view)
            span.set_attribute(
                "pyrefly.site_package_path.count",
                len(site_package_paths),
            )
        with tracer.start_as_current_span(
            f"pyrefly.wrapper.{trace_prefix}.build-config"
        ) as span:
            search_paths = merge_matching_import_roots(
                direct_search_paths,
                args.bazel_bin_dir,
                Path("."),
            )
            settings = build_config(
                source_files=args.source_file,
                search_paths=search_paths,
                site_package_paths=site_package_paths,
                python_platform=args.python_platform,
                python_version=args.python_version,
                base_config=args.base_config,
                baseline=None if update_baseline else baseline,
            )
            span.set_attribute(
                "pyrefly.project_include.count",
                len(settings["project-includes"]),
            )
            span.set_attribute(
                "pyrefly.search_path.count",
                len(search_paths),
            )
        if not settings["project-includes"]:
            logger.debug(
                "Skipping %s for %s because project-excludes match every source",
                operation,
                args.target_label,
            )
            return None

        with tracer.start_as_current_span(
            f"pyrefly.wrapper.{trace_prefix}.resolve-executable"
        ):
            executable = resolve_executable(args.pyrefly_executable)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=".pyrefly-bazel-",
            suffix=".toml",
            dir=Path.cwd(),
        ) as config_file:
            with tracer.start_as_current_span(
                f"pyrefly.wrapper.{trace_prefix}.write-config"
            ):
                config_file.write(dump_toml(settings))
                config_file.flush()
            command: list[str | Path] = [
                executable,
                "check",
                "--config",
                Path(config_file.name),
            ]
            for output_format, output_path in diagnostic_outputs:
                command.extend(["--output", f"{output_format}:{output_path}"])
            if update_baseline:
                if baseline is None:
                    raise WrapperError("A baseline output is required for an update")
                command.extend(["--baseline", baseline, "--update-baseline"])
            with tracer.start_as_current_span(
                f"pyrefly.wrapper.{trace_prefix}.run-pyrefly",
                attributes={
                    "pyrefly.source.count": len(args.source_file),
                    "pyrefly.timeout.seconds": args.timeout,
                },
            ) as span:
                result = run_command(
                    command,
                    cwd=Path.cwd(),
                    timeout=args.timeout,
                )
                span.set_attribute("pyrefly.wrapper.exit_code", result.returncode)
                if result.returncode != 0:
                    span.set_status(Status(StatusCode.ERROR))
                return result


def run(args: CheckOptions) -> int:
    for output in (
        args.output_marker,
        args.output_fulltext,
        args.output_json,
        args.output_sarif,
    ):
        output.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = invoke(
            args,
            baseline=args.baseline,
            diagnostic_outputs=(
                ("full-text", args.output_fulltext),
                ("json", args.output_json),
                ("sarif", args.output_sarif),
            ),
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
        _write_empty_outputs(args)
        _write_marker(args, exit_code=0, has_warnings=False)
        return 0

    logger.debug(
        "Pyrefly check for %s completed with exit code %d",
        args.target_label,
        result.returncode,
    )
    if result.returncode not in (0, 1):
        _write_marker(args, exit_code=result.returncode, has_warnings=False)
        if result.output:
            logger.error(result.output.rstrip("\n"))
        logger.error(
            "Pyrefly infrastructure failure for %s (exit code %d)",
            args.target_label,
            result.returncode,
        )
        return INFRASTRUCTURE_EXIT_CODE

    findings = _read_findings(args.output_json)
    has_warnings = any(finding.get("severity") == "warn" for finding in findings)
    _write_marker(
        args,
        exit_code=result.returncode,
        has_warnings=has_warnings,
    )
    non_blocking_severities = {"ignore", "info", "warn"}
    has_type_errors = any(
        finding.get("severity") not in non_blocking_severities for finding in findings
    )
    type_check_failed = has_type_errors or (result.returncode == 1 and not findings)
    fulltext = args.output_fulltext.read_text(encoding="utf-8").rstrip("\n")
    if type_check_failed and args.expected_to_fail:
        if fulltext:
            logger.warning(fulltext)
        logger.warning(
            "Pyrefly type checking failed for %s as expected",
            args.target_label,
        )
        return 0
    if type_check_failed:
        if fulltext:
            logger.error(fulltext)
        logger.error("Pyrefly type checking failed for %s", args.target_label)
        return 1
    if args.expected_to_fail:
        if args.stale_message is None:
            raise WrapperError("--stale-message is required with --expected-to-fail")
        stale_target_label = (
            args.target_label[2:]
            if args.target_label.startswith("@@//")
            else args.target_label
        )
        logger.error(args.stale_message.replace("%s", stale_target_label))
        return 1
    if result.output:
        logger.debug(result.output.rstrip("\n"))
    return 0
