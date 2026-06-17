from orcaverify.cli import main


def test_checks_lists_names(capsys):
    assert main(["checks"]) == 0
    out = capsys.readouterr().out
    assert "no_pii" in out  # offline check, unmarked
    assert "grounded *" in out  # judge-requiring check, marked
