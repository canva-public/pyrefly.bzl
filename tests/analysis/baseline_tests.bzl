"""Analysis tests for the public per-target baseline registry."""

load("@rules_testing//lib:analysis_test.bzl", "analysis_test")
load("@rules_testing//lib:truth.bzl", "matching")
load("//:pyrefly.bzl", "pyrefly_baselines")
load("//pyrefly/private:providers.bzl", "PyreflyBaselinesInfo")

def _expect_baseline_mapping(env, target):
    """Baseline paths map to root and nested target labels."""
    baselines = target[PyreflyBaselinesInfo].baselines
    expected = {
        Label("//:root_target"): "tests/analysis/root_target.json",
        Label("//nested/package:target"): "tests/analysis/nested/package/target.json",
    }
    if len(baselines) != len(expected):
        env.fail("expected {} baselines, got {}".format(len(expected), len(baselines)))
    for label, path in expected.items():
        baseline = baselines.get(label)
        if not baseline:
            env.fail("missing baseline for {}".format(label))
        elif baseline.short_path != path:
            env.fail("expected {} for {}, got {}".format(path, label, baseline.short_path))

    default_files = {file.short_path: None for file in target[DefaultInfo].files.to_list()}
    if default_files != {path: None for path in expected.values()}:
        env.fail("expected default files {}, got {}".format(expected.values(), default_files.keys()))
    if target[DefaultInfo].files_to_run.executable == None:
        env.fail("expected the baseline registry to be executable")

def _expect_source_file_failure(env, target):
    """Generated JSON outputs cannot be used as checked-in baselines."""
    env.expect.that_target(target).failures().contains_predicate(
        matching.contains("must be a source JSON file"),
    )

def _expect_package_root_failure(env, target):
    """Baseline files must live beneath the registry package."""
    env.expect.that_target(target).failures().contains_predicate(
        matching.contains("must be beneath the Pyrefly baselines package"),
    )

def baseline_test_suite(name):
    """Instantiate baseline-provider analysis tests."""
    pyrefly_baselines(
        name = name + "_mapping_subject",
        srcs = [
            "nested/package/target.json",
            "root_target.json",
        ],
        tags = ["manual"],
    )
    mapping_test = name + "_mapping"
    analysis_test(
        name = mapping_test,
        impl = _expect_baseline_mapping,
        target = name + "_mapping_subject",
    )

    native.genrule(
        name = name + "_generated_json",
        outs = [name + "_generated.json"],
        cmd = "echo '{\"errors\": []}' > $@",
        tags = ["manual"],
    )
    pyrefly_baselines(
        name = name + "_generated_subject",
        srcs = [name + "_generated_json"],
        tags = ["manual"],
    )
    generated_test = name + "_rejects_generated"
    analysis_test(
        name = generated_test,
        expect_failure = True,
        impl = _expect_source_file_failure,
        target = name + "_generated_subject",
    )

    pyrefly_baselines(
        name = name + "_outside_package_subject",
        srcs = ["//tests/fixtures:baseline.json"],
        tags = ["manual"],
    )
    outside_package_test = name + "_rejects_outside_package"
    analysis_test(
        name = outside_package_test,
        expect_failure = True,
        impl = _expect_package_root_failure,
        target = name + "_outside_package_subject",
    )

    native.test_suite(
        name = name,
        tests = [
            generated_test,
            mapping_test,
            outside_package_test,
        ],
    )
