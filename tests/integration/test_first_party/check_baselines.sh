#!/usr/bin/env bash

set -euo pipefail

fixture_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -n "${TEST_TMPDIR:-}" ]]; then
  workspace_source="$(cd "$fixture_dir/../../.." && pwd)"
  workspace_copy="$TEST_TMPDIR/writable_workspace"
  mkdir -p "$workspace_copy"
  cp -RL "$workspace_source/." "$workspace_copy"
  chmod -R u+w "$workspace_copy"
  fixture_dir="$workspace_copy/tests/integration/test_first_party"
fi
cd "$fixture_dir"

bazel=(
  "${BIT_BAZEL_BINARY:-bazel}"
  "--nohome_rc"
  "--nosystem_rc"
)
if [[ -n "${TEST_TMPDIR:-}" ]]; then
  bazel+=("--output_user_root=$TEST_TMPDIR/bazel")
fi

nested_bazel="${bazel[0]}"
if [[ -n "${TEST_TMPDIR:-}" ]]; then
  nested_bazel="$TEST_TMPDIR/nested-bazel"
  {
    printf '#!/usr/bin/env bash\nexec'
    for bazel_arg in "${bazel[@]}"; do
      printf ' %q' "$bazel_arg"
    done
    printf ' "$@"\n'
  } >"$nested_bazel"
  chmod +x "$nested_bazel"
fi

targets=(
  //tests/baselines:baseline_cache_a
  //tests/baselines:baseline_cache_b
  //tests/baselines:baselined_failure
  //tests/baselines:clean
)
"${bazel[@]}" build "${targets[@]}"
bazel_bin="$("${bazel[@]}" info bazel-bin)"

assert_action_baseline() {
  local target="$1"
  local expected_baseline="$2"
  local unexpected_baseline="$3"
  local output
  output="$("${bazel[@]}" aquery \
    --include_artifacts \
    "mnemonic(\"PyreflyCheck\", //tests/baselines:$target)" 2>&1)"
  if ! grep -F "pyrefly_baselines/tests/baselines/$expected_baseline.json" \
    <<<"$output" >/dev/null; then
    echo "Expected $target check inputs to contain $expected_baseline.json" >&2
    printf '%s\n' "$output" >&2
    exit 1
  fi
  if grep -F "pyrefly_baselines/tests/baselines/$unexpected_baseline.json" \
    <<<"$output" >/dev/null; then
    echo "Unexpected $unexpected_baseline.json in $target check inputs" >&2
    printf '%s\n' "$output" >&2
    exit 1
  fi
}

assert_action_baseline baseline_cache_a baseline_cache_a baseline_cache_b
assert_action_baseline baseline_cache_b baseline_cache_b baseline_cache_a

expect_only_a_baseline_check() {
  local output
  output="$("${bazel[@]}" build --subcommands \
    //tests/baselines:baseline_cache_a \
    //tests/baselines:baseline_cache_b 2>&1)"
  if ! grep -F "baseline_cache_a_pyrefly_check.marker" <<<"$output" >/dev/null; then
    echo "Expected baseline_cache_a's Pyrefly check to rerun" >&2
    printf '%s\n' "$output" >&2
    exit 1
  fi
  if grep -F "baseline_cache_b_pyrefly_check.marker" <<<"$output" >/dev/null; then
    echo "baseline_cache_b's Pyrefly check reran after only baseline_cache_a changed" >&2
    printf '%s\n' "$output" >&2
    exit 1
  fi
}

baseline_a="pyrefly_baselines/tests/baselines/baseline_cache_a.json"
baseline_a_backup="$(mktemp)"
cp "$baseline_a" "$baseline_a_backup"
restore_baseline_a() {
  cp "$baseline_a_backup" "$baseline_a"
  rm -f "$baseline_a_backup"
}
trap restore_baseline_a EXIT

printf '{\n  "errors": []\n}\n' >"$baseline_a"
expect_only_a_baseline_check

rm "$baseline_a"
expect_only_a_baseline_check

printf '{"errors": [ ]}\n' >"$baseline_a"
expect_only_a_baseline_check

restore_baseline_a
trap - EXIT

