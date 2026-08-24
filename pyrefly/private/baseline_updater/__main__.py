"""Entry point for the Pyrefly baseline updater."""

from __future__ import annotations

import sys

from .updater import main

if __name__ == "__main__":
    sys.exit(main())
