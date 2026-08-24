#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repository_root="$(dirname "$script_dir")"
cd "$repository_root"

exec "$repository_root/bin/dprint" fmt
