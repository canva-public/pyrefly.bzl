"""Shared helpers for the Pyrefly wrapper."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

INFRASTRUCTURE_EXIT_CODE = 3


class WrapperError(RuntimeError):
    """An infrastructure error that prevents the wrapper from doing its work."""


class CommandTimeout(WrapperError):
    """Raised when a wrapper subprocess exceeds its timeout."""


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    output: str


def deduplicate_paths(paths: Iterable[Path]) -> list[Path]:
    """Remove duplicate rendered paths while preserving their original order."""
    result: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        rendered = str(path)
        if rendered not in seen:
            seen.add(rendered)
            result.append(path)
    return result


def resolve_executable(executable_path: str) -> Path:
    """Expand an execroot-relative action input and validate the executable."""
    candidate = Path(executable_path)
    if not candidate.is_absolute():
        # File.path is intentionally serialized into the action as an
        # execroot-relative path. Make it absolute only inside the running
        # spawn so action keys never contain a local output-base path. Do not
        # call resolve(): sandbox inputs may be symlinks into a local cache.
        candidate = Path.cwd() / candidate

    if not candidate.is_file():
        raise WrapperError(f"Pyrefly executable does not exist: {candidate}")
    if not os.access(candidate, os.X_OK):
        raise WrapperError(f"Pyrefly executable is not executable: {candidate}")
    return candidate


def run_command(
    command: Sequence[str | os.PathLike[str]],
    *,
    cwd: Path | None = None,
    timeout: float,
    env: Mapping[str, str] | None = None,
) -> CommandResult:
    """Run a subprocess with consistent capture and timeout reporting."""
    rendered = [os.fspath(part) for part in command]
    try:
        result = subprocess.run(
            rendered,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise CommandTimeout(
            f"Command timed out after {timeout:g}s: {' '.join(rendered[:2])}"
        ) from error
    except OSError as error:
        raise WrapperError(f"Unable to execute {rendered[0]!r}: {error}") from error
    return CommandResult(result.returncode, result.stdout)
