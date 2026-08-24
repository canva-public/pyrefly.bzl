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

if output="$("${bazel[@]}" build "${EXPECTED_TARGET:?}" 2>&1)"; then
  echo "Expected $EXPECTED_TARGET to fail" >&2
  exit 1
fi

if [[ -n "${EXPECTED_OUTPUT:-}" ]] && ! grep -F -- "$EXPECTED_OUTPUT" <<<"$output" >/dev/null; then
  echo "Expected $EXPECTED_TARGET output to contain: $EXPECTED_OUTPUT" >&2
  printf '%s\n' "$output" >&2
  exit 1
fi
