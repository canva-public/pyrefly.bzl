#!/usr/bin/env bash

set -euo pipefail

readonly github_repository="facebook/pyrefly"
readonly -a platforms=(
  "linux_aarch64"
  "linux_x86_64"
  "macos_aarch64"
  "macos_x86_64"
)
readonly -a assets=(
  "pyrefly-linux-arm64-musl.tar.gz"
  "pyrefly-linux-x86_64-musl.tar.gz"
  "pyrefly-macos-arm64.tar.gz"
  "pyrefly-macos-x86_64.tar.gz"
)

usage() {
  echo "Usage: $0 <pyrefly-version>" >&2
}

if [[ $# -ne 1 ]]; then
  usage
  exit 2
fi

readonly version="$1"
if [[ ! "$version" =~ ^[0-9A-Za-z][0-9A-Za-z._-]*$ ]]; then
  echo "Invalid Pyrefly version: $version" >&2
  exit 2
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "The gh CLI is required." >&2
  exit 1
fi

readonly release_api_path="repos/${github_repository}/releases/tags/${version}"
release_assets="$(
  gh api "$release_api_path" \
    --jq '.assets[] | [.name, (.digest // "")] | @tsv'
)"

declare -a digests=()
for asset in "${assets[@]}"; do
  match="$(
    awk -F $'\t' -v expected_asset="$asset" \
      '$1 == expected_asset { count++; digest = $2 } END { printf "%d\t%s", count, digest }' \
      <<<"$release_assets"
  )"
  match_count="${match%%$'\t'*}"
  digest="${match#*$'\t'}"

  if [[ "$match_count" -ne 1 ]]; then
    echo "Expected exactly one release asset named $asset; found $match_count." >&2
    exit 1
  fi
  if [[ ! "$digest" =~ ^sha256:[0-9a-f]{64}$ ]]; then
    echo "Release asset $asset has no valid SHA-256 digest: ${digest:-(empty)}" >&2
    exit 1
  fi

  digests+=("${digest#sha256:}")
done

printf 'GitHub release: https://github.com/%s/releases/tag/%s\n\n' \
  "$github_repository" "$version"
printf 'Insert this entry near the top of PYREFLY_RELEASES:\n\n'
printf '    "%s": {\n' "$version"
for index in "${!platforms[@]}"; do
  printf '        "%s": "%s",\n' "${platforms[$index]}" "${digests[$index]}"
done
printf '    },\n'
