<!-- Generated with Stardoc: http://skydoc.bazel.build -->

Public API for pyrefly.bzl.

<a id="pyrefly_configuration"></a>

## pyrefly_configuration

<pre>
load("@pyrefly.bzl", "pyrefly_configuration")

pyrefly_configuration(*, <a href="#pyrefly_configuration-name">name</a>, <a href="#pyrefly_configuration-aspect_hints">aspect_hints</a>, <a href="#pyrefly_configuration-baselines">baselines</a>, <a href="#pyrefly_configuration-compatible_with">compatible_with</a>, <a href="#pyrefly_configuration-config">config</a>, <a href="#pyrefly_configuration-deprecation">deprecation</a>,
                      <a href="#pyrefly_configuration-exclude_tags">exclude_tags</a>, <a href="#pyrefly_configuration-exec_compatible_with">exec_compatible_with</a>, <a href="#pyrefly_configuration-exec_group_compatible_with">exec_group_compatible_with</a>, <a href="#pyrefly_configuration-exec_properties">exec_properties</a>,
                      <a href="#pyrefly_configuration-expected_failures">expected_failures</a>, <a href="#pyrefly_configuration-features">features</a>, <a href="#pyrefly_configuration-include_tags">include_tags</a>, <a href="#pyrefly_configuration-package_metadata">package_metadata</a>, <a href="#pyrefly_configuration-restricted_to">restricted_to</a>,
                      <a href="#pyrefly_configuration-stale_message">stale_message</a>, <a href="#pyrefly_configuration-stub_packages">stub_packages</a>, <a href="#pyrefly_configuration-stubgen_exclude">stubgen_exclude</a>, <a href="#pyrefly_configuration-stubgen_include">stubgen_include</a>,
                      <a href="#pyrefly_configuration-stubgen_include_docstrings">stubgen_include_docstrings</a>, <a href="#pyrefly_configuration-stubgen_include_private">stubgen_include_private</a>, <a href="#pyrefly_configuration-tags">tags</a>,
                      <a href="#pyrefly_configuration-target_compatible_with">target_compatible_with</a>, <a href="#pyrefly_configuration-testonly">testonly</a>, <a href="#pyrefly_configuration-toolchains">toolchains</a>, <a href="#pyrefly_configuration-visibility">visibility</a>)
</pre>

Declares the configuration consumed by Pyrefly aspects and rules.

**ATTRIBUTES**


