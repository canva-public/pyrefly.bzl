"""Providers shared by the Pyrefly rules and aspect."""

PyreflyBaselinesInfo = provider(
    doc = "Per-target Pyrefly baseline files.",
    fields = {
        "baselines": "Dictionary mapping target Labels to baseline JSON Files.",
    },
)

PyreflyConfigInfo = provider(
    doc = "Configuration and precomputed stub data for the Pyrefly aspect.",
    fields = {
        "base_config": "Optional effective pyrefly.toml File.",
        "baselines": "Dictionary mapping target Labels to baseline JSON Files.",
        "error_stale_baseline": "Whether stale baseline entries fail check actions.",
        "exclude_tags": "Set of tags which suppress Pyrefly check actions.",
        "expected_failure_labels": "Set of canonical target labels.",
        "include_tags": "Set of tags which enable Pyrefly check actions.",
        "stale_message": "Message emitted when an expected failure passes.",
        "stub_packages": "Dictionary mapping package labels to configured stub data.",
        "stubgen_include_docstrings": "Whether automatic stubgen preserves docstrings.",
        "stubgen_exclude": "Resolved exact targets and package groups excluded from stubgen.",
        "stubgen_include": "Resolved exact targets and package groups eligible for stubgen.",
        "stubgen_include_private": "Whether automatic stubgen includes private names.",
        "wrapper": "FilesToRunProvider for the unified wrapper.",
    },
)

PyreflyCheckInputsInfo = provider(
    doc = "Prepared direct inputs for Pyrefly check-like actions.",
    fields = {
        "check_sources": "Depset of direct source Files selected for checking.",
        "dependency_info": "PyreflyInfo containing transformed dependency inputs.",
        "enabled": "Whether this first-party target is eligible for checking.",
        "target_imports": "Depset of direct target import paths.",
        "target_inputs": "Depset of direct target input Files.",
    },
)

PyreflyInfo = provider(
    doc = "Curated transitive inputs propagated by the Pyrefly aspect.",
    fields = {
        "imports": "Depset of canonical transformed dependency import directories.",
        "sources": "Depset of canonical transformed dependency TreeArtifacts.",
    },
)

PyreflyTargetEnvironmentInfo = provider(
    doc = "Python runtime and platform modeled by Pyrefly for one target configuration.",
    fields = {
        "python_platform": "Pyrefly python-platform value.",
        "python_version": "Pyrefly python-version value.",
    },
)