update_aspect="//:pyrefly_aspects.bzl%pyrefly_update_baseline_aspect"
normal_update_actions="$("${bazel[@]}" aquery \
  'mnemonic("PyreflyUpdateBaseline", //tests/baselines:baselined_failure)' 2>&1)"
if grep -F "PyreflyUpdateBaseline" <<<"$normal_update_actions" >/dev/null; then
  echo "Normal builds unexpectedly contain baseline update actions" >&2
  printf '%s\n' "$normal_update_actions" >&2
  exit 1
fi

update_action="$("${bazel[@]}" aquery \
  --aspects="$update_aspect" \
  --include_artifacts \
  --output_groups=pyrefly_updated_baseline \
  'mnemonic("PyreflyUpdateBaseline", //tests/baselines:baselined_failure)' 2>&1)"
if grep -F "pyrefly_baselines/tests/baselines/baselined_failure.json" \
  <<<"$update_action" >/dev/null; then
  echo "Baseline update action unexpectedly depends on the checked-in baseline" >&2
  printf '%s\n' "$update_action" >&2
  exit 1
fi

run_baseline_updater() {
  BAZEL="$nested_bazel" "${bazel[@]}" run //pyrefly_baselines:baselines -- "$@"
}

updater_backup_dir="$(mktemp -d)"
cp pyrefly_baselines/tests/baselines/baselined_failure.json \
  "$updater_backup_dir/baselined_failure.json"
cp pyrefly_baselines/tests/baselines/baseline_cache_b.json \
  "$updater_backup_dir/baseline_cache_b.json"
restore_updater_fixtures() {
  cp "$updater_backup_dir/baselined_failure.json" \
    pyrefly_baselines/tests/baselines/baselined_failure.json
  cp "$updater_backup_dir/baseline_cache_b.json" \
    pyrefly_baselines/tests/baselines/baseline_cache_b.json
  rm -f \
    pyrefly_baselines/tests/baselines/clean.json \
    pyrefly_baselines/tests/baselines/failure.json \
    "$updater_backup_dir/baselined_failure.json" \
    "$updater_backup_dir/baseline_cache_b.json" \
    "$updater_backup_dir/target-patterns.txt"
  rmdir "$updater_backup_dir"
}
trap restore_updater_fixtures EXIT

printf '{"errors": [{"name": "stale-error"}]}\n' \
  >pyrefly_baselines/tests/baselines/baselined_failure.json
printf '{"errors": [{"name": "obsolete-clean-error"}]}\n' \
  >pyrefly_baselines/tests/baselines/clean.json
printf '%s\n' \
  //tests/baselines:baselined_failure \
  //tests/baselines:failure \
  //tests/baselines:clean \
  >"$updater_backup_dir/target-patterns.txt"
run_baseline_updater \
  --target_pattern_file="$updater_backup_dir/target-patterns.txt"

baselines_dir="pyrefly_baselines/tests/baselines"
generated_baseline="$bazel_bin/tests/baselines/baselined_failure_pyrefly_updated_baseline.json"
cmp "$generated_baseline" "$baselines_dir/baselined_failure.json"
cmp \
  "$bazel_bin/tests/baselines/failure_pyrefly_updated_baseline.json" \
  "$baselines_dir/failure.json"
test ! -e "$baselines_dir/clean.json"
cmp "$updater_backup_dir/baseline_cache_b.json" "$baselines_dir/baseline_cache_b.json"
"${bazel[@]}" build \
  //tests/baselines:baselined_failure \
  //tests/baselines:failure

update_build=(
  "${bazel[@]}"
  build
  --aspects="$update_aspect"
  --output_groups=pyrefly_updated_baseline
  --run_validations=false
  //tests/baselines:baselined_failure
)
"${update_build[@]}"
printf '{"errors": [{"name": "manually-edited"}]}\n' \
  >"$baselines_dir/baselined_failure.json"
cached_update_output="$("${update_build[@]}" --subcommands 2>&1)"
if grep -F "PyreflyUpdateBaseline" <<<"$cached_update_output" >/dev/null; then
  echo "Changing the checked-in baseline reran its from-scratch update action" >&2
  printf '%s\n' "$cached_update_output" >&2
  exit 1
fi
run_baseline_updater //tests/baselines:baselined_failure
cmp "$generated_baseline" "$baselines_dir/baselined_failure.json"

restore_updater_fixtures
trap - EXIT
