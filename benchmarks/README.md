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

The `materialisation` scenario generates 1,000 import roots contributing 40,000 stub modules to the
same five-level namespace package, `application.service.src.python.common`. Its consumer checks
imports from the first and last roots through the normal Pyrefly aspect. The fixture is generated
during the build; the stub files are not checked in.

Measure repeated checks with those dependency transformations already built:

```shell
bazel run //benchmarks:run -- --scenario materialisation --warm-dependencies
```

`--warm-dependencies` prepares dependencies before the warm-up, then forces only check actions to
execute for each sample. The benchmark rejects samples which rerun dependency transformations. This
measures a recheck with cached dependency outputs; it excludes their initial generation and
minification. Without the flag, all scenarios continue to rerun check, stubgen and minify actions.

Each JSON line reports one scenario. Timing fields use `min_`, `median_`, `max_` and `stddev_`
prefixes for statistics across repetitions. `stddev_` is the population standard deviation, zero for
one repetition:

- `*_action_seconds`: summed action execution time, including Pyrefly and its wrapper.
- `*_pyrefly_seconds`: Pyrefly subprocess time from OTLP traces.
- `*_wrapper_seconds`: remaining action time, including Python startup and shutdown.
- `*_command_wall_seconds`: wall time of the whole measured Bazel build command, including analysis
  and sandbox setup. Preparation, warm-up and benchmark report processing are excluded.
- `warm_dependencies`: whether dependency transformations were cached during measurement.
- `summary`: path to the JSON report with per-action timings and paths to logs and OTLP traces.

Action timings are in seconds and summed across actions per repetition, after a warm-up. They
exclude Bazel analysis and dependency downloads; command wall times include the whole build.
Statistics are calculated independently. Missing trace timing produces null breakdown statistics;
malformed trace files cause an error. Compare runs using the same settings and environment.
