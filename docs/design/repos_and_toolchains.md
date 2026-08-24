# Workspace configuration and toolchains

The public API separates workspace-owned policy from toolchain provisioning. The module extension
creates repositories only for the Pyrefly executable and its toolchain registrations. A target and
aspect definitions in the main workspace own all analysis policy.

## Ownership model

| Owner            | Responsibility                                                                                                   |
| ---------------- | ---------------------------------------------------------------------------------------------------------------- |
| Main workspace   | `pyrefly_configuration`, normal and update aspects, baselines, tag policy, expected failures, and stub selection |
| Module extension | Version validation, custom-executable validation, platform downloads, and registered toolchain repositories      |

This keeps configuration labels in the repository mapping where they were written and makes the
aspect entry point explicit in `.bazelrc`. There is no generated configuration repository,
executable alias, or generated expected-failures export.

## Toolchain repositories

`@pyrefly.bzl//pyrefly:toolchain_type` is the stable public toolchain type. `@pyrefly_toolchain`
contains the implementations registered for it. When a release version is selected, one repository
per supported execution platform contains the corresponding binary, for example
`@pyrefly_linux_x86_64`. Toolchain resolution evaluates and fetches only the selected platform
implementation.

A caller-supplied executable creates one unconstrained implementation. In both cases, the aspect and
`pyrefly_stubs` resolve `ctx.toolchains` directly. The executable is never stored in
`PyreflyConfigInfo`.

Every repository rule reports reproducible metadata, and the extension reports reproducible
extension metadata.

## Configuration target

The symbolic `pyrefly_configuration` macro normalises loading-time inputs and calls a private rule.
The private rule provides:

- `PyreflyConfigInfo`, containing the effective config file, tag and expected-failure policy,
  deterministic mapped-stub data, stubgen selectors, wrapper executable, and optional baseline
  label-to-file mapping.
- `PyreflyTargetEnvironmentInfo`, containing the Python version and `sys.platform` value derived
  from the target configuration's rules_python toolchain and OS constraint.

Keeping both providers on one target prevents the policy and target environment from being wired to
different configured instances. A target-platform or Python-runtime transition creates the
corresponding configured instance of this single target.

`stub_packages` is a non-configurable `string_keyed_label_dict`. The macro sorts its keys and sends
parallel runtime and stub label lists to the private rule. Bazel resolves aliases before the rule
records runtime labels. `expected_failures` is also non-configurable, but its `Label` values are
converted to canonical strings by the macro rather than becoming rule dependencies. That avoids a
configuration-target cycle when policy mentions a target whose aspect uses the same configuration.

## Configuration-file extraction

A source file named `pyrefly.toml` is stored directly in `PyreflyConfigInfo`. A source file named
`pyproject.toml` registers one `PyreflyExtractConfig` action. The wrapper parses the input and
writes only `[tool.pyrefly]` to a derived output whose basename is `pyrefly.toml`.

Only the derived output is given to downstream check and stubgen actions. Changes to unrelated
project metadata therefore do not enter those actions' declared inputs. Unsupported filenames fail
during analysis. Malformed TOML and a missing `[tool.pyrefly]` table fail the extraction action.

## Aspects

The main workspace creates its normal aspect with one configuration label. The update aspect is
created from the normal aspect and the same label. Both factories reject non-`Label` configuration
arguments.

The normal aspect resolves Pyrefly through the stable toolchain type and reads both configuration
providers from its `_pyrefly_config` attribute. It publishes baseline-independent check inputs for
the update aspect. Normal builds contain no `PyreflyUpdateBaseline` action.

The update aspect reuses the normal aspect's dependency materialisation graph and registers a fresh
baseline action only when explicitly selected. `pyrefly_baselines(update_aspect = ...)` places the
workspace aspect string in `PYREFLY_UPDATE_ASPECT`; the updater forwards it to its nested
`bazel build`.

## Action inputs

Pyrefly executables are Bazel tools and use execroot-relative paths, keeping action keys independent
of an output base or sandbox path. The wrapper resolves that path after the action starts.

For a target with a baseline, `PyreflyCheck` adds only the matching JSON file from
`PyreflyConfigInfo.baselines`. The aggregate registry is not an action input. Changing one baseline
therefore changes only its target's check input digest.

`PyreflyUpdateBaseline` does not consume an existing baseline. It publishes a fresh file through
`pyrefly_updated_baseline`. The executable registry requests that output group, reads the Build
Event Protocol mapping, sanitises unstable descriptions, and creates, updates, or deletes source
baselines atomically.
