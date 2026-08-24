"""Assertions for Stubgen inputs supplied through pyi_deps."""

from pyrefly_testlib.runfiles import workspace_runfile


def test_pyi_dependency_informs_stub_generation() -> None:
    """Types from pyi_deps are resolved in the generated interface."""
    stub = workspace_runfile(
        "tests/stubgen/pyi_dependency/library_pyrefly_stubs/"
        "tests/stubgen/pyi_dependency/library.pyi"
    )

    assert "def context_name(context: Context) -> str: ..." in stub.read_text()
