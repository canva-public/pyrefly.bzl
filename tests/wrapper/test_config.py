from __future__ import annotations

from pathlib import Path

import pytest

from pyrefly.private.wrapper import config
from pyrefly.private.wrapper.input_context import DependencyContext, DirectInputs


def test_loads_top_level_pyrefly_config(tmp_path: Path) -> None:
    """A pyrefly.toml file supplies top-level policy and nested error settings."""
    path = tmp_path / "pyrefly.toml"
    path.write_text(
        'ignore-missing-imports = true\n[errors]\nmissing-import = "warn"\n'
    )

    assert config.load_base_config(path) == {
        "ignore-missing-imports": True,
        "errors": {"missing-import": "warn"},
    }


def test_loads_only_pyrefly_table_from_pyproject(tmp_path: Path) -> None:
    """Only the tool.pyrefly table from pyproject.toml becomes Pyrefly policy."""
    path = tmp_path / "pyproject.toml"
    path.write_text('[project]\nname = "consumer"\n[tool.pyrefly]\nstrict = true\n')

    assert config.load_base_config(path) == {"strict": True}


def test_rejects_missing_pyproject_table_and_invalid_filename(tmp_path: Path) -> None:
    """Configuration fails clearly for unsupported files or missing policy."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "consumer"\n')
    with pytest.raises(config.ConfigError, match="tool.pyrefly"):
        config.load_base_config(pyproject)

    invalid = tmp_path / "settings.toml"
    invalid.write_text("")
    with pytest.raises(config.ConfigError, match="must be named"):
        config.load_base_config(invalid)


def test_build_config_preserves_policy_and_uses_target_environment(
    tmp_path: Path,
) -> None:
    """Consumer policy survives while the configured target environment wins."""
    base = tmp_path / "pyrefly.toml"
    base.write_text(
        'ignore-missing-imports = true\nproject-includes = ["old.py"]\n'
        'python-version = "3.9"\n[errors]\nmissing-import = "warn"\n'
    )
    package = tmp_path / "package"
    package.mkdir()

    result = config.build_config(
        source_files=[Path("src/app.py")],
        search_paths=[Path("src")],
        site_package_paths=[str(package)],
        python_platform="darwin",
        python_version="3.12.7",
        base_config=base,
    )

    assert result["project-includes"] == ["src/app.py"]
    assert result["python-platform"] == "darwin"
    assert result["python-version"] == "3.12.7"
    assert result["ignore-missing-imports"] is True
    assert result["errors"] == {"missing-import": "warn"}
    assert result["site-package-path"] == [str(package)]
    assert result["skip-interpreter-query"] is True


def test_build_config_omits_includes_matching_project_excludes(
    tmp_path: Path,
) -> None:
    """Excluded sources do not become warning-producing project includes."""
    excluded = tmp_path / "src/query_understand_llm_proto_service.py"
    included = tmp_path / "src/app.py"
    exclude_pattern = tmp_path / "**/*_proto_service.py"
    base = tmp_path / "pyrefly.toml"
    base.write_text(f'project-excludes = ["{exclude_pattern.as_posix()}"]\n')

    result = config.build_config(
        source_files=[excluded, included],
        search_paths=[],
        site_package_paths=[],
        python_platform="linux",
        python_version="3.13.11",
        base_config=base,
    )

    assert result["project-includes"] == [str(included)]
    assert result["project-excludes"] == [exclude_pattern.as_posix()]


def test_build_config_preserves_includes_for_invalid_exclude_globs(
    tmp_path: Path,
) -> None:
    """Malformed exclude globs remain Pyrefly's configuration error to report."""
    base = tmp_path / "pyrefly.toml"
    base.write_text('project-excludes = ["src/***.py"]\n')

    result = config.build_config(
        source_files=[Path("src/app.py")],
        search_paths=[],
        site_package_paths=[],
        python_platform="linux",
        python_version="3.13.11",
        base_config=base,
    )

    assert result["project-includes"] == ["src/app.py"]


def test_build_config_uses_per_target_baseline_over_base_config(tmp_path: Path) -> None:
    """The selected target baseline replaces shared baseline policy."""
    base = tmp_path / "pyrefly.toml"
    base.write_text('baseline = "shared.json"\n')
    result = config.build_config(
        source_files=[Path("src/app.py")],
        search_paths=[Path("src")],
        site_package_paths=[],
        python_platform="linux",
        python_version="3.13.11",
        base_config=base,
        baseline=Path("pyrefly_baselines/src/app.json"),
    )

    assert result["baseline"] == "pyrefly_baselines/src/app.json"


def test_build_config_removes_unmapped_base_config_baseline(tmp_path: Path) -> None:
    """A target without a mapped baseline cannot inherit an undeclared file."""
    base = tmp_path / "pyrefly.toml"
    base.write_text('baseline = "shared.json"\n')
    result = config.build_config(
        source_files=[Path("src/app.py")],
        search_paths=[Path("src")],
        site_package_paths=[],
        python_platform="linux",
        python_version="3.13.11",
        base_config=base,
    )

    assert "baseline" not in result


