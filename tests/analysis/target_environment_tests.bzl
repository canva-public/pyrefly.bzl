"""Analysis tests for Python target-platform derivation."""

load("@rules_testing//lib:analysis_test.bzl", "analysis_test")
load("//pyrefly/private:providers.bzl", "PyreflyTargetEnvironmentInfo")

_TARGET_PLATFORMS = "//command_line_option:platforms"
_TEST_CASES = [
    struct(
        name = "android",
        python_platform = "android",
        python_version = "3.13.11",
    ),
    struct(
        name = "emscripten",
        python_platform = "emscripten",
        python_version = "3.13.11",
    ),
    struct(
        name = "freebsd",
        python_platform = "freebsd",
        python_version = "3.13.11",
    ),
    struct(
        name = "ios",
        python_platform = "ios",
        python_version = "3.13.11",
    ),
    struct(
        name = "wasi",
        python_platform = "wasi",
        python_version = "3.13.11",
    ),
    struct(
        name = "windows",
        python_platform = "win32",
        python_version = "3.13.11",
    ),
]

def _expect_target_environment(env, target):
    """The environment provider mirrors the configured Python target."""
    environment = target[PyreflyTargetEnvironmentInfo]
    if environment.python_platform != env.ctx.attr.expected_python_platform:
        env.fail("expected python-platform {}, got {}".format(
            env.ctx.attr.expected_python_platform,
            environment.python_platform,
        ))
    if environment.python_version != env.ctx.attr.expected_python_version:
        env.fail("expected python-version {}, got {}".format(
            env.ctx.attr.expected_python_version,
            environment.python_version,
        ))

def target_environment_test_suite(name):
    """Generate one behavioral test for each supported target platform."""
    tests = []
    for test_case in _TEST_CASES:
        test_name = name + "_" + test_case.name
        tests.append(test_name)
        analysis_test(
            name = test_name,
            impl = _expect_target_environment,
            attrs = {
                "expected_python_platform": attr.string(),
                "expected_python_version": attr.string(),
            },
            attr_values = {
                "expected_python_platform": test_case.python_platform,
                "expected_python_version": test_case.python_version,
            },
            config_settings = {
                _TARGET_PLATFORMS: [
                    str(Label(
                        "//tests/analysis/target_environment_toolchains:" +
                        test_case.name +
                        "_target",
                    )),
                ],
            },
            target = "//tools/pyrefly:pyrefly_config",
        )

    native.test_suite(
        name = name,
        tests = tests,
    )
