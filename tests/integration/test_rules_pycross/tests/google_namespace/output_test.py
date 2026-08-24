"""Assertions for distributions sharing the google namespace."""

from pyrefly_testlib.runfiles import find_runfile


def test_namespace_dependencies_use_configured_transformations() -> None:
    """One namespace package is stub-generated while the excluded one is minified."""
    stub = find_runfile(
        "site-packages/google/rpc/status_pb2.pyi",
        containing="_pyrefly_stubs/",
    )
    minified = find_runfile(
        "site-packages/google/auth/credentials.py",
        containing="_pyrefly_minified/",
    )

    assert stub.is_file()
    assert minified.is_file()
