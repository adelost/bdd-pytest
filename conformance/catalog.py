"""Shared behavior used by the cross-harness ``bdd.run.v1`` equivalence gate."""

from bdd_pytest import expect, scenario, unit


@unit
def test_applies_discount_over_500kr():
    scenario(
        "applies discount over 500kr",
        given=("a cart totaling 600kr", lambda: 600),
        when=("applying a ten percent discount", lambda total: total * 0.9),
        then=("the total is 540kr", lambda result, _: expect(result).to_be(540)),
    )
