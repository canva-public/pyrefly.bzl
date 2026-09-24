"""Integration-test helpers for executing configured Pyrefly actions."""

load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@pyrefly.bzl//pyrefly/private:providers.bzl", "PyreflyInfo")

def _pyrefly_check_inputs_impl(ctx):
    sources = ctx.attr.target[PyreflyInfo].sources
    return [DefaultInfo(
        files = sources,
        runfiles = ctx.runfiles(transitive_files = sources),
    )]

def _pyrefly_check_validation_impl(ctx):
    validation = depset()
    target = ctx.attr.target
    if OutputGroupInfo in target and hasattr(target[OutputGroupInfo], "_validation"):
        validation = target[OutputGroupInfo]._validation
    return [DefaultInfo(files = validation)]

def make_pyrefly_check_rules(pyrefly_aspect):
    """Construct integration-test rules bound to a project-local aspect."""
    target_attr = attr.label(
        aspects = [pyrefly_aspect],
        mandatory = True,
    )
    return struct(
        inputs = rule(
            implementation = _pyrefly_check_inputs_impl,
            attrs = {
                "pyrefly_mode": attr.string(default = "check"),
                "target": target_attr,
            },
            doc = "Exposes the PyreflyInfo sources used to check a target.",
        ),
        validation = rule(
            implementation = _pyrefly_check_validation_impl,
            attrs = {
                "pyrefly_mode": attr.string(default = "check"),
                "target": target_attr,
            },
        ),
    )

def pyrefly_check_test(validation_rule, name, target, **kwargs):
    """Tests a target's Pyrefly validation outputs with build_test."""
    validation_name = name + "_validation"
    validation_rule(
        name = validation_name,
        target = target,
        tags = ["manual"],
        testonly = True,
        visibility = ["//visibility:private"],
    )
    build_test(
        name = name,
        targets = [":" + validation_name],
        **kwargs
    )
