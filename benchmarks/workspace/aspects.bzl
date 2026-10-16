"""Use the real Pyrefly aspect with the benchmark's external package policy."""

load("@pyrefly.bzl", "make_pyrefly_aspect")

pyrefly_aspect = make_pyrefly_aspect(
    configuration = Label("//:pyrefly_config"),
)
