"""Generate overlapping Python import roots for the materialisation benchmark."""

load("@rules_python//python:defs.bzl", "PyInfo")

def _generated_import_roots_impl(ctx):
    if ctx.attr.roots < 1:
        fail("must be at least 1", attr = "roots")
    if ctx.attr.files_per_root < 1:
        fail("must be at least 1", attr = "files_per_root")

    output = ctx.actions.declare_directory(ctx.label.name)
    args = ctx.actions.args()
    args.add("--output-dir", output.path)
    args.add("--roots", ctx.attr.roots)
    args.add("--files-per-root", ctx.attr.files_per_root)
    ctx.actions.run(
        executable = ctx.attr._generator[DefaultInfo].files_to_run,
        arguments = [args],
        outputs = [output],
        mnemonic = "GenerateBenchmarkImportRoots",
        progress_message = "Generating overlapping import roots for %{label}",
    )
    sources = depset([output])
    imports = depset([
        "{}/{}/root_{}".format(ctx.workspace_name, output.short_path, index)
        for index in range(ctx.attr.roots)
    ])
    return [
        DefaultInfo(files = sources),
        PyInfo(
            direct_original_sources = sources,
            imports = imports,
            transitive_original_sources = sources,
            transitive_sources = sources,
        ),
    ]

generated_import_roots = rule(
    implementation = _generated_import_roots_impl,
    attrs = {
        "files_per_root": attr.int(
            default = 40,
            doc = "Number of distinct stub modules in each import root.",
        ),
        "roots": attr.int(
            default = 1000,
            doc = "Number of import roots sharing the same package hierarchy.",
        ),
        "_generator": attr.label(
            default = Label(":generator"),
            executable = True,
            cfg = "exec",
        ),
    },
    provides = [PyInfo],
)
