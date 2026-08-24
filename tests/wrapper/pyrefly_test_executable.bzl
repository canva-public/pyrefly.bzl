"""Test-only access to the registered Pyrefly toolchain executable."""

_TOOLCHAIN_TYPE = Label("@pyrefly.bzl//pyrefly:toolchain_type")

def _pyrefly_test_executable_impl(ctx):
    toolchain = ctx.toolchains[_TOOLCHAIN_TYPE]
    ctx.actions.symlink(
        output = ctx.outputs.executable,
        target_file = toolchain.files_to_run.executable,
        is_executable = True,
    )
    return [DefaultInfo(
        executable = ctx.outputs.executable,
        runfiles = ctx.runfiles().merge(toolchain.default_runfiles),
    )]

pyrefly_test_executable = rule(
    implementation = _pyrefly_test_executable_impl,
    executable = True,
    toolchains = [_TOOLCHAIN_TYPE],
)
