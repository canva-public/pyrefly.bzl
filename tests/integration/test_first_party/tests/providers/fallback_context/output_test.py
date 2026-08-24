"""Assertions for Python providers that omit direct source fields."""

from pyrefly_testlib.runfiles import workspace_runfile


def test_rule_attributes_supply_fallback_python_inputs() -> None:
    """Fallback collection retains type inputs and excludes unrelated files."""
    output = workspace_runfile(
        "tests/providers/fallback_context/context_pyrefly_minified"
    )
    inputs = output / "tests/providers/fallback_context/input"

    assert (inputs / "source.py").is_file()
    assert (inputs / "context.pyi").is_file()
    assert (inputs / "py.typed").is_file()
    assert not (inputs / "ignored.py").exists()
    assert not (output / "tests/providers/fallback_context/context.txt").exists()
