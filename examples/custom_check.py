"""Registry demo — register your own check, then build a Verifier from config.

This is how the community extends Orca: write a Check, register it by name,
compose it from a config dict (or expose it via entry points so it auto-loads).

Run: python examples/custom_check.py
"""

from orcaverify import Check, CheckResult, from_config, register


@register("max_length")
class MaxLength(Check):
    """Fail if the output is longer than `limit` characters."""

    name = "max_length"

    def __init__(self, limit: int = 280):
        self.limit = limit

    def check(self, output, context=None):
        n = len(str(output))
        if n <= self.limit:
            return CheckResult(ok=True)
        return CheckResult(ok=False, reason=f"too long: {n} > {self.limit} chars")


def main():
    config = {
        "checks": [
            "no_pii",
            {"max_length": {"limit": 20}},
        ],
        "on_fail": "reject",
    }
    gate = from_config(config)

    print("Short, clean ->", gate.run(lambda feedback=None: "all good").decision)
    long_out = gate.run(lambda feedback=None: "this text is definitely way too long to pass")
    print("Too long     ->", long_out.decision)
    for f in long_out.failures:
        print("   reason:", f.reason)


if __name__ == "__main__":
    main()
