"""Project-local Pyrefly aspects for the rules_pycross integration fixture."""

load("@pyrefly.bzl", "make_pyrefly_aspect")
load(
    "@pyrefly_integration_testlib//:pyrefly_check.bzl",
    _make_pyrefly_check_rules = "make_pyrefly_check_rules",
    _pyrefly_check_test = "pyrefly_check_test",
)

pyrefly_aspect = make_pyrefly_aspect(
    configuration = Label("//:pyrefly_config"),
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
