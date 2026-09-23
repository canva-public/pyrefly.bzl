"""Analysis tests for aspect action selection and output-group propagation."""

load("@rules_python//python:defs.bzl", "PyInfo", "py_library")
load("@rules_testing//lib:analysis_test.bzl", "analysis_test", "test_suite")
load("@rules_testing//lib:util.bzl", "TestingAspectInfo", "util")
load("//tools/pyrefly:pyrefly_aspects.bzl", "pyrefly_aspect")

_testing_aspect = util.make_testing_aspect([pyrefly_aspect])
_SUBJECT_TAGS = ["manual"]

def _generated_python_impl(ctx):
    source = ctx.actions.declare_file(ctx.label.name + ".py")
    stub = ctx.actions.declare_file(ctx.label.name + ".pyi")
    metadata = ctx.actions.declare_file(ctx.label.name + ".txt")
    ctx.actions.write(source, "value = 1\n")
    ctx.actions.write(stub, "value: int\n")
    ctx.actions.write(metadata, "not a Python input\n")
    return [
        DefaultInfo(files = depset([metadata])),
        PyInfo(
            direct_original_sources = depset([source]),
            direct_pyi_files = depset([stub]),
            imports = depset(),
            transitive_original_sources = depset([source]),
            transitive_pyi_files = depset([stub]),
            transitive_sources = depset([source]),
        ),
    ]

_generated_python = rule(
    implementation = _generated_python_impl,
    provides = [PyInfo],
)

def _default_only_python_impl(ctx):
    source = ctx.actions.declare_file(ctx.label.name + ".py")
    ctx.actions.write(source, "value = 1\n")
    return [
        DefaultInfo(files = depset([source])),
        PyInfo(
            direct_original_sources = depset(),
            direct_pyi_files = depset(),
            imports = depset(),
            transitive_original_sources = depset(),
            transitive_pyi_files = depset(),
            transitive_sources = depset(),
        ),
    ]

_default_only_python = rule(
    implementation = _default_only_python_impl,
    provides = [PyInfo],
)

def _generated_tree_python_impl(ctx):
    sources = ctx.actions.declare_directory(ctx.label.name + "_sources")
    ctx.actions.run_shell(
        outputs = [sources],
        command = """
mkdir -p "$1/package"
printf 'value = 1\\n' > "$1/package/__init__.py"
printf 'value: int\\n' > "$1/package/__init__.pyi"
""",
        arguments = [sources.path],
    )
    return [
        DefaultInfo(files = depset([sources])),
        PyInfo(
            direct_original_sources = depset([sources]),
            direct_pyi_files = depset(),
            imports = depset(),
            transitive_original_sources = depset([sources]),
            transitive_pyi_files = depset(),
            transitive_sources = depset([sources]),
        ),
    ]

_generated_tree_python = rule(
    implementation = _generated_tree_python_impl,
    provides = [PyInfo],
)

def _mnemonics(target):
    return [action.mnemonic for action in target[TestingAspectInfo].actions]

def _expect_action_selection(env, target, selected, unselected):
    mnemonics = _mnemonics(target)
    count = len([mnemonic for mnemonic in mnemonics if mnemonic == selected])
    if count != 1:
        env.fail("expected one {} action for {}, found {}".format(
            selected,
            target.label,
            count,
        ))
    for mnemonic in unselected:
        if mnemonic in mnemonics:
            env.fail("unexpected {} action for {}".format(mnemonic, target.label))

def _expect_check(env, target):
    _expect_action_selection(
        env,
        target,
        "PyreflyCheck",
        ["PyreflyStubgen", "PyreflyUpdateBaseline"],
    )
    _expect_action_selection(
        env,
        target,
        "PyreflyDisplayWarnings",
        [],
    )
    if (
        OutputGroupInfo in target and
        hasattr(target[OutputGroupInfo], "pyrefly_updated_baseline")
    ):
        env.fail("check mode exposed the baseline-update output group")

def _expect_minify(env, target):
    _expect_action_selection(
        env,
        target,
        "PyreflyMinify",
        ["PyreflyCheck", "PyreflyStubgen"],
    )

def _expect_stubgen(env, target):
    _expect_action_selection(
        env,
        target,
        "PyreflyStubgen",
        ["PyreflyCheck", "PyreflyMinify"],
    )

def _test_first_party_source_selects_check(name):
    """A first-party library with source files selects one check action."""
    py_library(
        name = name + "_subject",
        srcs = ["consumer.py"],
        tags = _SUBJECT_TAGS,
    )
    analysis_test(
        name = name,
        impl = _expect_check,
        target = name + "_subject",
        testing_aspect = _testing_aspect,
    )

