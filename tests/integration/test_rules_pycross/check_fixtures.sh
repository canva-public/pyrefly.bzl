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
