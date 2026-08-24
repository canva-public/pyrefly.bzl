"""Aspect that propagates Python inputs and registers Pyrefly actions."""

load("@bazel_skylib//rules:common_settings.bzl", "BuildSettingInfo")
load("@rules_python//python:defs.bzl", "PyInfo")
load(":configuration.bzl", "is_type_checking_enabled")
load(
    ":providers.bzl",
    "PyreflyCheckInputsInfo",
    "PyreflyConfigInfo",
    "PyreflyInfo",
    "PyreflyTargetEnvironmentInfo",
)
load(
    ":pyrefly_check.bzl",
    "create_pyrefly_check_action",
    "create_pyrefly_update_baseline_action",
)
load(":pyrefly_minify.bzl", "create_pyrefly_minify_action")
load(":pyrefly_stubs.bzl", "create_pyrefly_stubgen_action")

_MAIN_REPOSITORY = ""
_LOG_LEVEL = Label("@pyrefly.bzl//pyrefly:log_level")
_PYREFLY_TOOLCHAIN_TYPE = Label("//pyrefly:toolchain_type")
_PYTHON_IMPORT_ALL_REPOSITORIES = Label(
    "@rules_python//python/config_settings:experimental_python_import_all_repositories",
)

def _check_sources(ctx):
    """Return source files declared by the rule that should be checked."""
    sources = []
    for attribute in ("srcs", "pyi_srcs"):
        for file in getattr(ctx.rule.files, attribute, []):
            if file.is_source and file.extension in ("py", "pyi", "ipynb"):
                sources.append(file)
    return sources

def _fallback_python_inputs(ctx):
    """Return direct Python inputs for rules whose PyInfo omits direct fields."""
    return [
        file
        for file in getattr(ctx.rule.files, "srcs", [])
        if file.extension == "py"
    ]

def _supplementary_data_inputs(ctx):
    """Return stub files from data which supplement a target's direct inputs."""
    return [
        file
        for file in getattr(ctx.rule.files, "data", [])
        if file.extension == "pyi" or file.basename == "py.typed"
    ]

def _matches_stubgen_selectors(selectors, label):
    if str(label) in selectors.exact_labels:
        return True
    for package_group in selectors.package_groups:
        if package_group.contains(label):
            return True
    return False

def _should_stubgen(config, label):
    if _matches_stubgen_selectors(config.stubgen_exclude, label):
        return False
    return _matches_stubgen_selectors(config.stubgen_include, label)

def _aspect_impl(target, ctx):
    check_sources = _check_sources(ctx)
    supplementary_data_inputs = _supplementary_data_inputs(ctx)
    dependencies = (
        getattr(ctx.rule.attr, "deps", []) +
        getattr(ctx.rule.attr, "pyi_deps", [])
    )

    transitive_sources = []
    transitive_imports = []
    transitive_validation = []
    for dependency in dependencies:
        if PyreflyInfo in dependency:
            info = dependency[PyreflyInfo]
            transitive_sources.append(info.sources)
            transitive_imports.append(info.imports)
        if OutputGroupInfo in dependency and hasattr(dependency[OutputGroupInfo], "_validation"):
            transitive_validation.append(dependency[OutputGroupInfo]._validation)

    dependency_info = PyreflyInfo(
        imports = depset(transitive = transitive_imports),
        sources = depset(transitive = transitive_sources),
    )

    direct_original_sources = target[PyInfo].direct_original_sources
    direct_pyi_files = target[PyInfo].direct_pyi_files
    target_imports = target[PyInfo].imports
    if direct_original_sources or direct_pyi_files:
        target_inputs = depset(
            direct = supplementary_data_inputs,
            transitive = [
                direct_original_sources,
                direct_pyi_files,
            ],
        )
    else:
        fallback_inputs = _fallback_python_inputs(ctx)
        if fallback_inputs:
            target_inputs = depset(fallback_inputs + supplementary_data_inputs)
        elif DefaultInfo in target:
            target_inputs = target[DefaultInfo].files
        else:
            target_inputs = depset(supplementary_data_inputs)

    config_target = ctx.attr._pyrefly_config
    config = config_target[PyreflyConfigInfo]
    pyrefly = ctx.toolchains[_PYREFLY_TOOLCHAIN_TYPE].files_to_run
    target_environment = config_target[PyreflyTargetEnvironmentInfo]
    type_checking_enabled = is_type_checking_enabled(
        config,
        getattr(ctx.rule.attr, "tags", []),
    )
    configured_stub = config.stub_packages.get(str(target.label))
    retain_repository_root = (
        target.label.repo_name == _MAIN_REPOSITORY or
        ctx.attr._python_import_all_repositories[BuildSettingInfo].value
    )

    if _should_stubgen(config, target.label):
        transformed = create_pyrefly_stubgen_action(
            ctx,
            target,
            config,
            pyrefly,
            ctx.attr._log_level[BuildSettingInfo].value,
            retain_repository_root,
            target_environment,
            include_docstrings = config.stubgen_include_docstrings,
            include_private = config.stubgen_include_private,
            dependency_info = dependency_info,
            mapped_stub = configured_stub,
            target_inputs = target_inputs,
        )
    else:
        transformed = create_pyrefly_minify_action(
            ctx,
            target,
            config,
            ctx.attr._log_level[BuildSettingInfo].value,
            target_inputs,
            retain_repository_root,
            mapped_stub = configured_stub,
        )

    info = PyreflyInfo(
        imports = depset(
            direct = [transformed.path],
            transitive = transitive_imports,
        ),
        sources = depset(
            direct = [transformed],
            transitive = transitive_sources,
        ),
    )

    should_check = (
        type_checking_enabled and
        target.label.repo_name == _MAIN_REPOSITORY and
        check_sources
    )
    check_inputs = PyreflyCheckInputsInfo(
        check_sources = depset(check_sources),
        dependency_info = dependency_info,
        enabled = should_check,
        target_imports = target_imports,
        target_inputs = target_inputs,
    )
    result = [info, check_inputs]
    if should_check:
        baseline = config.baselines.get(target.label)
        check_outputs = create_pyrefly_check_action(
            ctx,
            target,
            check_sources,
            target_inputs,
            target_imports,
            dependency_info,
            pyrefly,
            transitive_validation,
            target_environment,
            baseline = baseline,
        )
        if check_outputs.warnings:
            result.append(OutputGroupInfo(
                _validation = check_outputs.validation,
                pyrefly_warnings = check_outputs.warnings,
            ))
        else:
            result.append(OutputGroupInfo(_validation = check_outputs.validation))
        return result
    if transitive_validation:
        result.append(
            OutputGroupInfo(_validation = depset(transitive = transitive_validation)),
        )
    return result

