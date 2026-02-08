# bdd-pytest

Opinionated BDD for pytest. Your tests are your documentation.

```python
from bdd_pytest import unit, expect, scenario

@unit
def test_discount_over_500():
    scenario("applies discount over 500kr",
        given=("a cart with total 600kr",  lambda: create_cart(600)),
        when= ("checking out",            lambda cart: checkout(cart)),
        then= ("10% discount applied",    lambda res, _: expect(res.discount).to_be(60)),
    )
```

Read just the descriptions. You understand the system without opening production code.

## Why

Most test frameworks let you write `def test_something():` with no structure inside. AI agents (and tired humans) skip descriptions, skip assertions, write tests that pass but prove nothing.

bdd-pytest makes it impossible:

- **Descriptions are required.** Every phase is a `("description", fn)` tuple.
- **Levels are required.** No generic test. You must pick `@unit`, `@component`, `@integration`, or `@e2e`. Each has enforced timeouts.
- **Assertions are required.** `then` is mandatory. No test without a check.

## Install

```bash
pip install bdd-pytest
```

Requires `pytest-timeout>=2.0` (installed automatically).

## Levels

Every test must declare its level via decorator. Wrong level = timeout kills the test.

```python
from bdd_pytest import unit, component, integration, e2e
```

| Level | Timeout | Use for |
|-------|---------|---------|
| `@unit` | 100ms | Pure logic, no I/O |
| `@component` | 5s | Service in isolation, mocked deps |
| `@integration` | 30s | Multiple services, real deps |
| `@e2e` | 120s | Full system, browser, network |

Tests without a level decorator get a warning. Tests exceeding their timeout fail.

## Phases

`then` is always required. Everything else is optional:

```python
scenario("full",      given=..., when=..., then=...)   # setup -> action -> assert
scenario("no action", given=..., then=...)              # setup -> assert
scenario("no setup",  when=..., then=...)               # action -> assert
scenario("assertion", then=...)                         # just assert
```

No setup code? `given` can be just a description:

```python
@component
def test_health_check():
    scenario("returns 200",
        given="a running server",
        when= ("requesting /health", lambda _: client.get("/health")),
        then= ("status is 200",     lambda res, _: expect(res.status_code).to_be(200)),
    )
```

`when` receives `given`'s return value. `then` receives `(result, ctx)`:

```python
@unit
def test_fifo_order():
    scenario("processes in FIFO order",
        given=("a task queue",        lambda: TaskQueue()),
        when= ("enqueueing 1, 2, 3", lambda q: q.enqueue_all([1, 2, 3])),
        then= ("order preserved",    lambda result, _: expect(result).to_be([1, 2, 3])),
    )
```

Errors show which phase failed, with level prefix:

```
AssertionError: [unit/given] Database connection: connection refused
AssertionError: [unit/when] Request timeout: read timed out
AssertionError: [unit/then] status is 200: Expected 500 to be 200
```

## Cleanup

Resources that need teardown:

```python
@integration
def test_finds_user():
    scenario("finds user by email",
        given=  ("a seeded database", lambda: seed_test_db()),
        when=   ("querying",          lambda db: db.users.find_by(email="alice@test.com")),
        then=   ("returns Alice",     lambda user, _: expect(user.name).to_be("Alice")),
        cleanup=lambda db: db.destroy(),
    )
```

Cleanup runs even if the test fails.

## Table-driven

```python
from bdd_pytest import scenario_outline

@unit
def test_adds_numbers():
    scenario_outline("adds numbers", [
        {"name": "positives",  "a": 2,  "b": 3, "expected": 5},
        {"name": "negatives",  "a": -1, "b": 1, "expected": 0},
    ],
        given=lambda row: (row["a"], row["b"]),
        when= lambda ctx, row: ctx[0] + ctx[1],
        then= lambda result, ctx, row: expect(result).to_be(row["expected"]),
    )
```

Failures include row name: `[unit/then] adds numbers [negatives]: Expected -2 to be 0`.

## Grouping

Use pytest classes for nesting in test output:

```python
class TestCheckout:
    class TestDiscounts:
        @unit
        def test_applies_discount(self):
            scenario("applies 10% over 500kr",
                given=("a cart at 600kr", lambda: create_cart(600)),
                when= ("checking out",   lambda cart: checkout(cart)),
                then= ("discount is 60", lambda res, _: expect(res.discount).to_be(60)),
            )

        @unit
        def test_no_discount_under_500(self):
            scenario("no discount under 500kr",
                given=("a cart at 400kr", lambda: create_cart(400)),
                when= ("checking out",   lambda cart: checkout(cart)),
                then= ("discount is 0",  lambda res, _: expect(res.discount).to_be(0)),
            )
```

```
test_checkout.py::TestCheckout::TestDiscounts::test_applies_discount PASSED
test_checkout.py::TestCheckout::TestDiscounts::test_no_discount_under_500 PASSED
```

## expect()

Lambda-friendly assertions. Python's `assert` is a statement (can't use in lambdas), so `expect()` provides expressions that return `self` for chaining:

```python
expect(42).to_be(42)
expect(result).to_be_none()
expect(items).to_have_length(3)
expect(name).to_contain("Alice")
expect(value).to_be_truthy()
expect(score).to_be_greater_than(0.5)
expect(0.1 + 0.2).to_be_close_to(0.3)           # float comparison, default 7 decimal places
expect(depth).to_be_close_to(1.5, places=2)      # custom precision
expect(text).to_match(r"Error: \d+")
expect(obj).to_be_instance_of(User)
expect(lambda: bad()).to_raise(ValueError, match="invalid")
```

Negate with `.not_`:

```python
expect(42).not_.to_be(99)
expect(result).not_.to_be_none()
```

Multiple assertions in a lambda via tuple:

```python
then=("all correct", lambda res, _: (
    expect(res.status).to_be(200),
    expect(res.body).to_contain("ok"),
)),
```

## Testing exceptions

Use `catches()` to test that code raises:

```python
from bdd_pytest import catches

@unit
def test_rejects_negative():
    scenario("rejects negative amount",
        when= ("withdrawing -100", lambda _: catches(lambda: withdraw(-100))),
        then= ("raises ValueError",lambda err, _: (
            expect(err).to_be_instance_of(ValueError),
            expect(str(err)).to_contain("negative"),
        )),
    )
```

## Filtering

Level decorators double as pytest markers:

```bash
pytest -m unit               # only unit tests
pytest -m "not e2e"          # skip slow e2e tests
pytest -m "unit or component"
```

## API

| Export | What |
|--------|------|
| `@unit` / `@component` / `@integration` / `@e2e` | Test decorator with enforced timeout + marker |
| `scenario(name, *, given, when, then, cleanup)` | Inline Given/When/Then |
| `scenario_outline(name, table, *, given, when, then, cleanup)` | Table-driven scenarios |
| `expect(value)` | Lambda-friendly assertions |
| `catches(fn)` | Capture exception for assertion |

## License

MIT
