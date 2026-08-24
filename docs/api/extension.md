<!-- Generated with Stardoc: http://skydoc.bazel.build -->

Public API for pyrefly.bzl.

<a id="pyrefly"></a>

## pyrefly

<pre>
pyrefly = use_extension("@pyrefly.bzl", "pyrefly")
pyrefly.toolchain(<a href="#pyrefly.toolchain-toolchain">toolchain</a>, <a href="#pyrefly.toolchain-version">version</a>)
</pre>

Provisions a downloadable or custom Pyrefly toolchain for the root module.


**TAG CLASSES**

<a id="pyrefly.toolchain"></a>

### toolchain

Selects exactly one downloadable version or custom executable for Pyrefly.

**Attributes**

| Name  | Description | Type | Mandatory | Default |
| :------------- | :------------- | :------------- | :------------- | :------------- |
| <a id="pyrefly.toolchain-toolchain"></a>toolchain |  Executable target to register as a custom Pyrefly toolchain.   | <a href="https://bazel.build/concepts/labels">Label</a> | optional |  `None`  |
| <a id="pyrefly.toolchain-version"></a>version |  Pyrefly release version to download from the ruleset registry.   | String | optional |  `""`  |
