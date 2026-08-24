"""Assertions for a partial third-party stub mapping."""

from pyrefly_testlib.runfiles import find_runfile


def test_mapped_interfaces_are_retained_and_completed() -> None:
    """Mapped stubs match their source while Stubgen fills missing modules."""
    mapped_suffix = "_pyrefly_stubs/.pyrefly-mapped-stubs/grpc-stubs/__init__.pyi"
    mapped_stub = find_runfile(mapped_suffix)
    stubs = mapped_stub.parents[2]
    source_stub = find_runfile(
        "site-packages/grpc-stubs/__init__.pyi",
        exclude=mapped_stub,
    )
    generated_stub = find_runfile("site-packages/grpc/_auth.pyi", root=stubs)

    assert source_stub.read_bytes() == mapped_stub.read_bytes()
    assert generated_stub.is_file()
