"""Command-line interface for Bazel Pyrefly actions."""

from __future__ import annotations

import logging
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from simple_parsing import ArgumentParser, field
from simple_parsing.wrappers import DashVariant

from . import (
    check_runner,
    display_warnings,
    extract_config,
    minify_runner,
    stubgen_runner,
    update_baseline_runner,
)
from .input_context import DependencyContext, DirectInputs, MappedStubContext
from .utils import INFRASTRUCTURE_EXIT_CODE, WrapperError

logger = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class BaseOptions:
    log_level: Literal[
        "debug",
        "info",
        "warning",
        "error",
        "critical",
    ] = "error"
    log_file: Path | None = None


@dataclass(frozen=True, kw_only=True)
class DirectOptions(BaseOptions):
    bazel_bin_dir: Path
    import_path: list[Path] = field(
        default_factory=list,
        action="append",
        nargs=None,
    )
    input_path: list[Path] = field(
        default_factory=list,
        action="append",
        nargs=None,
    )

    def direct_inputs(self) -> DirectInputs:
        return DirectInputs(tuple(self.input_path), tuple(self.import_path))


@dataclass(frozen=True, kw_only=True)
class ImportOptions(DirectOptions):
    python_platform: str
    python_version: str
    base_config: Path | None = None
    dependency_import_path: list[Path] = field(
        default_factory=list,
        action="append",
        nargs=None,
    )
    stub_import_path: list[Path] = field(
        default_factory=list,
        action="append",
        nargs=None,
    )
    transformed_dependency_path: list[Path] = field(
        default_factory=list,
        action="append",
        nargs=None,
    )

    def dependency_context(
        self,
        *,
        additional_stub_roots: Sequence[Path] = (),
    ) -> DependencyContext:
        return DependencyContext(
            tuple(self.dependency_import_path),
            (*self.stub_import_path, *additional_stub_roots),
            tuple(self.transformed_dependency_path),
        )


@dataclass(frozen=True, kw_only=True)
class MappedStubOptions:
    mapped_stub_import_path: list[Path] = field(
        default_factory=list,
        action="append",
        nargs=None,
    )
    mapped_stub_dependency_import_path: list[Path] = field(
        default_factory=list,
        action="append",
        nargs=None,
    )
    mapped_stub_dependency_path: list[Path] = field(
        default_factory=list,
        action="append",
        nargs=None,
    )
    mapped_stub_path: list[Path] = field(
        default_factory=list,
        action="append",
        nargs=None,
    )

    def mapped_stub_context(self) -> MappedStubContext:
        return MappedStubContext(
            tuple(self.mapped_stub_path),
            tuple(self.mapped_stub_import_path),
            tuple(self.mapped_stub_dependency_path),
            tuple(self.mapped_stub_dependency_import_path),
        )


@dataclass(frozen=True)
class CheckOptions(ImportOptions):
    pyrefly_executable: str
    output_marker: Path
    target_label: str
    baseline: Path | None = None
    source_file: list[Path] = field(
        default_factory=list,
        action="append",
        nargs=None,
    )
    expected_to_fail: bool = False
    warning_output: Path | None = None
    stale_message: str | None = None
    timeout: float = check_runner.DEFAULT_TIMEOUT_SECONDS


@dataclass(frozen=True)
class DisplayWarningsOptions(BaseOptions):
    output_marker: Path
    warning_file: Path


@dataclass(frozen=True)
class ExtractConfigOptions(BaseOptions):
    input_config: Path
    output_config: Path


@dataclass(frozen=True)
class UpdateBaselineOptions(ImportOptions):
    pyrefly_executable: str
    output_baseline: Path
    target_label: str
    source_file: list[Path] = field(
        default_factory=list,
        action="append",
        nargs=None,
    )
    timeout: float = check_runner.DEFAULT_TIMEOUT_SECONDS


@dataclass(frozen=True)
class MinifyOptions(DirectOptions, MappedStubOptions):
    output_dir: Path
    repository_root: Path
    input_root: Path = field(default_factory=Path.cwd)
    retain_repository_root: bool = False


@dataclass(frozen=True)
class StubgenOptions(ImportOptions, MappedStubOptions):
    pyrefly_executable: str
    output_dir: Path
    repository_root: Path
    include_docstrings: bool = False
    include_private: bool = False
    input_root: Path = field(default_factory=Path.cwd)
    retain_repository_root: bool = False


def _setup_logging(options: BaseOptions) -> None:
    package_logger = logging.getLogger("pyrefly")
    for handler in package_logger.handlers:
        handler.close()
    package_logger.handlers.clear()
    formatter = logging.Formatter(
        fmt="[PYREFLY] [{levelname}] {message}",
        style="{",
    )
    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(formatter)
    package_logger.addHandler(stream_handler)
    if options.log_file is not None:
        options.log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(
            options.log_file,
            mode="w",
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        package_logger.addHandler(file_handler)
    package_logger.setLevel(options.log_level.upper())
    package_logger.propagate = False


def create_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="pyrefly-bazel-wrapper",
        fromfile_prefix_chars="@",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser(
        "check",
        help="Run a hermetic Pyrefly check",
        add_option_string_dash_variants=DashVariant.DASH,
    )
    check.add_arguments(CheckOptions, dest="options")
    check.set_defaults(handler=check_runner.run)

    display = subparsers.add_parser(
        "display-warnings",
        help="Display warnings from a ratcheted Pyrefly check",
        add_option_string_dash_variants=DashVariant.DASH,
    )
    display.add_arguments(DisplayWarningsOptions, dest="options")
    display.set_defaults(handler=display_warnings.run)

    extract = subparsers.add_parser(
        "extract-config",
        help="Extract Pyrefly settings from pyproject.toml into an effective pyrefly.toml",
        add_option_string_dash_variants=DashVariant.DASH,
    )
    extract.add_arguments(ExtractConfigOptions, dest="options")
    extract.set_defaults(handler=extract_config.run)

    update_baseline = subparsers.add_parser(
        "update-baseline",
        help="Generate a Pyrefly baseline",
        add_option_string_dash_variants=DashVariant.DASH,
    )
    update_baseline.add_arguments(UpdateBaselineOptions, dest="options")
    update_baseline.set_defaults(handler=update_baseline_runner.run)

    minify = subparsers.add_parser(
        "minify",
        help="Retain only files which can inform Python type checking",
        add_option_string_dash_variants=DashVariant.DASH,
    )
    minify.add_arguments(MinifyOptions, dest="options")
    minify.set_defaults(handler=minify_runner.run)

    stubgen = subparsers.add_parser(
        "stubgen",
        help="Generate compact dependency stubs",
        add_option_string_dash_variants=DashVariant.DASH,
    )
    stubgen.add_arguments(StubgenOptions, dest="options")
    stubgen.set_defaults(handler=stubgen_runner.run)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = create_parser().parse_args(argv)
        _setup_logging(args.options)
        return args.handler(args.options)
    except (WrapperError, ValueError) as error:
        logger.exception("Pyrefly wrapper infrastructure failure: %s", error)
        return INFRASTRUCTURE_EXIT_CODE
    except Exception as error:
        # Keep action failures explicit rather than traceback-only.
        logger.exception("Unexpected Pyrefly wrapper failure: %s", error)
        return INFRASTRUCTURE_EXIT_CODE
