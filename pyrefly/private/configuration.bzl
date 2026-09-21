"""Configured Pyrefly state shared by every application of the aspect."""

load("@rules_python//python:defs.bzl", "PyInfo")
load(":otlp.bzl", "declare_otlp_trace")
load(
    ":providers.bzl",
    "PyreflyBaselinesInfo",
    "PyreflyConfigInfo",
    "PyreflyTargetEnvironmentInfo",
)

_DEFAULT_STALE_MESSAGE = (
    "Pyrefly passed for %s, but the target is listed as an expected failure. Remove the stale entry."
)
_PYTHON_TOOLCHAIN_TYPE = Label("@rules_python//python:toolchain_type")
_PYTHON_VERSION = Label(
    "@rules_python//python/config_settings:python_version",
)
_PLATFORM_MAPPINGS = {
    Label("@platforms//os:android"): "android",
    Label("@platforms//os:emscripten"): "emscripten",
    Label("@platforms//os:freebsd"): "freebsd",
    Label("@platforms//os:ios"): "ios",
    Label("@platforms//os:linux"): "linux",
    Label("@platforms//os:osx"): "darwin",
    Label("@platforms//os:wasi"): "wasi",
    Label("@platforms//os:windows"): "win32",
}

def is_type_checking_enabled(config, target_tags):
    """Whether a target's tags select it for type-checking."""
    if config.include_tags:
        return any([tag in config.include_tags for tag in target_tags])
    return not any([tag in config.exclude_tags for tag in target_tags])

_MappedStubInfo = provider(
    fields = {
        "all_files": "Direct and transitive files from a mapped stub dependency.",
        "all_imports": "Direct and transitive import roots from a mapped stub dependency.",
        "dependency_files": "Files contributed by dependencies of the mapped stub target.",
        "dependency_imports": "Import roots contributed by dependencies of the mapped stub target.",
        "direct_files": "Files belonging directly to the mapped stub target.",
    },
)

def _mapped_stub_aspect_impl(target, ctx):
    direct_files = []
    direct_imports = []
    if DefaultInfo in target:
        direct_files.append(target[DefaultInfo].files)
    if PyInfo in target:
        direct_files.append(target[PyInfo].direct_original_sources)
        direct_files.append(target[PyInfo].direct_pyi_files)
        direct_imports.append(target[PyInfo].imports)

    dependency_files = []
    dependency_imports = []
    dependencies = (
        getattr(ctx.rule.attr, "deps", []) +
        getattr(ctx.rule.attr, "pyi_deps", [])
    )
    for dependency in dependencies:
        if _MappedStubInfo in dependency:
            dependency_files.append(dependency[_MappedStubInfo].all_files)
            dependency_imports.append(dependency[_MappedStubInfo].all_imports)
    actual = getattr(ctx.rule.attr, "actual", None)
    actual_targets = actual if type(actual) == "list" else [actual] if actual != None else []
    for dependency in actual_targets:
        if _MappedStubInfo in dependency:
            dependency_files.append(dependency[_MappedStubInfo].dependency_files)
            dependency_imports.append(dependency[_MappedStubInfo].dependency_imports)

    direct_files = depset(transitive = direct_files)
    dependency_files = depset(transitive = dependency_files)
    dependency_imports = depset(transitive = dependency_imports)
    return [_MappedStubInfo(
        all_files = depset(
            transitive = [
                direct_files,
                dependency_files,
            ],
        ),
        all_imports = depset(
            transitive = direct_imports + [dependency_imports],
        ),
        dependency_files = dependency_files,
        dependency_imports = dependency_imports,
        direct_files = direct_files,
    )]

_mapped_stub_aspect = aspect(
    implementation = _mapped_stub_aspect_impl,
    attr_aspects = [
        "actual",
        "deps",
        "pyi_deps",
    ],
)

def _stubgen_selectors(targets):
    exact_labels = set()
    package_groups = []
    for target in targets:
        if PackageSpecificationInfo in target:
            package_groups.append(target[PackageSpecificationInfo])
        elif PyInfo in target:
            exact_labels.add(str(target.label))
        else:
            fail(
                "{} must provide PyInfo or PackageSpecificationInfo to select stubgen targets".format(
                    target.label,
                ),
            )
    return struct(
        exact_labels = exact_labels,
        package_groups = package_groups,
    )

