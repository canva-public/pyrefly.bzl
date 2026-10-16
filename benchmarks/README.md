# Pyrefly aspect benchmarks

Run all scenarios with five measured repetitions and one job:

```shell
bazel run //benchmarks:run
```

Choose a scenario, repetition count or output directory with arguments after `--`:

```shell
bazel run //benchmarks:run -- --scenario namespace --repeats 3 --output-dir /tmp/pyrefly-benchmarks
```

Use a new directory for `--output-dir`, or omit it to keep results in a temporary directory.

Each JSON line reports one scenario:

- `median_action_seconds`: median summed action execution time, including Pyrefly and its wrapper.
- `median_pyrefly_seconds`: median Pyrefly subprocess time from OTLP traces.
- `median_wrapper_seconds`: median remaining action time, including Python startup and shutdown.
- `summary`: path to the JSON report with per-action timings and paths to logs and OTLP traces.

Times are in seconds and summed across actions per repetition, after a warm-up. They exclude Bazel
analysis and dependency downloads. The medians are calculated independently; a null breakdown means
trace timing was unavailable. Compare runs using the same settings and environment.
