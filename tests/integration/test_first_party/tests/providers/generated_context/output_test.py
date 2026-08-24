"""Assertions for generated Python provider inputs."""

from pyrefly_testlib.runfiles import workspace_runfile


def test_generated_provider_inputs_are_minified() -> None:
    """Generated sources and interfaces are retained without unrelated metadata."""
    output = workspace_runfile(
        "tests/providers/generated_context/context_pyrefly_minified"
    )
    inputs = output / "tests/providers/generated_context"

    assert (inputs / "context.py").is_file()
    assert (inputs / "context.pyi").is_file()
    assert not (inputs / "context.txt").exists()
