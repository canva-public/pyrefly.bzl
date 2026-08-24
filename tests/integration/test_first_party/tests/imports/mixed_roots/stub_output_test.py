"""Assertions for Stubgen with mixed source and generated import roots."""

from pyrefly_testlib.runfiles import workspace_runfile


def test_repository_qualified_imports_inform_stub_generation() -> None:
    """The generated interface resolves imports across the repository-qualified root."""
    stub = workspace_runfile(
        "tests/imports/mixed_roots/stubs_pyrefly_stubs/"
        "tests/imports/mixed_roots/application/data_access/src/python/library.pyi"
    )

    assert "def load(record: Record) -> str: ..." in stub.read_text()
