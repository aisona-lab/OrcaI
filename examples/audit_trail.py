"""Provenance demo — a tamper-evident audit trail for every verification.

Wire Provenance in as the Verifier's sink. Every decision is hash-chained.
Then we tamper with the log and watch .verify() catch it.

Run: python examples/audit_trail.py
"""

from orcaverify import NoPII, Provenance, Verifier
from orcaverify.provenance.store import InMemoryStore


def main():
    store = InMemoryStore()
    prov = Provenance(store)

    gate = Verifier([NoPII()], sink=prov)
    gate.run(lambda feedback=None: "clean report A")
    gate.run(lambda feedback=None: "leaked john@acme.com")  # fails NoPII, still logged

    print("Records:", len(prov.records()))
    print("Chain valid:", prov.verify().ok)

    # Someone edits a past decision in the log...
    store.read()[0]["payload"]["decision"] = "rejected"
    result = prov.verify()
    print("After tampering -> valid:", result.ok, "| broken at:", result.broken_at)


if __name__ == "__main__":
    main()
