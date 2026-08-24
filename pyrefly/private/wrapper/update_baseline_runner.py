"""Implementation of the wrapper's ``update-baseline`` subcommand."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from . import check_runner
from .utils import INFRASTRUCTURE_EXIT_CODE, CommandTimeout, WrapperError

if TYPE_CHECKING:
    from .cli import UpdateBaselineOptions

logger = logging.getLogger(__name__)


def run(args: UpdateBaselineOptions) -> int:
    """Generate a complete baseline without reading an existing baseline."""
    args.output_baseline.parent.mkdir(parents=True, exist_ok=True)
    args.output_baseline.unlink(missing_ok=True)
    try:
        result = check_runner.invoke(
            args,
            baseline=args.output_baseline,
            update_baseline=True,
        )
    except CommandTimeout as error:
        logger.error(
            "Pyrefly infrastructure failure for %s: %s",
            args.target_label,
            error,
        )
        return INFRASTRUCTURE_EXIT_CODE

    if result is None:
        args.output_baseline.write_text('{\n  "errors": []\n}\n')
        return 0
    if result.output:
        logger.debug(result.output.rstrip("\n"))
    if result.returncode not in (0, 1):
        logger.error(
            "Pyrefly infrastructure failure for %s (exit code %d)",
            args.target_label,
            result.returncode,
        )
        return INFRASTRUCTURE_EXIT_CODE
    if not args.output_baseline.is_file():
        raise WrapperError(
            f"Pyrefly did not produce baseline output for {args.target_label}"
        )
    return 0
