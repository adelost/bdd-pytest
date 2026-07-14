from bdd_pytest import expect, scenario, unit


@unit
def test_runs_from_the_installed_package():
    scenario(
        "runs from the installed package",
        given=("an installed public API", lambda: 21),
        when=("using the packaged runner", lambda value: value * 2),
        then=("the packaged result is correct", lambda result, _: expect(result).to_be(42)),
    )
