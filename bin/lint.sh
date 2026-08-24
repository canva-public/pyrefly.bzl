#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repository_root="$(dirname "$script_dir")"
cd "$repository_root"

rg --files -0 -g '*.sh' -g '*.bash' -g '*.zsh' |
  xargs -0 "$repository_root/bin/shellcheck"
