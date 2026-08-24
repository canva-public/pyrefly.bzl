"""Project-local Pyrefly aspects for the first-party integration fixture."""

load(
    "@pyrefly.bzl",
    "make_pyrefly_aspect",
    "make_pyrefly_update_baseline_aspect",
)
load(
    "@pyrefly_integration_testlib//:pyrefly_check.bzl",
    _make_pyrefly_check_rules = "make_pyrefly_check_rules",
    _pyrefly_check_test = "pyrefly_check_test",
)

_CONFIGURATION = Label("//:pyrefly_config")

pyrefly_aspect = make_pyrefly_aspect(configuration = _CONFIGURATION)
pyrefly_update_baseline_aspect = make_pyrefly_update_baseline_aspect(
    pyrefly_aspect = pyrefly_aspect,
    configuration = _CONFIGURATION,
)

_PYREFLY_CHECK_RULES = _make_pyrefly_check_rules(pyrefly_aspect)
_pyrefly_check_validation = _PYREFLY_CHECK_RULES.validation
pyrefly_check_inputs = _PYREFLY_CHECK_RULES.inputs

def pyrefly_check_test(name, target, **kwargs):
    """Test a target's validation outputs with the local Pyrefly aspect."""
    _pyrefly_check_test(
        validation_rule = _pyrefly_check_validation,
        name = name,
        target = target,
        **kwargs
    )
