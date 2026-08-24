from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pytest

from pyrefly.private.wrapper import import_view
from pyrefly.private.wrapper.input_context import DependencyContext
from pyrefly.private.wrapper.transformed import write_import_roots


def _dependencies(
    *,
    runtime: Iterable[Path] = (),
    stubs: Iterable[Path] = (),
    transformed: Iterable[Path] = (),
) -> DependencyContext:
    return DependencyContext(tuple(runtime), tuple(stubs), tuple(transformed))


def test_import_view_plan_follows_required_precedence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dependency imports prefer mapped, bundled, and generated stubs to sources."""
    mapped = tmp_path / "mapped"
    bundled = tmp_path / "bundled"
    generated = tmp_path / "generated"
    runtime = tmp_path / "runtime"
    target = tmp_path / "target"
    for directory in (mapped, bundled, generated, runtime, target):
        directory.mkdir()
    monkeypatch.setattr(import_view, "_stdlib_paths", lambda: [])

    plan = import_view.plan_import_view(
        _dependencies(
            runtime=[target, runtime],
            stubs=[mapped],
            transformed=[generated],
        ),
        bundled_stub_dirs=[bundled],
        bazel_bin_dir=tmp_path / "bin",
        excluded_runtime_roots=[target],
    )

    assert plan.configured_stub_roots == (mapped,)
    assert plan.bundled_stub_roots == (bundled,)
    assert plan.transformed_dependency_roots == (generated,)
    assert plan.runtime_roots == (runtime,)
    assert plan.ordered_roots == (mapped, bundled, generated, runtime)


def test_merged_import_view_preserves_precedence_on_collisions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The highest-precedence definition wins when dependency tiers collide."""
    roots = {
        name: tmp_path / name for name in ("mapped", "bundled", "generated", "runtime")
    }
    for name, root in roots.items():
        module = root / "sample" / "__init__.pyi"
        module.parent.mkdir(parents=True)
        module.write_text(name)
    monkeypatch.setattr(import_view, "_stdlib_paths", lambda: [])

    cases = [
        (["mapped"], ["bundled"], ["generated"], ["runtime"], "mapped"),
        ([], ["bundled"], ["generated"], ["runtime"], "bundled"),
        ([], [], ["generated"], ["runtime"], "generated"),
        ([], [], [], ["runtime"], "runtime"),
    ]
    for mapped, bundled, generated, runtime, expected in cases:
        materialized = import_view.materialize_import_view(
            import_view.plan_import_view(
                _dependencies(
                    runtime=(roots[name] for name in runtime),
                    stubs=(roots[name] for name in mapped),
                    transformed=(roots[name] for name in generated),
                ),
                bundled_stub_dirs=[roots[name] for name in bundled],
                bazel_bin_dir=tmp_path / "bin",
            )
        )
        assert len(materialized) == 1
        assert (
            Path(materialized[0]) / "sample" / "__init__.pyi"
        ).read_text() == expected


def test_merges_every_dependency_tier_into_one_site_packages_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """All non-conflicting dependency tiers remain importable from one root."""
    roots = {
        name: tmp_path / name for name in ("mapped", "bundled", "generated", "runtime")
    }
    for name, root in roots.items():
        module = root / name / "__init__.pyi"
        module.parent.mkdir(parents=True)
        module.write_text(f"{name}: int\n")
    monkeypatch.setattr(import_view, "_stdlib_paths", lambda: [])

    materialized = import_view.materialize_import_view(
        import_view.plan_import_view(
            _dependencies(
                runtime=[roots["runtime"]],
                stubs=[roots["mapped"]],
                transformed=[roots["generated"]],
            ),
            bundled_stub_dirs=[roots["bundled"]],
            bazel_bin_dir=tmp_path / "bin",
        )
    )

    assert len(materialized) == 1
    merged = Path(materialized[0])
    for name in roots:
        assert (merged / name / "__init__.pyi").read_text() == f"{name}: int\n"


def test_transformed_dependency_preserves_repository_and_explicit_import_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One repository-relative artifact exposes every declared import form."""
    transformed = tmp_path / "transformed"
    package_root = transformed / "application" / "data_access" / "src" / "python"
    (package_root / "generated").mkdir(parents=True)
    (package_root / "model.pyi").write_text("value: int\n")
    (package_root / "generated" / "records.pyi").write_text("record: int\n")
    write_import_roots(
        transformed,
        [Path("."), Path("application/data_access/src/python")],
    )
    monkeypatch.setattr(import_view, "_stdlib_paths", lambda: [])

    materialized = import_view.materialize_import_view(
        import_view.plan_import_view(
            _dependencies(transformed=[transformed]),
            bundled_stub_dirs=[],
            bazel_bin_dir=tmp_path / "bin",
        )
    )

    assert len(materialized) == 1
    merged = Path(materialized[0])
    assert (
        merged / "application/data_access/src/python/model.pyi"
    ).read_text() == "value: int\n"
    assert (merged / "generated" / "records.pyi").read_text() == "record: int\n"
