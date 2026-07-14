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

## Scenario invariants

- Scenario names and all phase descriptions are non-empty strings.
- `then` is mandatory and every executable phase has a callable.
- Failures identify level, phase, scenario, and phase description.
- `catches()` captures ordinary `Exception` instances, never process-control exceptions such
  as `KeyboardInterrupt` or `SystemExit`.
- `@cases(table)` creates one pytest item per row. The inline `scenario_outline()` API remains
  available for compatibility, but a failure in one inline row prevents later rows from running.

The framework validates structure. It cannot prove that an arbitrary callback contains a
meaningful assertion; use `expect()` or ordinary Python assertions to express the invariant.
