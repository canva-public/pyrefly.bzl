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


<a id="make_pyrefly_update_baseline_aspect"></a>

## make_pyrefly_update_baseline_aspect

<pre>
load("@pyrefly.bzl", "make_pyrefly_update_baseline_aspect")

make_pyrefly_update_baseline_aspect(<a href="#make_pyrefly_update_baseline_aspect-pyrefly_aspect">pyrefly_aspect</a>, <a href="#make_pyrefly_update_baseline_aspect-configuration">configuration</a>)
</pre>

Construct the on-demand aspect which generates fresh baselines.

**PARAMETERS**


| Name  | Description | Default Value |
| :------------- | :------------- | :------------- |
| <a id="make_pyrefly_update_baseline_aspect-pyrefly_aspect"></a>pyrefly_aspect |  Validation aspect returned by make_pyrefly_aspect.   |  none |
| <a id="make_pyrefly_update_baseline_aspect-configuration"></a>configuration |  Label of the pyrefly_configuration target used by pyrefly_aspect.   |  none |

**RETURNS**

An aspect which publishes fresh baseline files through pyrefly_updated_baseline.