def _test_configured_stub_mapping_selects_stubgen(name):
    """A mapped runtime package selects stubgen so partial mappings can be completed."""
    analysis_test(
        name = name,
        impl = _expect_stubgen,
        target = "@pyrefly_test_targets//:configured",
        testing_aspect = _testing_aspect,
    )

def _test_exact_alias_exclusion_selects_minify(name):
    """An exact exclusion referenced through an alias selects minify."""
    analysis_test(
        name = name,
        impl = _expect_minify,
        target = "@pyrefly_test_targets//:skipped",
        testing_aspect = _testing_aspect,
    )

def _test_unmatched_target_selects_minify(name):
    """A target outside all include selectors selects minify."""
    analysis_test(
        name = name,
        impl = _expect_minify,
        target = "@pyrefly_test_targets//:unmatched",
        testing_aspect = _testing_aspect,
    )

def _test_exact_alias_inclusion_selects_stubgen(name):
    """An exact inclusion referenced through an alias selects stubgen."""
    analysis_test(
        name = name,
        impl = _expect_stubgen,
        target = "@pyrefly_test_targets//:automatic",
        testing_aspect = _testing_aspect,
    )

def _test_excluded_package_group_selects_minify(name):
    """A package-group exclusion overrides a matching stubgen inclusion."""
    analysis_test(
        name = name,
        impl = _expect_minify,
        target = "@pyrefly_test_targets//nested:automatic",
        testing_aspect = _testing_aspect,
    )

def _test_included_descendant_selects_stubgen(name):
    """A package-group inclusion selects stubgen for descendant packages."""
    analysis_test(
        name = name,
        impl = _expect_stubgen,
        target = "@pyrefly_test_targets//nested/deeper:automatic",
        testing_aspect = _testing_aspect,
    )

def _test_generated_pyinfo_selects_minify(name):
    """A generated target represented by direct PyInfo sources selects minify."""
    _generated_python(
        name = name + "_subject",
        tags = _SUBJECT_TAGS,
    )
    analysis_test(
        name = name,
        impl = _expect_minify,
        target = name + "_subject",
        testing_aspect = _testing_aspect,
    )

def _test_generated_tree_selects_minify(name):
    """A generated target represented by a source TreeArtifact selects minify."""
    _generated_tree_python(
        name = name + "_subject",
        tags = _SUBJECT_TAGS,
    )
    analysis_test(
        name = name,
        impl = _expect_minify,
        target = name + "_subject",
        testing_aspect = _testing_aspect,
    )

def _test_empty_direct_pyinfo_selects_minify(name):
    """A generated target with Python only in DefaultInfo selects minify."""
    _default_only_python(
        name = name + "_subject",
        tags = _SUBJECT_TAGS,
    )
    analysis_test(
        name = name,
        impl = _expect_minify,
        target = name + "_subject",
        testing_aspect = _testing_aspect,
    )

def _test_public_stubs_rule_selects_stubgen(name):
    """The public pyrefly_stubs rule selects one stubgen action."""
    analysis_test(
        name = name,
        impl = _expect_public_stubgen,
        target = ":manual_stubs",
    )

def _expect_public_stubgen(env, target):
    action = env.expect.that_target(target).action_named("PyreflyStubgen")
    action.has_flags_specified(["--pyrefly-executable"])
    input_paths = [file.short_path for file in action.actual.inputs.to_list()]
    if "tools/pyrefly/pyrefly_config_effective/pyrefly.toml" not in input_paths:
        env.fail("pyrefly_stubs did not consume its explicit configuration")
    if "pyproject.toml" in input_paths:
        env.fail("pyrefly_stubs consumed the original pyproject.toml")
    env.expect.that_target(target).output_group(
        "pyrefly_otlp_traces",
    ).contains_exactly([
        "tests/analysis/manual_stubs_pyrefly_stubgen_otlp_trace.jsonl",
    ])

def _test_validation_outputs_propagate(name):
    """A validation group contains check outputs for a target and its dependency."""
    py_library(
        name = name + "_dependency",
        srcs = ["dependency.py"],
        tags = _SUBJECT_TAGS,
    )
    py_library(
        name = name + "_subject",
        srcs = ["consumer.py"],
        deps = [name + "_dependency"],
        tags = _SUBJECT_TAGS,
    )
    analysis_test(
        name = name,
        impl = _expect_validation_outputs,
        target = name + "_subject",
        testing_aspect = _testing_aspect,
    )

