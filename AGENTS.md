# Repository instructions

All agents must follow the project contribution guidelines in [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Starlark

- Preserve depsets through analysis and avoid `depset.to_list()` in production code. Prefer
  depset-aware APIs such as `Args.add_all`; only flatten a depset when an API genuinely requires
  materialized values, such as test assertions.

## Formatting and linting

- Format supported files with `bin/format.sh`.
- Run `bin/lint.sh` and resolve all findings.
- Run all tests with `bin/test.sh`.
