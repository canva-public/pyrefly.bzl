"""Unit tests for tag-based type-checking selection."""

load("@rules_testing//lib:unittest.bzl", "asserts", "unittest")
load("//pyrefly/private:configuration.bzl", "is_type_checking_enabled")

def _default_policy_checks_untagged_target_test_impl(ctx):
    """An empty tag policy checks a target without tags."""
    env = unittest.begin(ctx)
    config = struct(include_tags = set(), exclude_tags = set())
    asserts.true(env, is_type_checking_enabled(config, []))
    return unittest.end(env)

default_policy_checks_untagged_target_test = unittest.make(
    _default_policy_checks_untagged_target_test_impl,
)

def _include_policy_checks_matching_target_test_impl(ctx):
    """An include policy checks a target with any matching tag."""
    env = unittest.begin(ctx)
    config = struct(include_tags = set(["pyrefly"]), exclude_tags = set())
    asserts.true(env, is_type_checking_enabled(config, ["other", "pyrefly"]))
    return unittest.end(env)

include_policy_checks_matching_target_test = unittest.make(
    _include_policy_checks_matching_target_test_impl,
)

def _include_policy_skips_unmatched_target_test_impl(ctx):
    """An include policy skips a target without a matching tag."""
    env = unittest.begin(ctx)
    config = struct(include_tags = set(["pyrefly"]), exclude_tags = set())
    asserts.false(env, is_type_checking_enabled(config, ["other"]))
    return unittest.end(env)

include_policy_skips_unmatched_target_test = unittest.make(
    _include_policy_skips_unmatched_target_test_impl,
)

def _exclude_policy_skips_matching_target_test_impl(ctx):
    """An exclude policy skips a target with any matching tag."""
    env = unittest.begin(ctx)
    config = struct(include_tags = set(), exclude_tags = set(["no-pyrefly"]))
    asserts.false(env, is_type_checking_enabled(config, ["other", "no-pyrefly"]))
    return unittest.end(env)

exclude_policy_skips_matching_target_test = unittest.make(
    _exclude_policy_skips_matching_target_test_impl,
)

def _exclude_policy_checks_unmatched_target_test_impl(ctx):
    """An exclude policy checks a target without a matching tag."""
    env = unittest.begin(ctx)
    config = struct(include_tags = set(), exclude_tags = set(["no-pyrefly"]))
    asserts.true(env, is_type_checking_enabled(config, ["other"]))
    return unittest.end(env)

exclude_policy_checks_unmatched_target_test = unittest.make(
    _exclude_policy_checks_unmatched_target_test_impl,
)

def tag_filter_test_suite(name):
    """Instantiate tag-filter unit tests."""
    unittest.suite(
        name,
        default_policy_checks_untagged_target_test,
        include_policy_checks_matching_target_test,
        include_policy_skips_unmatched_target_test,
        exclude_policy_skips_matching_target_test,
        exclude_policy_checks_unmatched_target_test,
    )
