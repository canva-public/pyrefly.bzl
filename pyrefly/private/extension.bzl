"""Bzlmod extension that provisions the Pyrefly toolchain."""

load(":versions.bzl", "PYREFLY_PLATFORMS", "PYREFLY_RELEASES", "get_pyrefly_release")

def _custom_toolchain_build(toolchain):
    return """\
pyrefly_toolchain(
    name = "custom_implementation",
    executable = {toolchain},
)

toolchain(
    name = "custom",
    toolchain = ":custom_implementation",
    toolchain_type = "@pyrefly.bzl//pyrefly:toolchain_type",
)
""".format(toolchain = repr(str(toolchain)))

def _downloaded_toolchain_build():
    definitions = []
    for platform_name in sorted(PYREFLY_PLATFORMS.keys()):
        platform = PYREFLY_PLATFORMS[platform_name]
        definitions.append("""\
pyrefly_toolchain(
    name = {implementation_name},
    executable = {executable},
)

toolchain(
    name = {name},
    exec_compatible_with = {constraints},
    toolchain = {implementation},
    toolchain_type = "@pyrefly.bzl//pyrefly:toolchain_type",
)
""".format(
            constraints = repr(platform.constraints),
            executable = repr("@pyrefly_{}//:pyrefly".format(platform_name)),
            implementation = repr(":" + platform_name + "_implementation"),
            implementation_name = repr(platform_name + "_implementation"),
            name = repr(platform_name),
        ))
    return "\n".join(definitions)

def _pyrefly_toolchain_repository_impl(ctx):
    toolchain_definition = (
        _custom_toolchain_build(ctx.attr.toolchain) if ctx.attr.toolchain else _downloaded_toolchain_build()
    )
    ctx.file("BUILD.bazel", """\
load("@pyrefly.bzl//pyrefly/private:toolchain.bzl", "pyrefly_toolchain")

package(default_visibility = ["//visibility:public"])

{toolchain_definition}
""".format(toolchain_definition = toolchain_definition))
    return ctx.repo_metadata(reproducible = True)

_pyrefly_toolchain_repository = repository_rule(
    implementation = _pyrefly_toolchain_repository_impl,
    attrs = {
        "toolchain": attr.label(),
    },
)

def _pyrefly_platform_repository_impl(ctx):
    release = get_pyrefly_release(ctx.attr.version, ctx.attr.platform)
    ctx.download_and_extract(
        url = release.url,
        sha256 = release.digest,
    )
    if not ctx.path("pyrefly").exists:
        fail("{} does not contain a pyrefly executable".format(release.url))
    ctx.file("BUILD.bazel", """\
package(default_visibility = ["//visibility:public"])

exports_files(["pyrefly"])
""")
    return ctx.repo_metadata(reproducible = True)

_pyrefly_platform_repository = repository_rule(
    implementation = _pyrefly_platform_repository_impl,
    attrs = {
        "platform": attr.string(mandatory = True),
        "version": attr.string(mandatory = True),
    },
)

def _extension_impl(module_ctx):
    toolchain_configurations = []
    for module in module_ctx.modules:
        for toolchain_configuration in module.tags.toolchain:
            if not module.is_root:
                fail(
                    "pyrefly.toolchain may only be used by the root module; " +
                    "found one in module {}".format(module.name),
                )
            toolchain_configurations.append(toolchain_configuration)

    if len(toolchain_configurations) != 1:
        fail("The root module must contain exactly one pyrefly.toolchain tag, found {}".format(
            len(toolchain_configurations),
        ))

    toolchain_configuration = toolchain_configurations[0]
    if toolchain_configuration.toolchain and toolchain_configuration.version:
        fail("pyrefly.toolchain accepts either toolchain or version, not both")
    if not toolchain_configuration.toolchain and not toolchain_configuration.version:
        fail("pyrefly.toolchain requires either toolchain or version")
    if (
        toolchain_configuration.version and
        toolchain_configuration.version not in PYREFLY_RELEASES
    ):
        fail("Unsupported Pyrefly version {}; available versions: {}".format(
            repr(toolchain_configuration.version),
            ", ".join(PYREFLY_RELEASES.keys()),
        ))

    if toolchain_configuration.toolchain:
        _pyrefly_toolchain_repository(
            name = "pyrefly_toolchain",
            toolchain = toolchain_configuration.toolchain,
        )
    else:
        version = toolchain_configuration.version
        for platform_name in PYREFLY_PLATFORMS:
            _pyrefly_platform_repository(
                name = "pyrefly_" + platform_name,
                platform = platform_name,
                version = version,
            )
        _pyrefly_toolchain_repository(name = "pyrefly_toolchain")

    return module_ctx.extension_metadata(reproducible = True)

pyrefly = module_extension(
    doc = "Provisions a downloadable or custom Pyrefly toolchain for the root module.",
    implementation = _extension_impl,
    tag_classes = {
        "toolchain": tag_class(
            attrs = {
                "toolchain": attr.label(
                    doc = "Executable target to register as a custom Pyrefly toolchain.",
                ),
                "version": attr.string(
                    doc = "Pyrefly release version to download from the ruleset registry.",
                ),
            },
            doc = "Selects exactly one downloadable version or custom executable for Pyrefly.",
        ),
    },
)
