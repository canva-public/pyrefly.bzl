from __future__ import annotations

import importlib.machinery
from pathlib import Path

from pyrefly.private.wrapper import cli, minify_runner
from pyrefly.private.wrapper.transformed import (
    MAPPED_STUB_ROOT,
    transformed_import_roots,
)


def test_minify_retains_only_type_relevant_files(tmp_path: Path) -> None:
    """Minification preserves Python type inputs while discarding other assets."""
    import_root = tmp_path / "wheel" / "site-packages"
    package = import_root / "sample"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("value = 1\n")
    (package / "bundled.pyi").write_text("value: int\n")
    (package / "py.typed").touch()
    (package / "notebook.ipynb").write_text("{}\n")
    (package / "data.json").write_text("{}\n")
    native_suffix = importlib.machinery.EXTENSION_SUFFIXES[0]
    (package / ("native" + native_suffix)).touch()

    output = tmp_path / "output"
    args = cli.MinifyOptions(
        output_dir=output,
        bazel_bin_dir=tmp_path / "bin",
        repository_root=tmp_path / "wheel",
        import_path=[import_root],
        input_root=tmp_path,
        input_path=[tmp_path / "wheel"],
    )

    assert minify_runner.run(args) == 0
    package_output = output / "site-packages" / "sample"
    assert (package_output / "__init__.py").read_text() == "value = 1\n"
    assert (package_output / "bundled.pyi").read_text() == "value: int\n"
    assert (package_output / "py.typed").is_file()
    assert (package_output / "notebook.ipynb").is_file()
    assert (package_output / "native.pyi").is_file()
    assert not (package_output / "data.json").exists()
    assert not (package_output / ("native" + native_suffix)).exists()
    assert transformed_import_roots(output) == [output / "site-packages"]


def test_minify_can_expose_an_external_repository_root(tmp_path: Path) -> None:
    """Import-all-repositories adds the transformed external artifact root."""
    repository = tmp_path / "wheel"
    import_root = repository / "site-packages"
    source = import_root / "sample" / "__init__.py"
    source.parent.mkdir(parents=True)
    source.write_text("value = 1\n")
    output = tmp_path / "output"
    args = cli.MinifyOptions(
        output_dir=output,
        bazel_bin_dir=tmp_path / "bin",
        repository_root=repository,
        import_path=[import_root],
        input_root=tmp_path,
        input_path=[repository],
        retain_repository_root=True,
    )

    assert minify_runner.run(args) == 0
    assert transformed_import_roots(output) == [
        output / "site-packages",
        output,
    ]


def test_minify_skips_sources_outside_repository_root(tmp_path: Path) -> None:
    """Minification ignores forwarded sources owned by another repository."""
    repository = tmp_path / "public"
    repository.mkdir()
    outside_root = tmp_path / "backing" / "site-packages"
    source = outside_root / "sample" / "__init__.py"
    source.parent.mkdir(parents=True)
    source.write_text("value = 1\n")
    output = tmp_path / "output"
    args = cli.MinifyOptions(
        output_dir=output,
        bazel_bin_dir=tmp_path / "bin",
        repository_root=repository,
        import_path=[outside_root],
        input_root=tmp_path,
        input_path=[outside_root],
    )

    assert minify_runner.run(args) == 0
    assert not (output / "site-packages" / "sample").exists()
    assert transformed_import_roots(output) == []


def test_minify_combines_partial_mapped_stubs_with_runtime_gaps(
    tmp_path: Path,
) -> None:
    """A partial mapped package wins where present and retains uncovered sources."""
    runtime_root = tmp_path / "runtime" / "site-packages"
    runtime_package = runtime_root / "sample"
    runtime_package.mkdir(parents=True)
    (runtime_package / "covered.py").write_text("value = 'runtime'\n")
    (runtime_package / "missing.py").write_text("value = 'retained'\n")

    mapped_root = tmp_path / "mapped" / "site-packages"
    mapped_package = mapped_root / "sample-stubs"
    mapped_package.mkdir(parents=True)
    (mapped_package / "covered.pyi").write_text("value: int\n")
    (mapped_package / "py.typed").write_text("partial\n")

    output = tmp_path / "output"
    args = cli.MinifyOptions(
        output_dir=output,
        bazel_bin_dir=tmp_path / "bin",
        repository_root=tmp_path / "runtime",
        import_path=[runtime_root],
        input_root=tmp_path,
        input_path=[runtime_root],
        mapped_stub_import_path=[mapped_root],
        mapped_stub_path=[mapped_root],
    )

    assert minify_runner.run(args) == 0
    assert (
        output / MAPPED_STUB_ROOT / "sample-stubs" / "covered.pyi"
    ).read_text() == "value: int\n"
    assert (output / MAPPED_STUB_ROOT / "sample-stubs" / "py.typed").read_text() == (
        "partial\n"
    )
    assert (
        output / "site-packages" / "sample" / "missing.py"
    ).read_text() == "value = 'retained'\n"
    assert not (output / "site-packages" / "sample" / "covered.py").exists()
    assert transformed_import_roots(output) == [
        output / MAPPED_STUB_ROOT,
        output / "site-packages",
    ]


def test_minify_complete_mapped_stubs_replace_runtime_sources(
    tmp_path: Path,
) -> None:
    """A complete mapped package is emitted without redundant runtime sources."""
    runtime_root = tmp_path / "runtime" / "site-packages"
    runtime_package = runtime_root / "sample"
    runtime_package.mkdir(parents=True)
    (runtime_package / "__init__.py").write_text("value = 'runtime'\n")

    mapped_root = tmp_path / "mapped" / "site-packages"
    mapped_package = mapped_root / "sample-stubs"
    mapped_package.mkdir(parents=True)
    (mapped_package / "__init__.pyi").write_text("value: int\n")

    output = tmp_path / "output"
    args = cli.MinifyOptions(
        output_dir=output,
        bazel_bin_dir=tmp_path / "bin",
        repository_root=tmp_path / "runtime",
        import_path=[runtime_root],
        input_root=tmp_path,
        input_path=[runtime_root],
        mapped_stub_import_path=[mapped_root],
        mapped_stub_path=[mapped_root],
    )

    assert minify_runner.run(args) == 0
    assert (
        output / MAPPED_STUB_ROOT / "sample-stubs" / "__init__.pyi"
    ).read_text() == "value: int\n"
    assert not (output / "site-packages" / "sample").exists()