def _expect_validation_outputs(env, target):
    env.expect.that_target(target).output_group("_validation").contains_at_least([
        "{package}/test_validation_outputs_propagate_dependency_pyrefly.marker",
        "{package}/test_validation_outputs_propagate_subject_pyrefly.marker",
    ])

def _test_otlp_trace_outputs_are_direct(name):
    """The trace group contains only wrapper actions for the requested target."""
    py_library(
        name = name + "_dependency",
        srcs = ["dependency.py"],
        tags = _SUBJECT_TAGS,
    )
    py_library(
        name = name + "_subject",
        srcs = ["consumer.py"],
        deps = [name + "_dependency"],
        tags = _SUBJECT_TAGS,
    )
    analysis_test(
        name = name,
        impl = _expect_direct_otlp_trace_outputs,
        target = name + "_subject",
        testing_aspect = _testing_aspect,
    )

def _expect_direct_otlp_trace_outputs(env, target):
    env.expect.that_target(target).output_group(
        "pyrefly_otlp_traces",
    ).contains_exactly([
        "{package}/test_otlp_trace_outputs_are_direct_subject_pyrefly_minify_otlp_trace.jsonl",
        "{package}/test_otlp_trace_outputs_are_direct_subject_pyrefly_check_otlp_trace.jsonl",
        "{package}/test_otlp_trace_outputs_are_direct_subject_pyrefly_display_warnings_otlp_trace.jsonl",
    ])

def _test_check_exposes_diagnostic_output_groups(name):
    """Every check exposes full-text, JSON, SARIF, and warning outputs."""
    analysis_test(
        name = name,
        impl = _expect_diagnostic_outputs,
        target = "//tests/consumer:stale_expected_failure",
        testing_aspect = _testing_aspect,
    )

def _expect_diagnostic_outputs(env, target):
    _expect_check(env, target)
    env.expect.that_target(target).output_group("pyrefly_fulltext").contains_exactly([
        "tests/consumer/stale_expected_failure_pyrefly_fulltext.txt",
    ])
    env.expect.that_target(target).output_group("pyrefly_json").contains_exactly([
        "tests/consumer/stale_expected_failure_pyrefly.json",
    ])
    env.expect.that_target(target).output_group("pyrefly_sarif").contains_exactly([
        "tests/consumer/stale_expected_failure_pyrefly.sarif",
    ])
    env.expect.that_target(target).output_group("pyrefly_warnings").contains_exactly([
        "tests/consumer/stale_expected_failure_pyrefly_display_warnings.marker",
    ])

def _test_diagnostic_outputs_do_not_propagate(name):
    """A parent's diagnostic groups contain only its own check outputs."""
    py_library(
        name = name + "_subject",
        srcs = ["consumer.py"],
        deps = ["//tests/consumer:stale_expected_failure"],
        tags = _SUBJECT_TAGS,
    )
    analysis_test(
        name = name,
        impl = _expect_direct_diagnostic_outputs,
        target = name + "_subject",
        testing_aspect = _testing_aspect,
    )

def _expect_direct_diagnostic_outputs(env, target):
    env.expect.that_target(target).output_group("pyrefly_fulltext").contains_exactly([
        "{package}/test_diagnostic_outputs_do_not_propagate_subject_pyrefly_fulltext.txt",
    ])
    env.expect.that_target(target).output_group("pyrefly_json").contains_exactly([
        "{package}/test_diagnostic_outputs_do_not_propagate_subject_pyrefly.json",
    ])
    env.expect.that_target(target).output_group("pyrefly_sarif").contains_exactly([
        "{package}/test_diagnostic_outputs_do_not_propagate_subject_pyrefly.sarif",
    ])
    env.expect.that_target(target).output_group("pyrefly_warnings").contains_exactly([
        "{package}/test_diagnostic_outputs_do_not_propagate_subject_pyrefly_display_warnings.marker",
    ])

def aspect_test_suite(name):
    test_suite(
        name = name,
        tests = [
            _test_first_party_source_selects_check,
            _test_configured_stub_mapping_selects_stubgen,
            _test_exact_alias_exclusion_selects_minify,
            _test_unmatched_target_selects_minify,
            _test_exact_alias_inclusion_selects_stubgen,
            _test_excluded_package_group_selects_minify,
            _test_included_descendant_selects_stubgen,
            _test_generated_pyinfo_selects_minify,
            _test_generated_tree_selects_minify,
            _test_empty_direct_pyinfo_selects_minify,
            _test_public_stubs_rule_selects_stubgen,
            _test_validation_outputs_propagate,
            _test_otlp_trace_outputs_are_direct,
            _test_check_exposes_diagnostic_output_groups,
            _test_diagnostic_outputs_do_not_propagate,
        ],
    )
