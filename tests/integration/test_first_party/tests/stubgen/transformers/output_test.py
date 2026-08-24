"""Assertions for the Transformers-style Stubgen fixture."""

from pyrefly_testlib.runfiles import workspace_runfile


def test_conditional_fields_match_expected_interface() -> None:
    """Conditional fields remain complete and match the checked-in interface."""
    stub = workspace_runfile(
        "tests/stubgen/transformers/stubs_pyrefly_stubs/"
        "tests/stubgen/transformers/site-packages/transformers/trainer.pyi"
    )
    expected = workspace_runfile(
        "tests/stubgen/transformers/expected/trainer.pyi.golden"
    )
    actual_text = stub.read_text()

    assert "Incomplete" not in actual_text
    assert actual_text == expected.read_text()
