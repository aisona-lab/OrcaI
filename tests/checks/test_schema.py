from pydantic import BaseModel

from orcaverify.checks.schema import Schema


class Report(BaseModel):
    title: str
    score: int


def test_schema_passes_valid():
    assert Schema(Report).check({"title": "a", "score": 1}).ok


def test_schema_passes_model_instance():
    assert Schema(Report).check(Report(title="a", score=1)).ok


def test_schema_fails_invalid_and_explains():
    r = Schema(Report).check({"title": "a"})
    assert r.ok is False and "score" in r.reason
