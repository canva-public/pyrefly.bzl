# pyrefly.bzl v0.1 design specification

## Overview

`pyrefly.bzl` provides hermetic Pyrefly checks for Bazel Python targets through:

- a toolchain-only Bzlmod extension;
- a workspace-owned configuration target;
- workspace-owned normal and baseline-update aspects;
- expected-failure and per-target baseline ratchets;
- mapped third-party stub packages;
- automatic stub generation and dependency minification; and
- explicit stub generation for a `py_library`.

The execution model wraps `pyrefly check --config` and `pyrefly stubgen`. Integration with
`pyrefly bazel-check` is outside v0.1 scope.

## Public interface

The root module selects and registers exactly one Pyrefly toolchain:

```starlark
pyrefly = use_extension("@pyrefly.bzl", "pyrefly")
pyrefly.toolchain(version = "1.1.1")
use_repo(pyrefly, "pyrefly_toolchain")
register_toolchains("@pyrefly_toolchain//:all")
```

The workspace declares policy in a BUILD file:

```starlark
load("@pyrefly.bzl", "pyrefly_configuration")

pyrefly_configuration(
    name = "config",
    baselines = "//tools/pyrefly/baselines",
    config = "//:pyproject.toml",
    exclude_tags = ["no-pyrefly"],
    expected_failures = ["//legacy:known_failure"],
    stub_packages = {
        "@pypi//requests": "@pypi//types_requests",
    },
    stubgen_include = ["//:third_party_python_packages"],
    stubgen_exclude = ["@pypi//pydantic"],
    visibility = ["//visibility:public"],
)
```

It creates and exports aspects from a local `.bzl` file:

```starlark
load(
    "@pyrefly.bzl",
    "make_pyrefly_aspect",
    "make_pyrefly_update_baseline_aspect",
)

_CONFIGURATION = Label("//tools/pyrefly:config")
pyrefly_aspect = make_pyrefly_aspect(configuration = _CONFIGURATION)
pyrefly_update_baseline_aspect = make_pyrefly_update_baseline_aspect(
    pyrefly_aspect = pyrefly_aspect,
    configuration = _CONFIGURATION,
)
```

The normal aspect is enabled with:

```text
common --aspects=//tools/pyrefly:aspects.bzl%pyrefly_aspect
```

`pyrefly_stubs` requires the same configuration explicitly:

```starlark
load("@pyrefly.bzl", "pyrefly_stubs")

pyrefly_stubs(
    name = "client_stubs",
    configuration = "//tools/pyrefly:config",
    library = ":client",
)
```

## Module extension

The extension accepts only `pyrefly.toolchain`. Exactly one tag belongs to the root module, and it
sets exactly one of:

- `version`, selected from the checked-in release registry; or
- `toolchain`, a caller-supplied executable target.

Registered downloads cover Linux and macOS on x86-64 and Arm64. Linux uses static musl artifacts.
The extension creates `@pyrefly_toolchain` and, for downloads, separate platform repositories. There
is no generated policy repository or runnable executable proxy.

## Configuration macro and providers

`pyrefly_configuration` is a symbolic macro with these public attributes:

- `config`, `baselines`, `include_tags`, and `exclude_tags`;
- `expected_failures` and `stale_message`;
- `stub_packages`; and
- `stubgen_include`, `stubgen_exclude`, `stubgen_include_docstrings`, and `stubgen_include_private`.

`include_tags` and `exclude_tags` are mutually exclusive. With neither, all eligible targets are
checked. Stubgen exact selectors provide `PyInfo`; package-wide selectors provide
`PackageSpecificationInfo`. Exclusions take precedence.

`stub_packages` is a non-configurable `string_keyed_label_dict`. The macro sorts runtime-label keys
and forwards parallel label lists. The private rule resolves aliases and constructs the mapped-stub
data. `expected_failures` is a non-configurable label list whose values become canonical strings, so
mentioned targets are not dependencies of the configuration target.

The private rule returns both `PyreflyConfigInfo` and `PyreflyTargetEnvironmentInfo`.
`PyreflyConfigInfo` contains policy, mapped-stub data, resolved stubgen selectors, the optional
baseline mapping, effective config file, and wrapper executable. `PyreflyTargetEnvironmentInfo`
contains the target Python version and platform.

