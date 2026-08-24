"""Assertions for direct data files attached to a Python target."""

from pyrefly_testlib.runfiles import workspace_runfile


def test_type_relevant_data_is_minified() -> None:
    """Only source, interface, and py.typed data enter the minified context."""
    output = workspace_runfile(
        "tests/providers/direct_data_context/context_pyrefly_minified"
    )
    inputs = output / "tests/providers/direct_data_context/input"

    assert (inputs / "source.py").is_file()
    assert (inputs / "context.pyi").is_file()
    assert (inputs / "py.typed").is_file()
    assert not (inputs / "ignored.py").exists()
