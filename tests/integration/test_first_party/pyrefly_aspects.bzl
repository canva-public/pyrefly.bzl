"""Project-local Pyrefly aspects for the first-party integration fixture."""

load(
    "@pyrefly.bzl",
    "make_pyrefly_aspect",
)
load(
    "@pyrefly_integration_testlib//:pyrefly_check.bzl",
    _make_pyrefly_check_rules = "make_pyrefly_check_rules",
    _pyrefly_check_test = "pyrefly_check_test",
)

_CONFIGURATION = Label("//:pyrefly_config")
_STRICT_CONFIGURATION = Label("//:strict_pyrefly_config")

pyrefly_aspect = make_pyrefly_aspect(configuration = _CONFIGURATION)
_strict_pyrefly_aspect = make_pyrefly_aspect(configuration = _STRICT_CONFIGURATION)

_PYREFLY_CHECK_RULES = _make_pyrefly_check_rules(pyrefly_aspect)
_STRICT_PYREFLY_CHECK_RULES = _make_pyrefly_check_rules(_strict_pyrefly_aspect)
_pyrefly_check_validation = _PYREFLY_CHECK_RULES.validation
_strict_pyrefly_check_validation = _STRICT_PYREFLY_CHECK_RULES.validation
pyrefly_check_inputs = _PYREFLY_CHECK_RULES.inputs

def pyrefly_check_test(name, target, **kwargs):
    """Test a target's validation outputs with the local Pyrefly aspect."""
    _pyrefly_check_test(
        validation_rule = _pyrefly_check_validation,
        name = name,
        target = target,
        **kwargs
    )

def pyrefly_strict_check(name, target, **kwargs):
    """Expose validation outputs from the stale-baseline-error configuration."""
    _strict_pyrefly_check_validation(
        name = name,
        target = target,
        **kwargs
    )
