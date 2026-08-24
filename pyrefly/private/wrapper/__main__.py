"""Executable entry point for the Bazel Pyrefly wrapper."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
