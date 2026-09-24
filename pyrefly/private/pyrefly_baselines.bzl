"""Per-target Pyrefly baseline registry."""

load(":providers.bzl", "PyreflyBaselinesInfo")

def _target_label(repository_name, relative_path):
    target_path = relative_path[:-len(".json")]
    separator = target_path.rfind("/")
    if separator == -1:
        package = ""
        name = target_path
    else:
        package = target_path[:separator]
        name = target_path[separator + 1:]
    if not name:
        fail("Pyrefly baseline paths must end in <target-name>.json")
    return Label("@@{}//{}:{}".format(repository_name, package, name))

def _pyrefly_baselines_impl(ctx):
    baselines = {}
    for file in ctx.files.srcs:
        if not file.is_source:
            fail("{} must be a source JSON file".format(file.path))
        if (
            file.owner.repo_name != ctx.label.repo_name or
            file.owner.package != ctx.label.package
        ):
            fail("{} must be beneath the Pyrefly baselines package {}".format(
                file.owner,
                ctx.label.package,
            ))
        target_label = _target_label(ctx.label.repo_name, file.owner.name)
        if target_label in baselines:
            fail("More than one Pyrefly baseline maps to {}".format(target_label))
        baselines[target_label] = file

    executable = ctx.actions.declare_file(ctx.label.name + "_updater")
    ctx.actions.symlink(
        output = executable,
        target_file = ctx.executable._updater,
        is_executable = True,
    )
    updater_info = ctx.attr._updater[DefaultInfo]
    runfiles = ctx.runfiles().merge(updater_info.default_runfiles)

    return [
        DefaultInfo(
            executable = executable,
            files = depset(ctx.files.srcs),
            runfiles = runfiles,
        ),
        PyreflyBaselinesInfo(baselines = baselines),
        RunEnvironmentInfo(
            environment = {
                "PYREFLY_BASELINES_PACKAGE": ctx.label.package,
            },
            inherited_environment = ["BAZEL"],
        ),
    ]

pyrefly_baselines = rule(
    implementation = _pyrefly_baselines_impl,
    attrs = {
        "srcs": attr.label_list(
            allow_files = [".json"],
            doc = "Source JSON baseline files whose package-relative paths mirror checked target labels.",
        ),
        "_updater": attr.label(
            default = Label("//pyrefly/private/baseline_updater"),
            cfg = "exec",
            executable = True,
        ),
    },
    doc = "Collects per-target Pyrefly baseline JSON files.",
    executable = True,
    provides = [PyreflyBaselinesInfo],
)
