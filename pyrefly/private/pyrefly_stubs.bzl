"""Stub generation shared by the Pyrefly aspect and public rule."""

load("@bazel_skylib//rules:common_settings.bzl", "BuildSettingInfo")
load("@rules_python//python:defs.bzl", "PyInfo")
load(
    ":providers.bzl",
    "PyreflyConfigInfo",
    "PyreflyTargetEnvironmentInfo",
)

_LOG_LEVEL = Label("@pyrefly.bzl//pyrefly:log_level")
_PYREFLY_TOOLCHAIN_TYPE = Label("//pyrefly:toolchain_type")
_PYTHON_IMPORT_ALL_REPOSITORIES = Label(
    "@rules_python//python/config_settings:experimental_python_import_all_repositories",
)

def create_pyrefly_stubgen_action(
        ctx,
        target,
        config,
        pyrefly,
        log_level,
        retain_repository_root,
        target_environment,
        target_inputs,
        include_docstrings = False,
        include_private = False,
        dependency_info = None,
        mapped_stub = None,
        output_name = None):
    """Register a stubgen action for a Python target and return its TreeArtifact."""
    output = ctx.actions.declare_directory(
        output_name or target.label.name + "_pyrefly_stubs",
    )
    transitive_inputs = []
    imports = target[PyInfo].imports
    dependency_imports = depset()
    if mapped_stub == None:
        mapped_stub = config.stub_packages.get(str(target.label))
    if dependency_info:
        transitive_inputs.append(dependency_info.sources)
        dependency_imports = dependency_info.imports
    else:
        # The public rule has no aspect-propagated dependency view, so retain
        # the complete original source and stub closure for generation.
        transitive_inputs.append(target[PyInfo].transitive_original_sources)
        transitive_inputs.append(target[PyInfo].transitive_pyi_files)
    if mapped_stub:
        transitive_inputs.append(mapped_stub.files)

    dependency_inputs = depset(transitive = transitive_inputs)
    inputs = depset(
        direct = [config.base_config] if config.base_config else [],
        transitive = [
            target_inputs,
            dependency_inputs,
        ],
    )

    args = ctx.actions.args()
    args.add("stubgen")
    args.add("--log-level")
    args.add(log_level)
    if include_docstrings:
        args.add("--include-docstrings")
    if include_private:
        args.add("--include-private")
    args.add("--pyrefly-executable")
    args.add(pyrefly.executable)
    args.add("--output-dir")
    args.add(output.path)
    args.add("--bazel-bin-dir")
    args.add(ctx.bin_dir.path)
    args.add("--python-platform")
    args.add(target_environment.python_platform)
    args.add("--python-version")
    args.add(target_environment.python_version)
    if config.base_config:
        args.add("--base-config")
        args.add(config.base_config)
    args.add("--input-root")
    args.add(".")
    args.add("--repository-root")
    args.add(target.label.workspace_root or ".")
    if retain_repository_root:
        args.add("--retain-repository-root")
    args.add_all(
        target_inputs,
        before_each = "--input-path",
        expand_directories = False,
    )
    args.add_all(imports, before_each = "--import-path")
    args.add_all(
        dependency_imports,
        before_each = "--transformed-dependency-path",
    )
    if not dependency_info:
        args.add_all(imports, before_each = "--dependency-import-path")
    if mapped_stub:
        args.add_all(
            mapped_stub.direct_files,
            before_each = "--mapped-stub-path",
            expand_directories = False,
        )
        args.add_all(
            mapped_stub.imports,
            before_each = "--mapped-stub-import-path",
        )
        args.add_all(mapped_stub.imports, before_each = "--stub-import-path")
        args.add_all(
            mapped_stub.dependency_files,
            before_each = "--mapped-stub-dependency-path",
            expand_directories = False,
        )
        args.add_all(
            mapped_stub.dependency_imports,
            before_each = "--mapped-stub-dependency-import-path",
        )
    args.use_param_file("@%s", use_always = False)
    args.set_param_file_format("multiline")
    ctx.actions.run(
        executable = config.wrapper,
        arguments = [args],
        inputs = inputs,
        outputs = [output],
        mnemonic = "PyreflyStubgen",
        progress_message = "Generating type stubs for %{label}",
        tools = [pyrefly],
        use_default_shell_env = True,
    )
    return output

def _pyrefly_stubs_impl(ctx):
    library = ctx.attr.library
    configuration = ctx.attr.configuration
    direct_original_sources = library[PyInfo].direct_original_sources
    direct_pyi_files = library[PyInfo].direct_pyi_files
    if direct_original_sources or direct_pyi_files:
        target_inputs = depset(
            transitive = [
                direct_original_sources,
                direct_pyi_files,
            ],
        )
    elif DefaultInfo in library:
        target_inputs = library[DefaultInfo].files
    else:
        fail("{} must provide DefaultInfo to generate Pyrefly stubs".format(
            library.label,
        ))

    output = create_pyrefly_stubgen_action(
        ctx,
        library,
        configuration[PyreflyConfigInfo],
        ctx.toolchains[_PYREFLY_TOOLCHAIN_TYPE].files_to_run,
        ctx.attr.log_level[BuildSettingInfo].value,
        (
            ctx.attr.library.label.repo_name == "" or
            ctx.attr._python_import_all_repositories[BuildSettingInfo].value
        ),
        configuration[PyreflyTargetEnvironmentInfo],
        target_inputs,
        include_docstrings = ctx.attr.include_docstrings,
        include_private = ctx.attr.include_private,
        output_name = ctx.label.name + "_pyrefly_stubs",
    )
    return [DefaultInfo(files = depset([output]))]

_pyrefly_stubs = rule(
    implementation = _pyrefly_stubs_impl,
    attrs = {
        "_python_import_all_repositories": attr.label(
            default = _PYTHON_IMPORT_ALL_REPOSITORIES,
            providers = [BuildSettingInfo],
        ),
        "configuration": attr.label(
            doc = "pyrefly_configuration target supplying shared policy and target-environment information.",
            mandatory = True,
            providers = [PyreflyConfigInfo, PyreflyTargetEnvironmentInfo],
        ),
        "include_docstrings": attr.bool(
            doc = "Whether generated stubs preserve docstrings.",
        ),
        "include_private": attr.bool(
            doc = "Whether generated stubs include private names.",
        ),
        "library": attr.label(
            doc = "Python library for which to generate reusable stubs.",
            mandatory = True,
            providers = [[PyInfo]],
        ),
        "log_level": attr.label(
            mandatory = True,
            providers = [BuildSettingInfo],
        ),
    },
    doc = "Generates stubs for a py_library using the configured Pyrefly executable.",
    toolchains = [_PYREFLY_TOOLCHAIN_TYPE],
)

def pyrefly_stubs(
        name,
        configuration,
        library,
        include_docstrings = False,
        include_private = False,
        **kwargs):
    """Generate reusable Pyrefly stubs for a py_library.

    Args:
        name: Name of the generated-stub target.
        configuration: pyrefly_configuration target supplying shared policy.
        library: py_library-compatible target to pass to Pyrefly stubgen.
        include_docstrings: Whether generated stubs preserve docstrings.
        include_private: Whether generated stubs include private names.
        **kwargs: Additional common rule attributes.
    """
    _pyrefly_stubs(
        name = name,
        configuration = configuration,
        include_docstrings = include_docstrings,
        include_private = include_private,
        library = library,
        log_level = _LOG_LEVEL,
        **kwargs
    )
