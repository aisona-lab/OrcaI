from __future__ import annotations

from pydantic import BaseModel, ValidationError

from orcaverify.checks.base import Check, CheckResult


class Schema(Check):
    """Validate the output against a Pydantic model."""

    name = "schema"

    def __init__(self, model: type[BaseModel]):
        self.model = model

    def check(self, output, context=None) -> CheckResult:
        data = output.model_dump() if isinstance(output, BaseModel) else output
        try:
            self.model.model_validate(data)
            return CheckResult(ok=True)
        except ValidationError as e:
            return CheckResult(ok=False, reason=str(e))