| Name  | Description | Type | Mandatory | Default |
| :------------- | :------------- | :------------- | :------------- | :------------- |
| <a id="pyrefly_configuration-name"></a>name |  A unique name for this macro instance. Normally, this is also the name for the macro's main or only target. The names of any other targets that this macro might create will be this name with a string suffix.   | <a href="https://bazel.build/concepts/labels#target-names">Name</a> | required |  |
| <a id="pyrefly_configuration-aspect_hints"></a>aspect_hints |  <a href="https://bazel.build/reference/be/common-definitions#common.aspect_hints">Inherited rule attribute</a>   | <a href="https://bazel.build/concepts/labels">List of labels</a> | optional |  `None`  |
| <a id="pyrefly_configuration-baselines"></a>baselines |  Optional pyrefly_baselines target containing per-target baseline files.   | <a href="https://bazel.build/concepts/labels">Label</a> | optional |  `None`  |
| <a id="pyrefly_configuration-compatible_with"></a>compatible_with |  <a href="https://bazel.build/reference/be/common-definitions#common.compatible_with">Inherited rule attribute</a>   | <a href="https://bazel.build/concepts/labels">List of labels</a>; <a href="https://bazel.build/reference/be/common-definitions#configurable-attributes">nonconfigurable</a> | optional |  `None`  |
| <a id="pyrefly_configuration-config"></a>config |  Optional pyrefly.toml or pyproject.toml file containing Pyrefly configuration.   | <a href="https://bazel.build/concepts/labels">Label</a> | optional |  `None`  |
| <a id="pyrefly_configuration-deprecation"></a>deprecation |  <a href="https://bazel.build/reference/be/common-definitions#common.deprecation">Inherited rule attribute</a>   | String; <a href="https://bazel.build/reference/be/common-definitions#configurable-attributes">nonconfigurable</a> | optional |  `None`  |
| <a id="pyrefly_configuration-exclude_tags"></a>exclude_tags |  Target tags which disable checking. Mutually exclusive with include_tags.   | List of strings | optional |  `[]`  |
| <a id="pyrefly_configuration-exec_compatible_with"></a>exec_compatible_with |  <a href="https://bazel.build/reference/be/common-definitions#common.exec_compatible_with">Inherited rule attribute</a>   | <a href="https://bazel.build/concepts/labels">List of labels</a>; <a href="https://bazel.build/reference/be/common-definitions#configurable-attributes">nonconfigurable</a> | optional |  `None`  |
| <a id="pyrefly_configuration-exec_group_compatible_with"></a>exec_group_compatible_with |  <a href="https://bazel.build/reference/be/common-definitions#common.exec_group_compatible_with">Inherited rule attribute</a>   | Dictionary: String -> List of labels; <a href="https://bazel.build/reference/be/common-definitions#configurable-attributes">nonconfigurable</a> | optional |  `None`  |
| <a id="pyrefly_configuration-exec_properties"></a>exec_properties |  <a href="https://bazel.build/reference/be/common-definitions#common.exec_properties">Inherited rule attribute</a>   | <a href="https://bazel.build/rules/lib/core/dict">Dictionary: String -> String</a> | optional |  `None`  |
| <a id="pyrefly_configuration-expected_failures"></a>expected_failures |  Targets whose current Pyrefly failures are allowed; a clean result fails as stale.   | <a href="https://bazel.build/concepts/labels">List of labels</a>; <a href="https://bazel.build/reference/be/common-definitions#configurable-attributes">nonconfigurable</a> | optional |  `[]`  |
| <a id="pyrefly_configuration-features"></a>features |  <a href="https://bazel.build/reference/be/common-definitions#common.features">Inherited rule attribute</a>   | List of strings | optional |  `None`  |
| <a id="pyrefly_configuration-include_tags"></a>include_tags |  Target tags which enable checking. Mutually exclusive with exclude_tags.   | List of strings | optional |  `[]`  |
| <a id="pyrefly_configuration-package_metadata"></a>package_metadata |  <a href="https://bazel.build/reference/be/common-definitions#common.package_metadata">Inherited rule attribute</a>   | <a href="https://bazel.build/concepts/labels">List of labels</a>; <a href="https://bazel.build/reference/be/common-definitions#configurable-attributes">nonconfigurable</a> | optional |  `None`  |
| <a id="pyrefly_configuration-restricted_to"></a>restricted_to |  <a href="https://bazel.build/reference/be/common-definitions#common.restricted_to">Inherited rule attribute</a>   | <a href="https://bazel.build/concepts/labels">List of labels</a>; <a href="https://bazel.build/reference/be/common-definitions#configurable-attributes">nonconfigurable</a> | optional |  `None`  |
| <a id="pyrefly_configuration-stale_message"></a>stale_message |  Error template emitted when an expected failure passes; each %s is replaced with its label.   | String | optional |  `"Pyrefly passed for %s, but the target is listed as an expected failure. Remove the stale entry."`  |
| <a id="pyrefly_configuration-stub_packages"></a>stub_packages |  Mapping from runtime Python targets to their supplementary stub-package targets.   | Dictionary: String -> Label; <a href="https://bazel.build/reference/be/common-definitions#configurable-attributes">nonconfigurable</a> | optional |  `{}`  |
| <a id="pyrefly_configuration-stubgen_exclude"></a>stubgen_exclude |  Python targets and package groups excluded from automatic stubgen. Takes precedence over stubgen_include.   | <a href="https://bazel.build/concepts/labels">List of labels</a> | optional |  `[]`  |
| <a id="pyrefly_configuration-stubgen_include"></a>stubgen_include |  Python targets and package groups eligible for automatic stubgen.   | <a href="https://bazel.build/concepts/labels">List of labels</a> | optional |  `[]`  |
| <a id="pyrefly_configuration-stubgen_include_docstrings"></a>stubgen_include_docstrings |  Whether automatically generated stubs preserve docstrings.   | Boolean | optional |  `False`  |
| <a id="pyrefly_configuration-stubgen_include_private"></a>stubgen_include_private |  Whether automatically generated stubs include private names.   | Boolean | optional |  `False`  |
| <a id="pyrefly_configuration-tags"></a>tags |  <a href="https://bazel.build/reference/be/common-definitions#common.tags">Inherited rule attribute</a>   | List of strings; <a href="https://bazel.build/reference/be/common-definitions#configurable-attributes">nonconfigurable</a> | optional |  `None`  |
| <a id="pyrefly_configuration-target_compatible_with"></a>target_compatible_with |  <a href="https://bazel.build/reference/be/common-definitions#common.target_compatible_with">Inherited rule attribute</a>   | <a href="https://bazel.build/concepts/labels">List of labels</a> | optional |  `None`  |
| <a id="pyrefly_configuration-testonly"></a>testonly |  <a href="https://bazel.build/reference/be/common-definitions#common.testonly">Inherited rule attribute</a>   | Boolean; <a href="https://bazel.build/reference/be/common-definitions#configurable-attributes">nonconfigurable</a> | optional |  `None`  |
| <a id="pyrefly_configuration-toolchains"></a>toolchains |  <a href="https://bazel.build/reference/be/common-definitions#common.toolchains">Inherited rule attribute</a>   | <a href="https://bazel.build/concepts/labels">List of labels</a> | optional |  `None`  |
| <a id="pyrefly_configuration-visibility"></a>visibility |  The visibility to be passed to this macro's exported targets. It always implicitly includes the location where this macro is instantiated, so this attribute only needs to be explicitly set if you want the macro's targets to be additionally visible somewhere else.   | <a href="https://bazel.build/concepts/labels">List of labels</a>; <a href="https://bazel.build/reference/be/common-definitions#configurable-attributes">nonconfigurable</a> | optional |  |


