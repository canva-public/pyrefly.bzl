"""Target platforms and Python runtimes used by target-environment tests."""

load(
    "@rules_python//python:defs.bzl",
    "py_runtime",
    "py_runtime_pair",
)

_PLATFORMS = [
    struct(
        name = "android",
        os_constraint = "@platforms//os:android",
    ),
    struct(
        name = "emscripten",
        os_constraint = "@platforms//os:emscripten",
    ),
    struct(
        name = "freebsd",
        os_constraint = "@platforms//os:freebsd",
    ),
    struct(
        name = "ios",
        os_constraint = "@platforms//os:ios",
    ),
    struct(
        name = "wasi",
        os_constraint = "@platforms//os:wasi",
    ),
    struct(
        name = "windows",
        os_constraint = "@platforms//os:windows",
    ),
]

def target_environment_toolchains():
    """Declare analysis-only platforms and target Python toolchains."""
    native.constraint_setting(name = "test_runtime")

    py_runtime(
        name = "python_runtime",
        interpreter_path = "/usr/bin/python3",
        interpreter_version_info = {
            "major": "3",
            "micro": "11",
            "minor": "13",
        },
        python_version = "PY3",
    )
    py_runtime_pair(
        name = "python_runtime_pair",
        py3_runtime = ":python_runtime",
    )

    for platform in _PLATFORMS:
        runtime_constraint = platform.name + "_runtime"
        native.constraint_value(
            name = runtime_constraint,
            constraint_setting = ":test_runtime",
        )
        native.platform(
            name = platform.name + "_target",
            constraint_values = [
                platform.os_constraint,
                ":" + runtime_constraint,
            ],
        )
        native.toolchain(
            name = platform.name + "_python_toolchain",
            target_compatible_with = [
                platform.os_constraint,
                ":" + runtime_constraint,
            ],
            toolchain = ":python_runtime_pair",
            toolchain_type = "@rules_python//python:toolchain_type",
        )
