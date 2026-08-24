#!/usr/bin/env bash

set -euo pipefail

output="$1"
shift

copy_file() {
  local input="$1"
  while IFS= read -r line || [[ -n "$line" ]]; do
    printf '%s\n' "$line"
  done <"$input"
}

copy_symbol() {
  local input="$1"
  local started=""
  while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ -z "$started" && "$line" == "<a id="* ]]; then
      started="true"
    fi
    if [[ -n "$started" ]]; then
      printf '%s\n' "$line"
    fi
  done <"$input"
}

strip_trailing_blank_lines() {
  awk '
    /^[[:space:]]*$/ {
      blanks = blanks $0 ORS
      next
    }
    {
      printf "%s", blanks
      blanks = ""
      print
    }
  '
}

first="$1"
shift
{
  copy_file "$first"
  for input in "$@"; do
    copy_symbol "$input"
  done
} | strip_trailing_blank_lines >"$output"