def _extract_base_config(ctx, wrapper):
    config = ctx.file.config
    if not config:
        return struct(config = None, otlp_traces = depset())
    if config.basename == "pyrefly.toml":
        return struct(config = config, otlp_traces = depset())
    if config.basename != "pyproject.toml":
        fail(
            "pyrefly_configuration(config = ...) must name pyrefly.toml or " +
            "pyproject.toml, got {}".format(config.basename),
        )

    output = ctx.actions.declare_file(
        ctx.label.name + "_effective/pyrefly.toml",
    )
    args = ctx.actions.args()
    args.add("extract-config")
    args.add("--input-config")
    args.add(config)
    args.add("--output-config")
    args.add(output)
    otlp_trace = declare_otlp_trace(
        ctx,
        args,
        ctx.label.name + "_pyrefly_extract_config",
    )
    ctx.actions.run(
        executable = wrapper,
        arguments = [args],
        inputs = [config],
        outputs = [output, otlp_trace],
        mnemonic = "PyreflyExtractConfig",
        progress_message = "Extracting Pyrefly configuration from %{input}",
        use_default_shell_env = True,
    )
    return struct(config = output, otlp_traces = depset([otlp_trace]))

def _target_environment(ctx):
    toolchain = ctx.toolchains[_PYTHON_TOOLCHAIN_TYPE]
    runtime = getattr(toolchain, "py3_runtime", None)
    version_info = getattr(runtime, "interpreter_version_info", None)
    if (
        version_info != None and
        version_info.major != None and
        version_info.minor != None
    ):
        version_parts = [
            str(version_info.major),
            str(version_info.minor),
        ]
        if version_info.micro != None:
            version_parts.append(str(version_info.micro))
        python_version = ".".join(version_parts)
    else:
        python_version = ctx.attr._python_version[config_common.FeatureFlagInfo].value
        if not python_version:
            fail(
                "The active rules_python runtime does not describe its Python " +
                "version and no configured Python version is available",
            )

    for constraint_target in ctx.attr._platform_constraints:
        constraint = constraint_target[platform_common.ConstraintValueInfo]
        if ctx.target_platform_has_constraint(constraint):
            return PyreflyTargetEnvironmentInfo(
                python_platform = _PLATFORM_MAPPINGS[constraint_target.label],
                python_version = python_version,
            )

    fail(
        "Pyrefly cannot infer python-platform from the configured target " +
        "platform; supported OS constraints are {}".format(
            ", ".join([str(constraint) for constraint in _PLATFORM_MAPPINGS]),
        ),
    )

def _configuration_impl(ctx):
    if ctx.attr.include_tags and ctx.attr.exclude_tags:
        fail("pyrefly_configuration accepts either include_tags or exclude_tags, not both")
    if len(ctx.attr.stub_package_keys) != len(ctx.attr.stub_package_values):
        fail("stub_package_keys and stub_package_values must contain the same number of entries")

    wrapper = ctx.attr._wrapper[DefaultInfo].files_to_run
    extracted_config = _extract_base_config(ctx, wrapper)
    base_config = extracted_config.config

    stub_packages = {}
    for index in range(len(ctx.attr.stub_package_values)):
        package = str(ctx.attr.stub_package_keys[index].label)
        target = ctx.attr.stub_package_values[index]
        stub_files = []
        stub_import_paths = []
        if DefaultInfo in target:
            stub_files.append(target[DefaultInfo].files)
            if target[DefaultInfo].default_runfiles:
                stub_files.append(target[DefaultInfo].default_runfiles.files)
        if PyInfo in target:
            stub_files.append(target[PyInfo].transitive_sources)
            stub_import_paths.append(target[PyInfo].imports)
        mapped_stub_info = target[_MappedStubInfo]
        stub_packages[package] = struct(
            dependency_files = mapped_stub_info.dependency_files,
            dependency_imports = mapped_stub_info.dependency_imports,
            direct_files = mapped_stub_info.direct_files,
            files = depset(transitive = stub_files),
            imports = depset(transitive = stub_import_paths),
        )

    return [
        PyreflyConfigInfo(
            base_config = base_config,
            baselines = (
                ctx.attr.baselines[PyreflyBaselinesInfo].baselines if ctx.attr.baselines else {}
            ),
            exclude_tags = set(ctx.attr.exclude_tags),
            expected_failure_labels = set(ctx.attr.expected_failure_labels),
            include_tags = set(ctx.attr.include_tags),
            stale_message = ctx.attr.stale_message,
            stub_packages = stub_packages,
            stubgen_exclude = _stubgen_selectors(ctx.attr.stubgen_exclude),
            stubgen_include = _stubgen_selectors(ctx.attr.stubgen_include),
            stubgen_include_docstrings = ctx.attr.stubgen_include_docstrings,
            stubgen_include_private = ctx.attr.stubgen_include_private,
            wrapper = wrapper,
        ),
        OutputGroupInfo(pyrefly_otlp_traces = extracted_config.otlp_traces),
        _target_environment(ctx),
    ]

