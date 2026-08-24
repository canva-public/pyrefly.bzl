"""A macro for running tests with pytest."""

load("@pytest_deps//:requirements.bzl", "requirement")
load("@rules_python//python:py_test.bzl", "py_test")

_PYTEST_BAZEL_PKG = requirement("pytest-bazel")

def _pytest_test_impl(
        name,
        visibility,
        srcs,
        deps,
        data,
        env,
        args,
        **kwargs):
    args = [
        "$(location %s)" % src
        for src in (srcs or [])
    ] + (args or [])

    py_test(
        name = name,
        args = args,
        data = data,
        deps = [_PYTEST_BAZEL_PKG] + (deps or []),
        env = env,
        main_module = "pytest_bazel",
        srcs = srcs,
        visibility = visibility,
        **kwargs
    )

pytest_test = macro(
    implementation = _pytest_test_impl,
    inherit_attrs = "common",
    attrs = {
        "args": attr.string_list(default = [], configurable = False),
        "data": attr.label_list(default = [], configurable = False),
        "deps": attr.label_list(default = [], configurable = False),
        "env": attr.string_dict(default = {}, configurable = False),
        "srcs": attr.label_list(default = [], configurable = False),
    },
    doc = "Defines a py_test that uses pytest-bazel as its entry point.",
)
