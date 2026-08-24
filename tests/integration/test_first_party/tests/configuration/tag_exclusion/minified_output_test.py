"""Assertions for dependencies selected for minification by tag exclusion."""

from pyrefly_testlib.runfiles import workspace_runfile


def test_excluded_dependency_is_minified() -> None:
    """A dependency excluded from checking remains available as minified source."""
    output = workspace_runfile(
        "tests/configuration/tag_exclusion/dependency_pyrefly_minified"
    )

    assert (output / "tests/configuration/tag_exclusion/dependency.py").is_file()
