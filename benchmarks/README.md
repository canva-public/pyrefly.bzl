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

Add `--warm-dependencies` to measure rechecks with dependency outputs already built. Initial
dependency generation and minification are excluded.

Each JSON line reports one scenario. Timing fields use `min_`, `median_`, `max_` and `stddev_`
prefixes for statistics across repetitions. `stddev_` is the population standard deviation, zero for
one repetition:

- `*_action_seconds`: summed action execution time, including Pyrefly and its wrapper.
- `*_pyrefly_seconds`: Pyrefly subprocess time from OTLP traces.
- `*_wrapper_seconds`: remaining action time, including Python startup and shutdown.
- `*_command_wall_seconds`: elapsed Bazel build time, including analysis and sandbox setup.
- `summary`: path to the JSON report with per-action timings and paths to logs and OTLP traces.

Action timings are in seconds and summed across actions per repetition, after a warm-up. They
exclude Bazel analysis and dependency downloads; command wall times include the whole build.
Statistics are calculated independently. Missing trace timing produces null breakdown statistics;
malformed trace files cause an error. Compare runs using the same settings and environment.
