"""Construction of filtered Python dependency actions."""

load("@rules_python//python:defs.bzl", "PyInfo")
load(":otlp.bzl", "declare_otlp_trace")

def create_pyrefly_minify_action(
        ctx,
        target,
        config,
        log_level,
        target_inputs,
        retain_repository_root,
        mapped_stub = None,
        repository_root = None):
    """Copy a target's type-relevant files into a compact TreeArtifact."""
    if mapped_stub == None:
        mapped_stub = config.stub_packages.get(str(target.label))
    inputs = depset(
        transitive = [target_inputs, mapped_stub.files] if mapped_stub else [target_inputs],
    )
    imports = target[PyInfo].imports
    output = ctx.actions.declare_directory(
        target.label.name + "_pyrefly_minified",
    )

    args = ctx.actions.args()
    args.add("minify")
    args.add("--log-level")
    args.add(log_level)
    args.add("--output-dir")
    args.add(output.path)
    args.add("--bazel-bin-dir")
    args.add(ctx.bin_dir.path)
    args.add("--input-root")
    args.add(".")
    args.add("--repository-root")
    args.add(repository_root or target.label.workspace_root or ".")
    otlp_trace = declare_otlp_trace(
        ctx,
        args,
        target.label.name + "_pyrefly_minify",
    )
    if retain_repository_root:
        args.add("--retain-repository-root")
    args.add_all(
        target_inputs,
        before_each = "--input-path",
        expand_directories = False,
    )
    args.add_all(imports, before_each = "--import-path")
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
        outputs = [output, otlp_trace],
        mnemonic = "PyreflyMinify",
        progress_message = "Minifying Python for %{label}",
        use_default_shell_env = True,
    )
    return struct(output = output, otlp_trace = otlp_trace)
