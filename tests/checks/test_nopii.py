from orcaverify.checks.nopii import NoPII, NoSecrets


def test_nopii_flags_email():
    r = NoPII().check("contact me at john@acme.com")
    assert r.ok is False and "email" in r.reason


def test_nopii_does_not_echo_the_value():
    r = NoPII().check("john@acme.com")
    assert "john@acme.com" not in r.reason


def test_nopii_clean_passes():
    assert NoPII().check("no personal data here").ok


def test_nosecrets_flags_key():
    r = NoSecrets().check("key sk-ABCDEF0123456789ABCDEF0123")
    assert r.ok is False and "openai_key" in r.reason


def test_nosecrets_clean_passes():
    assert NoSecrets().check("nothing sensitive").ok