Python version comes from the selected target runtime's interpreter metadata, falling back to
rules_python's configured version. Python platform comes from the target OS constraint and maps to
Pyrefly's `sys.platform` names for Android, Emscripten, FreeBSD, iOS, Linux, macOS, Windows, and
WASI.

## Configuration files

Only `pyrefly.toml` and `pyproject.toml` basenames are accepted. `pyrefly.toml` is passed directly.
For `pyproject.toml`, the configuration rule registers one `PyreflyExtractConfig` action that writes
only `[tool.pyrefly]` to a derived `pyrefly.toml`. Downstream actions receive only that output.

Unsupported filenames fail analysis. Malformed TOML and a missing `[tool.pyrefly]` table fail the
extraction action with an explicit wrapper diagnostic.

## Aspect model

The normal aspect applies to targets providing `PyInfo` and traverses `deps` and `pyi_deps`. It
reads both shared providers from the configured target and resolves Pyrefly from
`@pyrefly.bzl//pyrefly:toolchain_type`.

Main-repository targets with direct `.py`, `.pyi`, or `.ipynb` sources register `PyreflyCheck`
validation actions when selected by tag policy. External and unselected targets still contribute a
canonical dependency representation through stubgen or minification. Validation outputs propagate
through Bazel's `_validation` output group.

The aspect publishes baseline-independent `PyreflyCheckInputsInfo`. The update aspect requires that
provider, reuses the normal aspect's dependency graph, and emits a direct `pyrefly_updated_baseline`
output without running normal validations.

## Stub selection

For each dependency target:

1. A target matching `stubgen_include` and no `stubgen_exclude` selector registers one
   `PyreflyStubgen` action.
2. Every other target registers one `PyreflyMinify` action containing only type-relevant files.

A matching `stub_packages` entry overlays mapped `.pyi` files. A complete stub package replaces
runtime interfaces; a PEP 561 partial package is combined with generated or minified files for
uncovered modules. Downstream actions consume only canonical replacement artifacts, not original
dependency file sets.

The explicit `pyrefly_stubs` rule uses the registered toolchain and its required configuration
target. Its `include_private` and `include_docstrings` options default to false, matching Pyrefly.

## Checks and expected failures

The check wrapper creates a temporary effective `pyrefly.toml`, preserving consumer policy while
replacing Bazel-owned source, search-path, site-package, interpreter, and heuristic settings. It
then runs `pyrefly check --config`.

| Pyrefly result                  | Expected failure | Action result                              |
| ------------------------------- | ---------------- | ------------------------------------------ |
| Clean                           | No               | Success                                    |
| Type errors                     | No               | Failure                                    |
| Type errors                     | Yes              | Success with warning output                |
| Clean                           | Yes              | Failure because the ratchet entry is stale |
| Infrastructure error or timeout | Either           | Failure                                    |

Each `%s` in `stale_message` is replaced with the canonical target label. Expected failures are
available only through the configuration provider; there is no generated Starlark export.

## Baselines

`pyrefly_baselines` maps checked-in JSON paths to target labels and carries a required local update
aspect string. A configuration target stores its label-to-file mapping in `PyreflyConfigInfo`.
Normal check actions declare only the matching file.

The registry is executable. Its run environment supplies `PYREFLY_UPDATE_ASPECT`, and the updater
uses that value for the nested Bazel build. Fresh update actions do not consume existing baseline
files. The updater reads output-to-label associations from the Build Event Protocol before copying
non-empty outputs verbatim or removing source files for empty outputs.

## Hermetic execution

The execution platform selects the Pyrefly executable, while the configuration target models the
Python target platform and runtime. These are intentionally independent so local and remote
execution cannot change type-checking semantics.

Pyrefly is passed to actions as a Bazel tool using an execroot-relative path. The wrapper resolves
that path after the spawn starts. Long argument lists use Bazel parameter files.

The wrapper's `check`, `minify`, `stubgen`, `update-baseline`, `display-warnings`, and
`extract-config` subcommands report infrastructure failures consistently. More detail is in
[`wrapper.md`](wrapper.md).

## Compatibility and verification

- The v0.1 ruleset targets Bazel 9 and rules_python 2.0.0.
- The wrapper requires Python 3.11 or newer.
- Downloaded releases are pinned by asset name and SHA-256.
- Wrapper tests cover command behaviour, analysis tests cover providers and actions, and integration
  workspaces cover complete builds with real Pyrefly execution.
