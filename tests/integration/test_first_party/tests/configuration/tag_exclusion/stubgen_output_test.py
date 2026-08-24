"""Assertions for dependencies selected for Stubgen by tag exclusion."""

from pyrefly_testlib.runfiles import workspace_runfile


def test_excluded_dependency_is_stub_generated() -> None:
    """A Stubgen-selected dependency emits its generated interface."""
    output = workspace_runfile(
        "tests/configuration/tag_exclusion/stubgen_dependency_pyrefly_stubs"
    )

    assert (
        output / "tests/configuration/tag_exclusion/stubgen_dependency.pyi"
    ).is_file()
