"""Project-local Pyrefly aspects used by this repository."""

load(
    "//:pyrefly.bzl",
    "make_pyrefly_aspect",
    "make_pyrefly_update_baseline_aspect",
)

_CONFIGURATION = Label("//tools/pyrefly:pyrefly_config")

pyrefly_aspect = make_pyrefly_aspect(configuration = _CONFIGURATION)
pyrefly_update_baseline_aspect = make_pyrefly_update_baseline_aspect(
    pyrefly_aspect = pyrefly_aspect,
    configuration = _CONFIGURATION,
)
