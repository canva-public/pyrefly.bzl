# Import-view merge benchmark

Run all three synthetic layouts:

```shell
bazel run //benchmarks:merge_import_view -- --roots 500 --files-per-root 40 --repeats 5
```

Each layout contains the same number of distinct physical stub files (`roots × files-per-root`):

- `disjoint`: each root provides its own package, with files under `package_N/nested`.
- `overlapping`: all roots provide `shared/nested`, with different filenames in each root.
- `duplicate-physical-roots`: the disjoint layout, plus one symlink alias to each physical root.
  This doubles the number of import roots without adding files. Physical roots precede the aliases.

Use `--scenario disjoint`, `--scenario overlapping` or `--scenario duplicate-physical-roots` to run
one layout. All count arguments must be positive. With one root, the first two layouts measure the
merger's single-root shortcut.

Output is one JSON object per layout, suitable for saving as JSONL. Each object includes the fixture
configuration, median duration in seconds and individual samples. Each sample records its duration,
`entries_visited`, `directory_collisions`, `symlinks_created` and `fallback`. Counters include work
on intermediate links that are subsequently replaced. The command fails if merging falls back to the
original roots.

Only `merge_site_package_dirs` is timed. Fixture creation and cleanup are excluded. Every sample
builds a fresh merged destination, which is removed before the next sample; input roots are
preserved.

These are local, warm-cache measurements: fixtures are written immediately before timing, inputs are
reused across repetitions and filesystem caches are not cleared. Compare revisions using the same
machine, filesystem and arguments. These fixtures isolate merge shapes; they do not reproduce
Canva's dependency closure or predict its CI runtimes. The test target checks benchmark behaviour
without wall-clock performance assertions.
