from orcaverify.checks.predicate import Predicate


def test_predicate_bool():
    assert Predicate(lambda o, c: len(o) > 0).check("hi").ok


def test_predicate_tuple_reason():
    r = Predicate(lambda o, c: (False, "empty"), name="nonempty").check("")
    assert r.ok is False and r.reason == "empty" and r.meta["name"] == "nonempty"
