"""Assertions for the public pyrefly_stubs rule."""

from pyrefly_testlib.runfiles import workspace_runfile


def test_public_rule_generates_expected_interface() -> None:
    """The public rule emits the inferred type for the fixture value."""
    stub = workspace_runfile(
        "tests/stubgen/manual/stubs_pyrefly_stubs/tests/stubgen/manual/fixture.pyi"
    )

    assert "value: int = 1" in stub.read_text().splitlines()