def test_resolves_source_layout_owning_direct_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only the import root containing a direct source enters its layout."""
    monkeypatch.chdir(tmp_path)
    target_root = Path("target/site-packages")
    dependency_root = Path("dependency/site-packages")
    source = target_root / "transformers/trainer.py"
    source.parent.mkdir(parents=True)
    source.touch()
    dependency_root.mkdir(parents=True)

    layout = config.resolve_source_layout(
        [source],
        [target_root, dependency_root],
        Path("bazel-out/bin"),
        Path("."),
    )

    assert layout.declared_roots == (target_root,)
    assert layout.effective_roots == (target_root,)


def test_resolves_layouts_across_all_dependencies_before_source_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Generated dependency roots precede source roots across the whole graph."""
    monkeypatch.chdir(tmp_path)
    bazel_bin_dir = Path("bazel-out/bin")
    generated_dependency = bazel_bin_dir / "second"
    source_dependency = Path("first")
    generated_dependency.mkdir(parents=True)
    source_dependency.mkdir()

    assert config.resolve_import_paths(
        [Path("first"), Path("second")],
        bazel_bin_dir,
    ) == [
        generated_dependency,
        source_dependency,
    ]


def test_discovers_bundled_stubs_inside_declared_tree_artifacts(
    tmp_path: Path,
) -> None:
    """Bundled stubs are retained without duplicating sources or replacement stubs."""
    wheel = tmp_path / "wheel"
    bundled = wheel / "site-packages" / "sample" / "__init__.pyi"
    source = wheel / "site-packages" / "sample" / "__init__.py"
    mapped = tmp_path / "mapped"
    generated = tmp_path / "generated"
    bundled.parent.mkdir(parents=True)
    bundled.write_text("value: int\n")
    source.write_text("value = 1\n")
    (mapped / "mapped").mkdir(parents=True)
    (mapped / "mapped" / "__init__.pyi").write_text("mapped: int\n")
    (generated / "generated").mkdir(parents=True)
    (generated / "generated" / "__init__.pyi").write_text("generated: int\n")
    overlay = tmp_path / "overlay"

    assert config.materialize_bundled_stub_overlay(
        DirectInputs(
            paths=(wheel, mapped, generated),
            import_roots=(wheel / "site-packages",),
        ),
        DependencyContext(
            runtime_import_roots=(),
            stub_roots=(mapped,),
            transformed_trees=(generated,),
        ),
        overlay,
        bazel_bin_dir=tmp_path / "bin",
    )
    assert (overlay / "sample" / "__init__.pyi").read_text() == "value: int\n"
    assert not (overlay / "sample" / "__init__.py").exists()
    assert not (overlay / "mapped").exists()
    assert not (overlay / "generated").exists()


@pytest.mark.parametrize(
    ("patterns", "sources", "expected_includes"),
    [
        (["src/generated"], ["src/generated/model.py"], []),
        (["src/**/generated/*.py"], ["src/generated/model.py"], []),
        (["src/**/generated/*.py"], ["src/nested/generated/model.py"], []),
        (["src/*.py"], ["src/nested/model.py"], []),
        (
            ["src/excluded.py"],
            ["src/excluded.py", "src/included.py"],
            ["src/included.py"],
        ),
        (["src**"], ["src/model.py"], ["src/model.py"]),
        ([], ["src/model.py"], ["src/model.py"]),
    ],
)
def test_build_config_filters_project_includes_with_pyrefly_globs(
    tmp_path: Path,
    patterns: list[str],
    sources: list[str],
    expected_includes: list[str],
) -> None:
    """Project includes use Pyrefly's exclude glob matching behaviour."""
    base = tmp_path / "pyrefly.toml"
    patterns_toml = ", ".join(f'"{pattern}"' for pattern in patterns)
    base.write_text(f"project-excludes = [{patterns_toml}]\n")

    result = config.build_config(
        source_files=[Path(source) for source in sources],
        search_paths=[],
        site_package_paths=[],
        python_platform="linux",
        python_version="3.13.11",
        base_config=base,
    )

    assert result["project-includes"] == expected_includes


def test_namespace_packages_are_merged(tmp_path: Path) -> None:
    """Distinct branches of one namespace package remain importable together."""
    first = tmp_path / "first"
    second = tmp_path / "second"
    (first / "google" / "cloud").mkdir(parents=True)
    (second / "google" / "api").mkdir(parents=True)
    (first / "google" / "cloud" / "a.pyi").touch()
    (second / "google" / "api" / "b.pyi").touch()

    merged = Path(config.merge_site_package_dirs([first, second])[0])

    assert (merged / "google" / "cloud" / "a.pyi").is_file()
    assert (merged / "google" / "api" / "b.pyi").is_file()


def test_merge_falls_back_when_symlinks_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dependency roots remain usable when a combined import view cannot be made."""
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "a.py").touch()
    monkeypatch.setattr(
        config.os, "symlink", lambda *_args: (_ for _ in ()).throw(OSError())
    )

    assert config.merge_site_package_dirs([first, second]) == [str(first), str(second)]