def _update_baseline_aspect_impl(target, ctx):
    check_inputs = target[PyreflyCheckInputsInfo]
    if not check_inputs.enabled:
        return []

    output = create_pyrefly_update_baseline_action(
        ctx,
        target,
        check_inputs.check_sources,
        check_inputs.target_inputs,
        check_inputs.target_imports,
        check_inputs.dependency_info,
        ctx.toolchains[_PYREFLY_TOOLCHAIN_TYPE].files_to_run,
        ctx.attr._pyrefly_config[PyreflyTargetEnvironmentInfo],
    )
    return [
        OutputGroupInfo(pyrefly_updated_baseline = depset([output])),
    ]

def _check_action_attrs(configuration):
    if type(configuration) != "Label":
        fail("configuration must be a Label")
    return {
        "_pyrefly_config": attr.label(
            default = configuration,
            providers = [PyreflyConfigInfo, PyreflyTargetEnvironmentInfo],
        ),
        "_log_level": attr.label(
            default = _LOG_LEVEL,
            providers = [BuildSettingInfo],
        ),
    }

def make_pyrefly_aspect(configuration):
    """Construct the validation aspect with workspace-owned configuration.

    Args:
        configuration: Label of a pyrefly_configuration target.

    Returns:
        An aspect which checks first-party Python targets and propagates dependency interfaces.
    """
    attrs = _check_action_attrs(configuration)
    attrs.update({
        "_python_import_all_repositories": attr.label(
            default = _PYTHON_IMPORT_ALL_REPOSITORIES,
            providers = [BuildSettingInfo],
        ),
    })
    return aspect(
        implementation = _aspect_impl,
        attr_aspects = [
            "deps",
            "pyi_deps",
        ],
        attrs = attrs,
        doc = "Type-checks source targets and propagates hermetic Python inputs.",
        provides = [PyreflyCheckInputsInfo, PyreflyInfo],
        required_providers = [[PyInfo]],
        toolchains = [_PYREFLY_TOOLCHAIN_TYPE],
    )

def make_pyrefly_update_baseline_aspect(
        pyrefly_aspect,
        configuration):
    """Construct the on-demand aspect which generates fresh baselines.

    Args:
        pyrefly_aspect: Validation aspect returned by make_pyrefly_aspect.
        configuration: Label of the pyrefly_configuration target used by pyrefly_aspect.

    Returns:
        An aspect which publishes fresh baseline files through pyrefly_updated_baseline.
    """
    return aspect(
        implementation = _update_baseline_aspect_impl,
        attrs = _check_action_attrs(configuration),
        doc = "Generates fresh per-target Pyrefly baseline files on demand.",
        required_aspect_providers = [[PyreflyCheckInputsInfo]],
        required_providers = [[PyInfo]],
        requires = [pyrefly_aspect],
        toolchains = [_PYREFLY_TOOLCHAIN_TYPE],
    )
