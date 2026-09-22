"""Analysis tests for the workspace-owned Pyrefly configuration."""

load("@rules_python//python:defs.bzl", "py_library")
load("@rules_testing//lib:analysis_test.bzl", "analysis_test")
load("@rules_testing//lib:truth.bzl", "matching")
load("@rules_testing//lib:util.bzl", "TestingAspectInfo", "util")
load(
    "//:pyrefly.bzl",
    "make_pyrefly_aspect",
    "pyrefly_baselines",
    "pyrefly_configuration",
)
load(
    "//pyrefly/private:providers.bzl",
    "PyreflyConfigInfo",
    "PyreflyTargetEnvironmentInfo",
)

_PYPROJECT_CONFIGURATION = Label(
    "//tests/analysis:configuration_tests_pyproject_subject",
)
_PYPROJECT_ASPECT = make_pyrefly_aspect(
    configuration = _PYPROJECT_CONFIGURATION,
)
_PYPROJECT_TESTING_ASPECT = util.make_testing_aspect([_PYPROJECT_ASPECT])

def _expect_mutually_exclusive_tag_failure(env, target):
    """A configuration cannot combine include and exclude tag policies."""
    env.expect.that_target(target).failures().contains_predicate(
        matching.contains("pyrefly_configuration accepts either include_tags or exclude_tags, not both"),
    )

def _expect_unsupported_config_failure(env, target):
    """A configuration rejects files outside the supported filename contract."""
    env.expect.that_target(target).failures().contains_predicate(
        matching.contains("must name pyrefly.toml or pyproject.toml"),
    )

def _expect_configuration_contract(env, target):
    """The macro canonicalises policy and returns both configuration providers."""
    if PyreflyConfigInfo not in target:
        env.fail("configuration target does not provide PyreflyConfigInfo")
        return
    if PyreflyTargetEnvironmentInfo not in target:
        env.fail("configuration target does not provide PyreflyTargetEnvironmentInfo")
        return

    config = target[PyreflyConfigInfo]
    if config.base_config.short_path != "tests/analysis/pyrefly.toml":
        env.fail("unexpected direct config path {}".format(config.base_config.short_path))
    if "PyreflyExtractConfig" in [
        action.mnemonic
        for action in target[TestingAspectInfo].actions
    ]:
        env.fail("a direct pyrefly.toml unexpectedly registered extraction")

    expected_failure = str(Label(
        "//tests/analysis:configuration_tests_nonexistent_expected_failure",
    ))
    if config.expected_failure_labels != set([expected_failure]):
        env.fail("unexpected expected-failure labels {}".format(
            config.expected_failure_labels,
        ))

    expected_stub_keys = [
        str(Label("//tests/analysis:configuration_tests_runtime_a")),
        str(Label("//tests/analysis:configuration_tests_runtime_z")),
    ]
    actual_stub_keys = config.stub_packages.keys()
    if actual_stub_keys != expected_stub_keys:
        env.fail("expected deterministic resolved stub keys {}, got {}".format(
            expected_stub_keys,
            actual_stub_keys,
        ))

    baseline = config.baselines.get(Label("//:root_target"))
    if not baseline or baseline.short_path != "tests/analysis/root_target.json":
        env.fail("configuration did not retain the baseline mapping")

def _expect_pyproject_extraction(env, target):
    """A pyproject input becomes one derived pyrefly.toml action output."""
    config = target[PyreflyConfigInfo]
    if config.base_config.basename != "pyrefly.toml":
        env.fail("expected a derived pyrefly.toml, got {}".format(
            config.base_config.basename,
        ))
    if config.base_config.is_source or "_effective/pyrefly.toml" not in config.base_config.short_path:
        env.fail("unexpected extracted config path {}".format(config.base_config.short_path))

    action = env.expect.that_target(target).action_named("PyreflyExtractConfig")
    action.argv().contains_at_least([
        "extract-config",
        "--input-config",
        "tests/analysis/pyproject.toml",
        "--output-config",
        "{bindir}/tests/analysis/configuration_tests_pyproject_subject_effective/pyrefly.toml",
        "--otlp-trace-output",
        "{bindir}/tests/analysis/configuration_tests_pyproject_subject_pyrefly_extract_config_otlp_trace.jsonl",
    ]).in_order()
    action.inputs().contains("tests/analysis/pyproject.toml")
    env.expect.that_target(target).output_group(
        "pyrefly_otlp_traces",
    ).contains_exactly([
        "{package}/configuration_tests_pyproject_subject_pyrefly_extract_config_otlp_trace.jsonl",
    ])

