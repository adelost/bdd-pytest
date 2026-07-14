# bdd-pytest contract

The plugin can enforce two independent contracts:

1. Every collected test has exactly one of `unit`, `component`, `integration`, or `e2e`.
2. Every successful test has either a non-empty function docstring or executes at least one
   validated `scenario()` / `scenario_outline()`.

Enable both as errors in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
bdd_level_policy = "error"
bdd_documentation_policy = "error"
```

Each policy accepts `off`, `warn`, or `error`. The command-line options
`--bdd-level-policy` and `--bdd-documentation-policy` override configuration.

The policy names match `bdd-vitest`. Defaults differ deliberately: this pytest plugin auto-loads
when installed, so its migration-safe defaults are level `warn` and documentation `off`. A strict
repository should set both to `error`. Level validation happens after marker deselection and only
applies to the items pytest will execute.

## Scenario invariants

- Scenario names and all phase descriptions are non-empty strings.
- `then` is mandatory and every executable phase has a callable.
- Failures identify level, phase, scenario, and phase description.
- Cleanup always runs. A cleanup-only failure is phase-tagged; if behavior and cleanup both fail,
  `ScenarioCleanupError` retains both and does not mask the primary failure.
- `catches()` captures ordinary `Exception` instances, never process-control exceptions such
  as `KeyboardInterrupt` or `SystemExit`.
- `@cases(table)` requires unique, non-empty row names and creates one pytest item per row.
- The strict `scenario_outline()` form describes every executable phase with a
  `(description, callable)` tuple. Callable-only outlines remain compatible but are marked
  undocumented; mixed forms are rejected. A failure in one inline row prevents later rows from
  running.

## Report metadata

Every executed item publishes `bdd.level` and `bdd.documentation` through pytest
`user_properties`. Items that execute scenarios also publish `bdd.scenarios`, a JSON array of
validated scenario names and phase descriptions. These properties are included in JUnit XML and
are the stable integration surface for documentation tooling. Scenario records include a
`documented` boolean matching the equivalent `bdd-vitest` metadata field.

The framework validates structure. It cannot prove that an arbitrary callback contains a
meaningful assertion; use `expect()` or ordinary Python assertions to express the invariant.