_pyrefly_configuration = rule(
    implementation = _configuration_impl,
    attrs = {
        "_platform_constraints": attr.label_list(
            default = _PLATFORM_MAPPINGS.keys(),
            providers = [platform_common.ConstraintValueInfo],
        ),
        "_python_version": attr.label(
            default = _PYTHON_VERSION,
            providers = [config_common.FeatureFlagInfo],
        ),
        "_wrapper": attr.label(
            cfg = "exec",
            default = Label("//pyrefly/private/wrapper:wrapper"),
            executable = True,
        ),
        "baselines": attr.label(providers = [PyreflyBaselinesInfo]),
        "config": attr.label(allow_single_file = True),
        "exclude_tags": attr.string_list(),
        "expected_failure_labels": attr.string_list(),
        "include_tags": attr.string_list(),
        "stale_message": attr.string(default = _DEFAULT_STALE_MESSAGE),
        "stub_package_keys": attr.label_list(),
        "stub_package_values": attr.label_list(
            aspects = [_mapped_stub_aspect],
        ),
        "stubgen_exclude": attr.label_list(
            providers = [[PyInfo], [PackageSpecificationInfo]],
        ),
        "stubgen_include": attr.label_list(
            providers = [[PyInfo], [PackageSpecificationInfo]],
        ),
        "stubgen_include_docstrings": attr.bool(),
        "stubgen_include_private": attr.bool(),
    },
    doc = "Precomputes the configuration consumed by the Pyrefly aspect.",
    provides = [PyreflyConfigInfo, PyreflyTargetEnvironmentInfo],
    toolchains = [_PYTHON_TOOLCHAIN_TYPE],
)

def _pyrefly_configuration_macro_impl(
        name,
        visibility,
        expected_failures,
        stub_packages,
        **kwargs):
    stub_package_keys = sorted(stub_packages.keys())
    _pyrefly_configuration(
        name = name,
        visibility = visibility,
        expected_failure_labels = [str(label) for label in expected_failures],
        stub_package_keys = [
            native.package_relative_label(label)
            for label in stub_package_keys
        ],
        stub_package_values = [
            stub_packages[label]
            for label in stub_package_keys
        ],
        **kwargs
    )

pyrefly_configuration = macro(
    implementation = _pyrefly_configuration_macro_impl,
    inherit_attrs = "common",
    attrs = {
        "baselines": attr.label(
            doc = "Optional pyrefly_baselines target containing per-target baseline files.",
            providers = [PyreflyBaselinesInfo],
        ),
        "config": attr.label(
            allow_single_file = True,
            doc = "Optional pyrefly.toml or pyproject.toml file containing Pyrefly configuration.",
        ),
        "exclude_tags": attr.string_list(
            doc = "Target tags which disable checking. Mutually exclusive with include_tags.",
        ),
        "expected_failures": attr.label_list(
            configurable = False,
            doc = "Targets whose current Pyrefly failures are allowed; a clean result fails as stale.",
        ),
        "include_tags": attr.string_list(
            doc = "Target tags which enable checking. Mutually exclusive with exclude_tags.",
        ),
        "stale_message": attr.string(
            default = _DEFAULT_STALE_MESSAGE,
            doc = "Error template emitted when an expected failure passes; each %s is replaced with its label.",
        ),
        "stub_packages": attr.string_keyed_label_dict(
            configurable = False,
            doc = "Mapping from runtime Python targets to their supplementary stub-package targets.",
        ),
        "stubgen_exclude": attr.label_list(
            doc = "Python targets and package groups excluded from automatic stubgen. Takes precedence over stubgen_include.",
            providers = [[PyInfo], [PackageSpecificationInfo]],
        ),
        "stubgen_include": attr.label_list(
            doc = "Python targets and package groups eligible for automatic stubgen.",
            providers = [[PyInfo], [PackageSpecificationInfo]],
        ),
        "stubgen_include_docstrings": attr.bool(
            doc = "Whether automatically generated stubs preserve docstrings.",
        ),
        "stubgen_include_private": attr.bool(
            doc = "Whether automatically generated stubs include private names.",
        ),
    },
    doc = "Declares the configuration consumed by Pyrefly aspects and rules.",
)
