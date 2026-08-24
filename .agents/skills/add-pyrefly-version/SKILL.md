---
name: add-pyrefly-version
description: Add support for an explicit, loosely formatted, or latest Pyrefly release in this repository by resolving its canonical GitHub tag, fetching its four supported platform SHA-256 digests, and updating pyrefly/private/versions.bzl. Use when asked to support, register, bump, or add a Pyrefly version.
---

# Add Pyrefly Version

1. Read `AGENTS.md` and `CONTRIBUTING.md`, then inspect `git status` to preserve unrelated changes.
2. Resolve the user's request to a canonical upstream release tag before fetching checksums.

   Pyrefly tags use these forms:

   - Stable release: `MAJOR.MINOR.PATCH`, for example `1.2.0`.
   - Development release: `MAJOR.MINOR.PATCH-dev.N`, for example `1.3.0-dev.2`.
   - Never retain a leading `v`.

   Normalise common inputs such as `v1.3.0-dev.2`, `1.3.0.dev2`, and `1.3.0-dev2` to `1.3.0-dev.2`.
   Change only the spelling and punctuation; never infer different numeric components.

   If the user requests the "latest" version, resolve the most recently published non-draft GitHub
   release, including prereleases:

   ```shell
   gh api 'repos/facebook/pyrefly/releases?per_page=100' \
     --jq 'map(select(.draft == false)) | max_by(.published_at) | .tag_name'
   ```

   Confirm the canonical tag exists with:

   ```shell
   gh api repos/facebook/pyrefly/releases/tags/<canonical-tag> --jq .tag_name
   ```

   If it does not exist, inspect the available tags rather than guessing another version.
3. From the repository root, run:

   ```shell
   .agents/skills/add-pyrefly-version/scripts/fetch-release-checksums.sh <canonical-tag>
   ```

   The script is read-only and prints a complete Starlark entry using GitHub's reported artifact
   digests.
4. Confirm that the canonical version is not already present in `PYREFLY_RELEASES`, then insert the
   printed entry near the top of `pyrefly/private/versions.bzl`. Keep the script read-only; make the
   edit yourself so the fetched values can be reviewed first.
5. Run `bin/format.sh`, `bin/lint.sh`, and `bin/test.sh`.
6. Report the changed file and validation results. Do not commit or push unless explicitly
   requested.
