# Contributing

## Dev environment

Install the following tools:

- [`direnv`](https://direnv.net/docs/installation.html)
- [`dotslash`](https://dotslash-cli.com/)
- [Bazelisk](https://github.com/bazelbuild/bazelisk/blob/master/README.md)

Run `direnv allow` in the repo root.

## Formatting and linting

Apply standard formatting for all files:

```shell
format.sh
```

Run linters and resolve all findings:

```shell
lint.sh
```

## Tests

Run all tests:

```shell
test.sh
```

### Writing tests

Tests should describe and protect observable behaviour, not preserve the current implementation.
Name each test after the behaviour it validates, and add a brief docstring directly under every test
case describing that behaviour.

Keep each test focused on one contract so that a failure identifies what has broken. Split unrelated
assertions into separate cases, and avoid assertions about private helpers, obsolete flags, or
historical implementation choices unless they enforce a deliberate correctness or performance
guarantee.

Use the narrowest appropriate test layer:

- Wrapper tests validate command behaviour directly.
- Analysis tests validate Bazel-facing contracts such as action selection, providers, and output
  groups.
- Integration tests validate complete builds and real Pyrefly execution.
