"""Implementation of the wrapper's ``minify`` subcommand."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .config import resolve_source_layout
from .mapped_stubs import (
    inspect_mapped_stub_overlay,
    runtime_supplements,
)
from .source_utils import (
    collect_type_relevant_files,
    copy_file,
    native_extension_suffix,
)
from .transformed import (
    finalize_transformed_tree,
    is_repository_path,
    repository_relative_path,
)

if TYPE_CHECKING:
    from .cli import MinifyOptions


logger = logging.getLogger(__name__)


def run(args: MinifyOptions) -> int:
    """Materialize the type-relevant subset of a target's files."""
    direct_inputs = args.direct_inputs()
    mapped_stub_context = args.mapped_stub_context()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    files = [
        source
        for source in collect_type_relevant_files(direct_inputs.paths)
        if is_repository_path(
            source,
            args.repository_root,
            args.bazel_bin_dir,
        )
    ]
    source_layout = resolve_source_layout(
        files,
        direct_inputs.import_roots,
        args.bazel_bin_dir,
        args.repository_root,
    )
    mapped_stub = inspect_mapped_stub_overlay(
        mapped_stub_context,
        args.bazel_bin_dir,
        args.input_root,
    )
    files = runtime_supplements(
        files,
        source_layout.effective_roots,
        args.input_root,
        mapped_stub,
    )
    copied = 0
    for source in files:
        if native_extension_suffix(source) is not None:
            continue
        copy_file(
            source,
            args.output_dir
            / repository_relative_path(
                source,
                args.repository_root,
                args.bazel_bin_dir,
            ),
        )
        copied += 1
    finalize_transformed_tree(
        files,
        source_layout.declared_roots,
        mapped_stub,
        mapped_stub_context,
        args,
    )
    logger.debug(
        "Minified %d type-relevant files from %d declared inputs",
        copied,
        len(direct_inputs.paths),
    )
    return 0
