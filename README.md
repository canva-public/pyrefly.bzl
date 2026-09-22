# pyrefly.bzl

`pyrefly.bzl` provides Bazel aspects and rules for hermetic Python type checking with
[Pyrefly](https://pyrefly.org/).

This is Canva's Bazel ruleset for Pyrefly. The long-term goal is to consolidate this work with the
official [rules_pyrefly](https://github.com/facebook/rules_pyrefly) ruleset, not to maintain a
competing ruleset.

## Setup

Register the Pyrefly toolchain in a `MODULE.bazel` file:

```starlark
bazel_dep(name = "pyrefly.bzl", version = "0.2.0")

pyrefly = use_extension("@pyrefly.bzl", "pyrefly")
pyrefly.toolchain(version = "1.1.1")
use_repo(pyrefly, "pyrefly_toolchain")

register_toolchains("@pyrefly_toolchain//:all")
```

Declare the shared policy in a `BUILD` file, for example `//tools/pyrefly/BUILD`:

```starlark
load("@pyrefly.bzl", "pyrefly_configuration")

pyrefly_configuration(
    name = "config",
    # Configure Pyrefly using `pyroject.toml` or `pyrefly.toml` 
    config = "//:pyproject.toml",
    # Use tags for target-level opt-in or opt-out
    exclude_tags = ["no-pyrefly"],
    # Ratchet down on targets with existing failures
    expected_failures = ["//legacy:known_failure"],
    # Map 3rd party libraries to their supplementary stub packages
    stub_packages = {
        "@pypi//requests": "@pypi//types_requests",
    },
    # Generate stubs for imported libraries to improve type-checking performance
    stubgen_include = ["//:third_party_python_packages"],
    stubgen_exclude = ["@pypi//pydantic"],
    visibility = ["//visibility:public"],
)
```

Create the aspect in a `.bzl` file in the same workspace, for example `//tools/pyrefly:aspects.bzl`:

```starlark
load("@pyrefly.bzl", "make_pyrefly_aspect")

_CONFIGURATION = Label("//tools/pyrefly:config")

pyrefly_aspect = make_pyrefly_aspect(configuration = _CONFIGURATION)
```

Enable the validation aspect in `.bazelrc`:

```text
common --aspects=//tools/pyrefly:aspects.bzl%pyrefly_aspect
```

Type checks run as [validation actions](https://bazel.build/extending/rules#validation_actions) and
can be toggled with Bazel's
[`--run_validations` flag](https://bazel.build/reference/command-line-reference#build-flag--run_validations).

## Toolchain

To allow `pyrefly.bzl` to manage the Pyrefly toolchain, provide the version of Pyrefly to use:

```starlark
pyrefly.toolchain(version = "1.1.1")
```

To bring your own toolchain instead, provide an executable target:

```starlark
pyrefly.toolchain(toolchain = "//tools/pyrefly")
```

Exactly one `pyrefly.toolchain` tag is required. Its `version` and `toolchain` attributes are
mutually exclusive. Registered versions are downloaded from
[Pyrefly's GitHub releases](https://github.com/facebook/pyrefly/releases), with support for Linux
(musl) and macOS on x86-64 and Arm64.

## Configuration

The aspect is configured through the `pyrefly_configuration` target. It accepts:

- `config`: a `pyrefly.toml` or `pyproject.toml` file.
- `baselines`: an optional [`pyrefly_baselines`](#baselines) target.
- `include_tags` or `exclude_tags`, which are mutually exclusive.
- `expected_failures` and an optional `stale_message`.
- `stub_packages`, a runtime-target-to-stub-target dictionary.
- `stubgen_include`, `stubgen_exclude`, `stubgen_include_docstrings`, and `stubgen_include_private`
  to configure automatic stubgen.

When `config` is a `pyrefly.toml` file, the file is passed directly to check and stubgen actions.
When it is `pyproject.toml`, a `pyrefly.toml` file will be extracted from the `[tool.pyrefly]`
section, meaning action caches are not invalidated by every unrelated change to pyproject.toml.

### Tag-based enrolment

`include_tags` makes checking opt-in. `exclude_tags` makes it opt-out. With neither attribute, every
eligible first-party target is checked.

### Stub package mappings

Prebuilt stub packages can be associated with a runtime package:

```starlark
pyrefly_configuration(
    name = "config",
    ...
    stub_packages = {
        "@pypi//requests": "@pypi//types_requests",
    },
    ...
)
```

Mapped stubs are included only when the runtime package occurs in a target's dependency closure.
[Partial stub packages](https://peps.python.org/pep-0561/#partial-stub-packages) are combined with
generated or minified runtime interfaces for modules they do not cover.

### Stub generation

Pyrefly normally infers types from dependency implementations while type-checking the sources in
your target. Running `pyrefly stubgen` on those dependencies beforehand effectively precomputes and
caches that inference process. This results in substantially faster type-checking.

Enable the aspect's automatic stub generation in the `pyrefly_configuration` target:

```starlark
pyrefly_configuration(
    name = "config",
    ...
    stubgen_include = [":third_party_python_packages"],
    stubgen_exclude = [  # takes precedence over `stubgen_include`
        "@pypi//pydantic",
        "//internal/dynamic_package",
    ],
    stubgen_include_docstrings = True,  # Optional, defaults to False
    stubgen_include_private = True,  # Optional, defaults to False
    ...
)
```

`stubgen_include` and `stubgen_exclude` accept Python targets and native `package_group` targets.
Define a package group when stubgen should cover a package tree:

```starlark
package_group(
    name = "third_party_python_packages",
    packages = ["@pypi//..."],
)
```

In some cases, stubgen can lose information that was available in the original source, causing false
positives in downstream type-checks. Use `stubgen_exclude` to exclude affected packages and retain
their original Python sources instead.

### Baselines

[Baseline files](https://pyrefly.org/en/docs/error-suppressions/#baseline-files-experimental) can be
used to help introduce type checking to a project for the first time. In `pyrefly.bzl`, baseline
files are per-target and must be kept in a central baselines folder. Each file mirrors the label of
a Python target. For example, assuming you locate your baselines folder at
`third_party/pyrefly.bzl/baselines`, then
`third_party/pyrefly.bzl/baselines/application/data_access/library.json` supplies the baseline for
`//application/data_access:library`.

Define one public aggregate target in your baselines folder, e.g. in
`//tools/pyrefly/baselines/BUILD`:

```starlark
load("@pyrefly.bzl", "pyrefly_baselines")

pyrefly_baselines(
    name = "baselines",
    srcs = glob(["**/*.json"], allow_empty = True),
    update_aspect = "//tools/pyrefly:aspects.bzl%pyrefly_update_baseline_aspect",
    visibility = ["//visibility:public"],
)
```

The `pyrefly_update_baseline_aspect` should be declared alongside the validation aspect, e.g. in
`//tools/pyrefly:aspects.bzl`:

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

Then associate the baseline target with the Pyrefly configuration target:

```starlark
pyrefly_configuration(
    name = "config",
    ...
    baselines = "//tools/pyrefly/baselines",
    ...
)
```

Targets without a matching file run without a baseline.

Create, refresh, or clean up baselines by running the baselines target with one or more Bazel target
patterns:

```shell
bazel run //tools/pyrefly/baselines -- \
  //application/data_access/... \
  //other/package:library
```

If a target has no errors, its existing baseline is removed.

Arguments after `--` must be target patterns or the target-pattern file option described below;
other Bazel options are not supported. The updater invokes a nested `bazel build`, using the
executable named by the `BAZEL` environment variable when set and `bazel` otherwise.

For a long target list, supply one pattern per line through Bazel's target-pattern file interface:

```shell
bazel run //tools/pyrefly/baselines -- \
  --target_pattern_file=pyrefly-targets.txt
```

As with Bazel itself, `--target_pattern_file` cannot be combined with positional target patterns.

### Expected failures

If Pyrefly type-checking is being rolled out gradually in a large repository, it can be useful to
establish a ratcheting system. This would be considered an alternative to using baseline files for
all targets.

`pyrefly.bzl` allows you to specify a self-ratcheting list of targets which are expected to fail
Pyrefly type-checking:

```starlark
pyrefly_configuration(
    name = "config",
    ...
    expected_failures = ["//legacy:known_failure"],
    stale_message = "Remove %s from expected_failures in //tools/pyrefly:config",
    ...
)
```

Type-checking will still run on these targets, however the results will be effectively inverted:

- If the target fails type-checking as expected, the action will exit zero and record its findings
  as warnings. The warnings will only be displayed in Bazel's output if the `pyrefly_warnings`
  output group is requested - to prevent bloating your CI logs, you may wish to request this only
  when developing locally.
- If the target passes type-checking, the action will exit non-zero with an error message
  instructing the user to remove the target from the expected failure list.

You may specify a custom `stale_message` to be printed when an expected failure passes
type-checking. `%s` will be replaced with the passing target's label.

## OpenTelemetry traces

Each wrapper operation writes its OpenTelemetry spans as OTLP/JSON Lines. Request the trace files
for wrapper actions created directly for a target through the `pyrefly_otlp_traces` output group:

```shell
bazel build --output_groups=+pyrefly_otlp_traces //path/to:target
```

## Future improvements

- Expose Pyrefly results through Bazel output groups in machine-readable formats such as JSON,
  [SARIF](https://github.com/facebook/pyrefly/issues/4205), and JUnit XML. Supporting multiple
  formats from a single check action may depend on
  [Pyrefly support for multiple simultaneous outputs](https://github.com/facebook/pyrefly/issues/4375).
- Add aspect-integrated support for `pyrefly suppress`, `pyrefly infer`, and
  `pyrefly suppress --remove-unused`, emitting generated patch files through an output group.

## Further reading

### API reference

- [Module extension and toolchain](docs/api/extension.md)
- [Rules and macros](docs/api/rules.md)
- [Aspects](docs/api/aspects.md)

### Design documentation

- [Workspace configuration and toolchains](docs/design/repos_and_toolchains.md)
- [Wrapper design](docs/design/wrapper.md)
- [v0.1 design specification](docs/design/spec-v0.1.md)

## Limitations

- Windows is not supported.
