"""Generate many import roots contributing to one shared namespace package."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--roots", type=int, required=True)
    parser.add_argument("--files-per-root", type=int, required=True)
    args = parser.parse_args()
    for root in range(args.roots):
        package = (
            args.output_dir
            / f"root_{root}"
            / "application"
            / "service"
            / "src"
            / "python"
            / "common"
        )
        package.mkdir(parents=True)
        for module in range(args.files_per_root):
            (package / f"module_{root}_{module}.pyi").write_text(
                "value: int\n", encoding="utf-8"
            )


if __name__ == "__main__":
    main()
