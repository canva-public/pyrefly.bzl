"""Pyrefly toolchain implementation rule."""

def _pyrefly_toolchain_impl(ctx):
    files_to_run = ctx.attr.executable[DefaultInfo].files_to_run
    if not files_to_run.executable:
        fail("{} must provide an executable".format(ctx.attr.executable.label))
    return [
        platform_common.ToolchainInfo(
            default_runfiles = ctx.attr.executable[DefaultInfo].default_runfiles,
            files_to_run = files_to_run,
        ),
    ]

pyrefly_toolchain = rule(
    implementation = _pyrefly_toolchain_impl,
    attrs = {
        "executable": attr.label(
            allow_files = True,
            cfg = "exec",
            executable = True,
            mandatory = True,
        ),
    },
)
