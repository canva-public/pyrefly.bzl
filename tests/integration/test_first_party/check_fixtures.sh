#!/usr/bin/env bash

set -euo pipefail

fixture_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$fixture_dir"

bazel=(
  "${BIT_BAZEL_BINARY:-bazel}"
  "--nohome_rc"
  "--nosystem_rc"
)
if [[ -n "${TEST_TMPDIR:-}" ]]; then
  bazel+=("--output_user_root=$TEST_TMPDIR/bazel")
fi

"${bazel[@]}" test //...

warning_target=//tests/checking/expected_failure:consumer
warning_path=tests/checking/expected_failure

test_trace_requests_keep_warning_display_disabled() {
  # Requesting traces alone does not execute warning-display actions or print findings.
  local output
  output="$("${bazel[@]}" build \
    --color=no --curses=no --subcommands --show_result=20 \
    --output_groups=pyrefly_otlp_traces \
    "$warning_target" 2>&1)"
  if ! grep -E '^  .*consumer_pyrefly_check_otlp_trace.jsonl$' <<<"$output" >/dev/null || \
    grep -E 'PyreflyDisplayWarnings|_pyrefly_display_warnings|bad-assignment' \
      <<<"$output" >/dev/null; then
    echo "Requesting traces did not return check traces without displaying warnings" >&2
    printf '%s\n' "$output" >&2
    exit 1
  fi
}

test_warning_parameter_displays_checked_dependencies() {
  # Warning display includes both requested targets and their checked dependencies.
  local output
  output="$("${bazel[@]}" build \
    --color=no --curses=no --subcommands \
    --aspects_parameters=pyrefly_display_warnings=true \
    "$warning_target" 2>&1)"
  if ! grep -F "$warning_path/consumer.py:1:" <<<"$output" >/dev/null || \
    ! grep -F "$warning_path/fixture.py:1:" <<<"$output" >/dev/null; then
    echo "Warning display did not print findings for the target and its dependency" >&2
    printf '%s\n' "$output" >&2
    exit 1
  fi
}

test_enabled_warning_traces_are_returned_only_for_requested_targets() {
  # Enabled warning-display traces are returned only for requested targets.
  local output
  output="$("${bazel[@]}" build \
    --color=no --curses=no --subcommands --show_result=20 \
    --aspects_parameters=pyrefly_display_warnings=true \
    --output_groups=pyrefly_otlp_traces \
    "$warning_target" 2>&1)"
  if ! grep -E '^  .*consumer_pyrefly_display_warnings_otlp_trace.jsonl$' \
    <<<"$output" >/dev/null || \
    grep -E '^  .*fixture_pyrefly_display_warnings_otlp_trace.jsonl$' \
      <<<"$output" >/dev/null; then
    echo "Warning traces did not include only the requested target's warning display" >&2
    printf '%s\n' "$output" >&2
    exit 1
  fi
}

test_trace_requests_keep_warning_display_disabled
test_warning_parameter_displays_checked_dependencies
test_enabled_warning_traces_are_returned_only_for_requested_targets
