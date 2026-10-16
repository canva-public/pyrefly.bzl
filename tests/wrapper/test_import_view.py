from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from opentelemetry.trace import Tracer

from pyrefly.private.wrapper import config, import_view
from pyrefly.private.wrapper.input_context import DependencyContext
from pyrefly.private.wrapper.transformed import write_import_roots


def _dependencies(
    *,
    runtime: Iterable[Path] = (),
    stubs: Iterable[Path] = (),
    transformed: Iterable[Path] = (),
) -> DependencyContext:
    return DependencyContext(tuple(runtime), tuple(stubs), tuple(transformed))


@pytest.fixture
def tracing() -> Iterator[tuple[Tracer, InMemorySpanExporter]]:
    provider = TracerProvider()
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    try:
        yield provider.get_tracer(__name__), exporter
    finally:
        provider.shutdown()


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


def test_materialization_span_reports_merge_work_and_deduplicated_roots(
    tmp_path: Path,
    tracing: tuple[Tracer, InMemorySpanExporter],
) -> None:
    """The current span records work across dependency tiers after root deduplication."""
    first = tmp_path / "first"
    second = tmp_path / "second"
    (first / "sample").mkdir(parents=True)
    (second / "sample").mkdir(parents=True)
    (first / "sample" / "a.pyi").touch()
    (second / "sample" / "b.pyi").touch()
    plan = import_view.ImportViewPlan((), (first,), (), (), (second, first))
    tracer, exporter = tracing

    with tracer.start_as_current_span("materialize-import-view"):
        materialized = import_view.materialize_import_view(plan)

    assert len(materialized) == 1
    span = exporter.get_finished_spans()[0]
    assert dict(span.attributes or {}) == {
        "pyrefly.import_root.count": 2,
        "pyrefly.import_view.entries_visited": 4,
        "pyrefly.import_view.directory_collisions": 1,
        "pyrefly.import_view.symlinks_created": 3,
        "pyrefly.import_view.fallback": False,
    }


@pytest.mark.parametrize("root_count", [0, 1])
def test_materialization_span_reports_zero_work_without_a_merge(
    tmp_path: Path,
    tracing: tuple[Tracer, InMemorySpanExporter],
    root_count: int,
) -> None:
    """Fast paths still expose complete zero-work counters on the current span."""
    root = tmp_path / "root"
    root.mkdir()
    (root / "module.pyi").touch()
    roots = (root,)[:root_count]
    plan = import_view.ImportViewPlan((), (), (), (), roots)
    tracer, exporter = tracing

    with tracer.start_as_current_span("materialize-import-view"):
        assert import_view.materialize_import_view(plan) == [
            str(path) for path in roots
        ]

    span = exporter.get_finished_spans()[0]
    assert dict(span.attributes or {}) == {
        "pyrefly.import_root.count": root_count,
        "pyrefly.import_view.entries_visited": 0,
        "pyrefly.import_view.directory_collisions": 0,
        "pyrefly.import_view.symlinks_created": 0,
        "pyrefly.import_view.fallback": False,
    }


def test_materialization_span_reports_fallback_with_partial_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tracing: tuple[Tracer, InMemorySpanExporter],
) -> None:
    """A failed merge exports completed operations alongside the fallback flag."""
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "a.pyi").touch()
    (second / "b.pyi").touch()
    original_symlink = config.os.symlink

    def fail_later_symlink(source: Path, destination: Path) -> None:
        if destination.name == "b.pyi":
            raise OSError("Symlink creation failed")
        original_symlink(source, destination)

    monkeypatch.setattr(config.os, "symlink", fail_later_symlink)
    plan = import_view.ImportViewPlan((), (), (), (), (first, second))
    tracer, exporter = tracing

    with tracer.start_as_current_span("materialize-import-view"):
        assert import_view.materialize_import_view(plan) == [str(first), str(second)]

    span = exporter.get_finished_spans()[0]
    assert dict(span.attributes or {}) == {
        "pyrefly.import_root.count": 2,
        "pyrefly.import_view.entries_visited": 2,
        "pyrefly.import_view.directory_collisions": 0,
        "pyrefly.import_view.symlinks_created": 1,
        "pyrefly.import_view.fallback": True,
    }