<a id="pyrefly_baselines"></a>

## pyrefly_baselines

<pre>
load("@pyrefly.bzl", "pyrefly_baselines")

pyrefly_baselines(<a href="#pyrefly_baselines-name">name</a>, <a href="#pyrefly_baselines-srcs">srcs</a>, <a href="#pyrefly_baselines-update_aspect">update_aspect</a>)
</pre>

Collects per-target Pyrefly baseline JSON files.

**ATTRIBUTES**


| Name  | Description | Type | Mandatory | Default |
| :------------- | :------------- | :------------- | :------------- | :------------- |
| <a id="pyrefly_baselines-name"></a>name |  A unique name for this target.   | <a href="https://bazel.build/concepts/labels#target-names">Name</a> | required |  |
| <a id="pyrefly_baselines-srcs"></a>srcs |  Source JSON baseline files whose package-relative paths mirror checked target labels.   | <a href="https://bazel.build/concepts/labels">List of labels</a> | optional |  `[]`  |
| <a id="pyrefly_baselines-update_aspect"></a>update_aspect |  Workspace aspect spec in <bzl-label>%<symbol> form for the baseline-update aspect.   | String | required |  |


<a id="pyrefly_stubs"></a>

## pyrefly_stubs

<pre>
load("@pyrefly.bzl", "pyrefly_stubs")

pyrefly_stubs(<a href="#pyrefly_stubs-name">name</a>, <a href="#pyrefly_stubs-configuration">configuration</a>, <a href="#pyrefly_stubs-library">library</a>, <a href="#pyrefly_stubs-include_docstrings">include_docstrings</a>, <a href="#pyrefly_stubs-include_private">include_private</a>, <a href="#pyrefly_stubs-kwargs">**kwargs</a>)
</pre>

Generate reusable Pyrefly stubs for a py_library.

**PARAMETERS**


| Name  | Description | Default Value |
| :------------- | :------------- | :------------- |
| <a id="pyrefly_stubs-name"></a>name |  Name of the generated-stub target.   |  none |
| <a id="pyrefly_stubs-configuration"></a>configuration |  pyrefly_configuration target supplying shared policy.   |  none |
| <a id="pyrefly_stubs-library"></a>library |  py_library-compatible target to pass to Pyrefly stubgen.   |  none |
| <a id="pyrefly_stubs-include_docstrings"></a>include_docstrings |  Whether generated stubs preserve docstrings.   |  `False` |
| <a id="pyrefly_stubs-include_private"></a>include_private |  Whether generated stubs include private names.   |  `False` |
| <a id="pyrefly_stubs-kwargs"></a>kwargs |  Additional common rule attributes.   |  none |
