"""Project-local Pyrefly aspects used by this repository."""

load("//:pyrefly.bzl", "make_pyrefly_aspect")

_CONFIGURATION = Label("//tools/pyrefly:pyrefly_config")

pyrefly_aspect = make_pyrefly_aspect(configuration = _CONFIGURATION)