def _expect_check_uses_extracted_config(env, target):
    """PyreflyCheck consumes the extracted file and not the original pyproject."""
    actions = [
        action
        for action in target[TestingAspectInfo].actions
        if action.mnemonic == "PyreflyCheck"
    ]
    if len(actions) != 1:
        env.fail("expected one PyreflyCheck action, got {}".format(len(actions)))
        return
    input_paths = [file.short_path for file in actions[0].inputs.to_list()]
    extracted = "tests/analysis/configuration_tests_pyproject_subject_effective/pyrefly.toml"
    if extracted not in input_paths:
        env.fail("PyreflyCheck did not consume {}".format(extracted))
    if "tests/analysis/pyproject.toml" in input_paths:
        env.fail("PyreflyCheck consumed the original pyproject.toml")

def configuration_test_suite(name):
    """Instantiate configuration analysis tests."""
    pyrefly_configuration(
        name = name + "_mutually_exclusive_tags_subject",
        exclude_tags = ["no-pyrefly"],
        include_tags = ["pyrefly"],
        tags = ["manual"],
    )
    mutually_exclusive_test = name + "_mutually_exclusive_tags"
    analysis_test(
        name = mutually_exclusive_test,
        expect_failure = True,
        impl = _expect_mutually_exclusive_tag_failure,
        target = name + "_mutually_exclusive_tags_subject",
    )

    pyrefly_configuration(
        name = name + "_unsupported_config_subject",
        config = "settings.toml",
        tags = ["manual"],
    )
    unsupported_config_test = name + "_unsupported_config"
    analysis_test(
        name = unsupported_config_test,
        expect_failure = True,
        impl = _expect_unsupported_config_failure,
        target = name + "_unsupported_config_subject",
    )

    py_library(
        name = name + "_runtime_a",
        srcs = ["dependency.py"],
        tags = ["manual"],
        visibility = ["//visibility:public"],
    )
    py_library(
        name = name + "_runtime_z",
        srcs = ["dependency.py"],
        tags = ["manual"],
        visibility = ["//visibility:public"],
    )
    py_library(
        name = name + "_stubs_a",
        pyi_srcs = ["dependency.pyi"],
        tags = ["manual"],
        visibility = ["//visibility:public"],
    )
    py_library(
        name = name + "_stubs_z",
        pyi_srcs = ["dependency.pyi"],
        tags = ["manual"],
        visibility = ["//visibility:public"],
    )
    native.alias(
        name = name + "_runtime_a_alias",
        actual = name + "_runtime_a",
        tags = ["manual"],
        visibility = ["//visibility:public"],
    )
    native.alias(
        name = name + "_runtime_z_alias",
        actual = name + "_runtime_z",
        tags = ["manual"],
        visibility = ["//visibility:public"],
    )
    native.alias(
        name = name + "_stubs_a_alias",
        actual = name + "_stubs_a",
        tags = ["manual"],
        visibility = ["//visibility:public"],
    )
    native.alias(
        name = name + "_stubs_z_alias",
        actual = name + "_stubs_z",
        tags = ["manual"],
        visibility = ["//visibility:public"],
    )
    pyrefly_baselines(
        name = name + "_baselines",
        srcs = ["root_target.json"],
        tags = ["manual"],
        update_aspect = "//tools/pyrefly:pyrefly_aspects.bzl%pyrefly_update_baseline_aspect",
    )
    pyrefly_configuration(
        name = name + "_contract_subject",
        baselines = name + "_baselines",
        config = "pyrefly.toml",
        expected_failures = [name + "_nonexistent_expected_failure"],
        stub_packages = {
            name + "_runtime_z_alias": name + "_stubs_z_alias",
            name + "_runtime_a_alias": name + "_stubs_a_alias",
        },
        tags = ["manual"],
    )
    contract_test = name + "_contract"
    analysis_test(
        name = contract_test,
        impl = _expect_configuration_contract,
        target = name + "_contract_subject",
    )

    pyrefly_configuration(
        name = name + "_pyproject_subject",
        config = "pyproject.toml",
        tags = ["manual"],
    )
    extraction_test = name + "_pyproject_extraction"
    analysis_test(
        name = extraction_test,
        impl = _expect_pyproject_extraction,
        target = name + "_pyproject_subject",
    )
    py_library(
        name = name + "_pyproject_check_subject",
        srcs = ["consumer.py"],
        tags = ["manual"],
    )
    check_test = name + "_check_uses_extracted_config"
    analysis_test(
        name = check_test,
        impl = _expect_check_uses_extracted_config,
        target = name + "_pyproject_check_subject",
        testing_aspect = _PYPROJECT_TESTING_ASPECT,
    )

    native.test_suite(
        name = name,
        tests = [
            check_test,
            contract_test,
            extraction_test,
            mutually_exclusive_test,
            unsupported_config_test,
        ],
    )
