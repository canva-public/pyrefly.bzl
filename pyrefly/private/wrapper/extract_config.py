"""Extract the Pyrefly table from a project configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .config import dump_toml, load_base_config

if TYPE_CHECKING:
    from .cli import ExtractConfigOptions


def run(args: ExtractConfigOptions) -> int:
    """Write an effective pyrefly.toml containing only Pyrefly settings."""
    input_config = args.input_config
    output_config = args.output_config
    settings = load_base_config(input_config)
    output_config.parent.mkdir(parents=True, exist_ok=True)
    output_config.write_text(dump_toml(settings), encoding="utf-8")
    return 0
