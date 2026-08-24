"""Small Python-provider fixtures for integration behavior not exposed by py_library."""

load("@rules_python//python:defs.bzl", "PyInfo")

def _generated_python_context_impl(ctx):
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

generated_python_context = rule(
    implementation = _generated_python_context_impl,
    provides = [PyInfo],
)

def _fallback_python_context_impl(ctx):
    metadata = ctx.actions.declare_file(ctx.label.name + ".txt")
    ctx.actions.write(metadata, "not a Python input\n")
    return [
        DefaultInfo(files = depset([metadata])),
        PyInfo(
            direct_original_sources = depset(),
            direct_pyi_files = depset(),
            imports = depset(),
            transitive_original_sources = depset(),
            transitive_pyi_files = depset(),
            transitive_sources = depset(),
        ),
    ]

fallback_python_context = rule(
    implementation = _fallback_python_context_impl,
    attrs = {
        "data": attr.label_list(allow_files = True),
        "srcs": attr.label_list(allow_files = [".py"]),
    },
    provides = [PyInfo],
)
