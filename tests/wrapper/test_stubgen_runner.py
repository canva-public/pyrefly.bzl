from __future__ import annotations

import importlib.machinery
import os
from dataclasses import replace
from pathlib import Path

from pyrefly.private.wrapper import cli, stubgen_runner
from pyrefly.private.wrapper.transformed import (
    MAPPED_STUB_ROOT,
    transformed_import_roots,
)

_PYREFLY_EXECUTABLE = str(
    (Path.cwd() / os.environ["PYREFLY_TEST_EXECUTABLE"]).absolute()
)


def _args(
    tmp_path: Path,
    inputs: list[Path],
) -> cli.StubgenOptions:
    return cli.StubgenOptions(
        pyrefly_executable=_PYREFLY_EXECUTABLE,
        output_dir=tmp_path / "output",
        bazel_bin_dir=tmp_path / "bin",
        python_platform="linux",
        python_version="3.13.11",
        repository_root=tmp_path,
        input_root=tmp_path,
        input_path=inputs,
        retain_repository_root=True,
    )


def test_directory_preserves_typed_assets_and_generates_stubs(
    tmp_path: Path,
) -> None:
    """One import tree contains both generated interfaces and bundled type data."""
    source = tmp_path / "wheel"
    package = source / "site-packages" / "sample"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("value = 1\n")
    (package / "typed.pyi").write_text("value: int\n")
    (package / "py.typed").touch()
    args = replace(
        _args(tmp_path, [source]),
        import_path=[source / "site-packages"],
        repository_root=source,
        retain_repository_root=False,
    )

    assert stubgen_runner.run(args) == 0
    package_output = args.output_dir / "site-packages" / "sample"
    assert (package_output / "typed.pyi").read_text() == "value: int\n"
    assert (package_output / "__init__.pyi").is_file()
    assert not (package_output / "__init__.py").exists()


def test_workspace_source_generates_stub_from_input_root(tmp_path: Path) -> None:
    """Generated stubs retain a workspace module's import path."""
    source = tmp_path / "package" / "module.py"
    source.parent.mkdir(parents=True)
    source.write_text("value: int = 1\n")
    args = _args(tmp_path, [source])

    assert stubgen_runner.run(args) == 0
    assert (args.output_dir / "package" / "module.pyi").is_file()
    assert transformed_import_roots(args.output_dir) == [args.output_dir]


def test_dependency_imports_resolve_through_effective_config(tmp_path: Path) -> None:
    """Dependency stubs inform the types emitted for a target module."""
    dependency = tmp_path / "dependencies" / "dependency"
    dependency.mkdir(parents=True)
    (dependency / "__init__.pyi").write_text("class Thing: ...\n")
    source = tmp_path / "package" / "module.py"
    source.parent.mkdir(parents=True)
    source.write_text("from dependency import Thing\nvalue = Thing()\n")
    args = replace(
        _args(tmp_path, [source]),
        stub_import_path=[dependency.parent],
    )

    assert stubgen_runner.run(args) == 0
    assert "value: Thing" in (args.output_dir / "package" / "module.pyi").read_text()


def test_include_private_and_docstrings_options(tmp_path: Path) -> None:
    """Requested private names and docstrings appear in generated stubs."""
    source = tmp_path / "package" / "module.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        'def public() -> None:\n    """preserved documentation"""\n\n_private = 1\n'
    )
    args = replace(
        _args(tmp_path, [source]),
        include_docstrings=True,
        include_private=True,
    )

    assert stubgen_runner.run(args) == 0
    generated = (args.output_dir / "package" / "module.pyi").read_text()
    assert '"""preserved documentation"""' in generated
    assert "_private" in generated


def test_partial_bundled_stubs_only_generate_uncovered_files(
    tmp_path: Path,
) -> None:
    """Bundled sibling stubs win while uncovered modules still receive stubs."""
    package = tmp_path / "site-packages" / "sample"
    package.mkdir(parents=True)
    public_py = package / "public.py"
    public_pyi = package / "public.pyi"
    private_py = package / "private.py"
    public_py.write_text("value = 1\n")
    public_pyi.write_text("value: int\n")
    private_py.write_text("private = 1\n")
    args = replace(
        _args(tmp_path, [public_py, public_pyi, private_py]),
        import_path=[tmp_path / "site-packages"],
    )

    assert stubgen_runner.run(args) == 0
    package_output = args.output_dir / "site-packages" / "sample"
    assert (package_output / "public.pyi").read_text() == "value: int\n"
    assert (package_output / "private.pyi").is_file()


def test_partial_mapped_stubs_are_combined_with_generated_runtime_gaps(
    tmp_path: Path,
) -> None:
    """Mapped stubs and their dependencies inform generated runtime gaps."""
    runtime_root = tmp_path / "runtime" / "site-packages"
    runtime_package = runtime_root / "sample"
    runtime_package.mkdir(parents=True)
    (runtime_package / "covered.py").write_text("class Thing: pass\n")
    (runtime_package / "missing.py").write_text(
        "from mapped_dependency import Context\n"
        "from sample.covered import Thing\n"
        "context = Context()\n"
        "value = Thing()\n"
    )

    mapped_root = tmp_path / "mapped" / "site-packages"
    mapped_package = mapped_root / "sample-stubs"
    mapped_package.mkdir(parents=True)
    (mapped_package / "covered.pyi").write_text("class Thing: ...\n")
    (mapped_package / "py.typed").write_text("partial\n")
    mapped_dependency_root = tmp_path / "mapped_dependency" / "site-packages"
    mapped_dependency = mapped_dependency_root / "mapped_dependency"
    mapped_dependency.mkdir(parents=True)
    (mapped_dependency / "__init__.pyi").write_text("class Context: ...\n")
    args = replace(
        _args(tmp_path, [runtime_root]),
        import_path=[runtime_root],
        mapped_stub_dependency_import_path=[mapped_dependency_root],
        mapped_stub_dependency_path=[mapped_dependency_root],
        mapped_stub_import_path=[mapped_root],
        mapped_stub_path=[mapped_root],
        stub_import_path=[mapped_root],
    )

    assert stubgen_runner.run(args) == 0
    assert (
        args.output_dir / MAPPED_STUB_ROOT / "sample-stubs" / "covered.pyi"
    ).read_text() == "class Thing: ...\n"
    assert (
        args.output_dir / MAPPED_STUB_ROOT / "sample-stubs" / "py.typed"
    ).read_text() == "partial\n"
    assert (
        "value: Thing"
        in (
            args.output_dir / "runtime" / "site-packages" / "sample" / "missing.pyi"
        ).read_text()
    )
    assert (
        "context: Context"
        in (
            args.output_dir / "runtime" / "site-packages" / "sample" / "missing.pyi"
        ).read_text()
    )
    assert not (
        args.output_dir / "runtime" / "site-packages" / "sample" / "covered.pyi"
    ).exists()


def test_individual_native_extension_gets_pyi_shim(tmp_path: Path) -> None:
    """A native extension remains importable to the type checker."""
    suffix = importlib.machinery.EXTENSION_SUFFIXES[0]
    native = tmp_path / "site-packages" / "sample" / ("native" + suffix)
    native.parent.mkdir(parents=True)
    native.touch()
    args = replace(
        _args(tmp_path, [native]),
        import_path=[tmp_path / "site-packages"],
    )

    assert stubgen_runner.run(args) == 0
    assert (args.output_dir / "site-packages" / "sample" / "native.pyi").is_file()
