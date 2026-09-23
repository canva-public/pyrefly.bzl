<!-- Generated with Stardoc: http://skydoc.bazel.build -->

Public API for pyrefly.bzl.

<a id="make_pyrefly_aspect"></a>

## make_pyrefly_aspect

<pre>
load("@pyrefly.bzl", "make_pyrefly_aspect")

make_pyrefly_aspect(<a href="#make_pyrefly_aspect-configuration">configuration</a>)
</pre>

Construct the validation aspect with workspace-owned configuration.

**PARAMETERS**


| Name  | Description | Default Value |
| :------------- | :------------- | :------------- |
| <a id="make_pyrefly_aspect-configuration"></a>configuration |  Label of a pyrefly_configuration target.   |  none |

**RETURNS**

An aspect which checks first-party Python targets and propagates dependency interfaces.
