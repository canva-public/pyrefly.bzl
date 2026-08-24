"""Construction of the per-target Pyrefly check action."""

load("@bazel_skylib//rules:common_settings.bzl", "BuildSettingInfo")
load(":providers.bzl", "PyreflyConfigInfo")

def _fixed_args(ctx, target, pyrefly, target_environment, command):
    fixed_args = ctx.actions.args()
    fixed_args.add(command)
    fixed_args.add("--log-level")
    fixed_args.add(ctx.attr._log_level[BuildSettingInfo].value)
    fixed_args.add("--pyrefly-executable")
    fixed_args.add(pyrefly.executable)
    fixed_args.add("--bazel-bin-dir")
    fixed_args.add(ctx.bin_dir.path)
    fixed_args.add("--python-platform")
    fixed_args.add(target_environment.python_platform)
    fixed_args.add("--python-version")
    fixed_args.add(target_environment.python_version)

    # Keep canonical labels on the same argv token as the flag. The wrapper
    # expands '@file' arguments, so a standalone '@@repo//...' value would be
    # mistaken for a second parameter file.
    fixed_args.add(target.label, format = "--target-label=%s")
    return fixed_args

def _input_args(ctx, check_sources, target_inputs, target_imports, dependency_info):
    input_args = ctx.actions.args()
    input_args.add_all(check_sources, before_each = "--source-file")
    input_args.add_all(target_imports, before_each = "--import-path")
    input_args.add_all(
        dependency_info.imports,
        before_each = "--transformed-dependency-path",
    )
    input_args.add_all(
        target_inputs,
        before_each = "--input-path",
        expand_directories = False,
    )
    input_args.use_param_file("@%s", use_always = True)
    input_args.set_param_file_format("multiline")
    return input_args

def _common_inputs(config, target_inputs, dependency_info):
    inputs = [
        target_inputs,
        dependency_info.sources,
    ]
    if config.base_config:
        inputs.append(depset([config.base_config]))
    return inputs

def create_pyrefly_check_action(
        ctx,
        target,
        check_sources,
        target_inputs,
        target_imports,
        dependency_info,
        pyrefly,
        transitive_validation,
        target_environment,
        baseline = None):
    """Register a check action and return its validation output depset."""
    config = ctx.attr._pyrefly_config[PyreflyConfigInfo]
    marker = ctx.actions.declare_file(target.label.name + "_pyrefly_check.marker")
    expected_to_fail = str(target.label) in config.expected_failure_labels
    warning_output = None
    check_outputs = [marker]
    if expected_to_fail:
        warning_output = ctx.actions.declare_file(
            target.label.name + "_pyrefly_expected_failure.txt",
        )
        check_outputs.append(warning_output)

    fixed_args = _fixed_args(ctx, target, pyrefly, target_environment, "check")
    fixed_args.add("--output-marker")
    fixed_args.add(marker)
    if expected_to_fail:
        fixed_args.add("--expected-to-fail")
        fixed_args.add("--warning-output")
        fixed_args.add(warning_output)
        fixed_args.add("--stale-message")
        fixed_args.add(config.stale_message)
    if config.base_config:
        fixed_args.add("--base-config")
        fixed_args.add(config.base_config)
    if baseline:
        fixed_args.add("--baseline")
        fixed_args.add(baseline)

    input_args = _input_args(
        ctx,
        check_sources,
        target_inputs,
        target_imports,
        dependency_info,
    )

    inputs = _common_inputs(config, target_inputs, dependency_info)
    if baseline:
        inputs.append(depset([baseline]))

    ctx.actions.run(
        executable = config.wrapper,
        arguments = [fixed_args, input_args],
        inputs = depset(transitive = inputs),
        outputs = check_outputs,
        mnemonic = "PyreflyCheck",
        progress_message = "Pyrefly type checking %{label}",
        tools = [pyrefly],
        use_default_shell_env = True,
    )
    warnings = None
    if warning_output:
        display_marker = ctx.actions.declare_file(
            target.label.name + "_pyrefly_display_warnings.marker",
        )
        display_args = ctx.actions.args()
        display_args.add("display-warnings")
        display_args.add("--output-marker")
        display_args.add(display_marker)
        display_args.add("--warning-file")
        display_args.add(warning_output)

        ctx.actions.run(
            executable = config.wrapper,
            arguments = [display_args],
            inputs = [warning_output],
            outputs = [display_marker],
            mnemonic = "PyreflyDisplayWarnings",
            progress_message = "Displaying Pyrefly warnings for %{label}",
        )
        warnings = depset([display_marker])

    return struct(
        validation = depset([marker], transitive = transitive_validation),
        warnings = warnings,
    )

def create_pyrefly_update_baseline_action(
        ctx,
        target,
        check_sources,
        target_inputs,
        target_imports,
        dependency_info,
        pyrefly,
        target_environment):
    """Register a from-scratch baseline update action and return its output."""
    config = ctx.attr._pyrefly_config[PyreflyConfigInfo]
    output = ctx.actions.declare_file(
        target.label.name + "_pyrefly_updated_baseline.json",
    )

    fixed_args = _fixed_args(
        ctx,
        target,
        pyrefly,
        target_environment,
        "update-baseline",
    )
    fixed_args.add("--output-baseline")
    fixed_args.add(output)
    if config.base_config:
        fixed_args.add("--base-config")
        fixed_args.add(config.base_config)

    input_args = _input_args(
        ctx,
        check_sources,
        target_inputs,
        target_imports,
        dependency_info,
    )

    ctx.actions.run(
        executable = config.wrapper,
        arguments = [fixed_args, input_args],
        inputs = depset(
            transitive = _common_inputs(config, target_inputs, dependency_info),
        ),
        outputs = [output],
        mnemonic = "PyreflyUpdateBaseline",
        progress_message = "Updating Pyrefly baseline for %{label}",
        tools = [pyrefly],
        use_default_shell_env = True,
    )
    return output
