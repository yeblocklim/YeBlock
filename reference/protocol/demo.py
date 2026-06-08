# SPDX-License-Identifier: Apache-2.0
#
# Status: first-phase reference excerpt (pre-alpha). Interfaces and protocol logic only,
# not the production implementation, and subject to change as the spec matures.
# Scope and rationale: reference/README.md.
"""YeBlock LIM - Walkthrough of the original protocol mechanisms.

Run it:

    python reference/protocol/demo.py

This exercises the three self-developed mechanisms end to end with worked examples, so the
logic is visible and checkable without any deployed system:

  1. economic_security  - why cheating is unprofitable, and how redundancy scales with value;
  2. routing            - how a confidential, high-value request picks its operator shard;
  3. royalty_waterfall  - how one inference's royalty flows, integer-exact, down a LoRA lineage.

Nothing here touches a network or a key. It is the protocol's logic, demonstrated.
"""

from __future__ import annotations

import os
import sys

# Make the module imports work no matter where the script is launched from.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import economic_security as es  # noqa: E402
import routing as rt  # noqa: E402
import royalty_waterfall as rw  # noqa: E402


def rule(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def demo_economic_security() -> None:
    rule("1 · Economic security - making cheating unprofitable in expectation")

    cheap = es.WorkloadEconomics(honest_cost=0.10, reward=0.30, stake_at_risk=5.0)
    pricey = es.WorkloadEconomics(honest_cost=2.00, reward=4.00, stake_at_risk=3.0)

    for name, w in (("low-value call", cheap), ("high-value call", pricey)):
        p_min = es.min_audit_probability(w)
        print(f"\n{name}:  c={w.honest_cost}  r={w.reward}  S={w.stake_at_risk}")
        print(f"  minimum audit rate p_min = c/(S+r) = {p_min:.4f}  ({p_min*100:.2f}% of tasks)")
        for p in (0.001, 0.03):
            adv = es.expected_cheating_advantage(w, p)
            verdict = "honest wins" if adv < 0 else "CHEATING PAYS - raise p or stake"
            print(f"  at audit rate {p:>5}: E[cheat advantage] = {adv:+.4f}  -> {verdict}")
        k = es.recommended_redundancy(w, base_audit_prob=0.03)
        print(f"  recommended redundancy at 3% sampling: k = {k} replica(s)")

    print("\n  takeaway: the high-value call has a higher p_min, so the protocol")
    print("  automatically cross-checks it on more operators. Value drives redundancy.")


def demo_routing() -> None:
    rule("2 · Routing - reputation-weighted, latency-aware, TEE-eligible shard selection")

    operators = [
        rt.Operator("op-a", reputation=0.95, price_per_1k_tokens=0.06, est_latency_ms=180,
                    stake=50, vram_gb=24, has_tee=True, region="us-east"),
        rt.Operator("op-b", reputation=0.80, price_per_1k_tokens=0.04, est_latency_ms=600,
                    stake=20, vram_gb=24, has_tee=False, region="eu-west"),
        rt.Operator("op-c", reputation=0.99, price_per_1k_tokens=0.05, est_latency_ms=220,
                    stake=80, vram_gb=24, has_tee=True, region="us-east"),
        rt.Operator("op-d", reputation=0.70, price_per_1k_tokens=0.03, est_latency_ms=300,
                    stake=5, vram_gb=12, has_tee=False, region="us-east"),
    ]

    workload = es.WorkloadEconomics(honest_cost=2.0, reward=4.0, stake_at_risk=3.0)
    req = rt.RoutingRequest(
        min_vram_gb=16,
        workload=workload,
        confidential=True,           # medical/legal/financial tier → TEE required
        preferred_region="us-east",
        stake_floor=10,
    )

    print("\n  request: confidential=True, min_vram=16GB, stake_floor=10, region=us-east")
    print("\n  per-operator score (eligible only, best first):")
    for op, score in rt.score_operators(operators, req):
        print(f"    {op.identity}: score={score:.3f}  rep={op.reputation} "
              f"price={op.price_per_1k_tokens} lat={op.est_latency_ms}ms tee={op.has_tee}")

    decision = rt.route(operators, req)
    print(f"\n  chosen shard: {[o.identity for o in decision.shard]}  (k={decision.redundancy})")
    print("  rejected:")
    for ident, reason in decision.rejected.items():
        print(f"    {ident}: {reason}")


def demo_royalty_waterfall() -> None:
    rule("3 · Royalty waterfall - integer-exact distribution down a LoRA lineage")

    registry = {
        "lora-legal": rw.Manifest(
            artifact="lora-legal", author="alice",
            splits=(("alice", 8000), ("lp-pool", 2000)),
            parents=("lora-formal",), parent_share_bps=2500,   # 25% flows upstream
        ),
        "lora-formal": rw.Manifest(
            artifact="lora-formal", author="bob",
            splits=(("bob", 10000),),
            parents=("lora-base-style",), parent_share_bps=1000,  # 10% flows upstream
        ),
        "lora-base-style": rw.Manifest(
            artifact="lora-base-style", author="carol",
            splits=(("carol", 10000),),
        ),
    }

    gross = 1_000_003  # deliberately odd, to show no rounding leak
    print("\n  lineage: lora-legal  --derives from-->  lora-formal  --derives from-->  lora-base-style")
    print("  shares : legal keeps 75% (alice 80% / lp 20%), sends 25% up;")
    print("           formal keeps 90% (bob), sends 10% up; base-style: carol 100%")
    print(f"\n  gross royalty for one settlement = {gross:,} units")

    payouts = rw.distribute("lora-legal", gross, registry)
    print("\n  payouts:")
    for ident, amt in sorted(payouts.items(), key=lambda t: -t[1]):
        print(f"    {ident:<16} {amt:>12,}  ({amt / gross * 100:5.2f}%)")

    total = sum(payouts.values())
    print(f"\n  sum of payouts = {total:,}")
    print(f"  exactly equals gross? {total == gross}  <- no value created or lost")


def main() -> None:
    print("YeBlock LIM - original protocol mechanisms, demonstrated")
    demo_economic_security()
    demo_routing()
    demo_royalty_waterfall()
    print("\n" + "=" * 70)
    print("done. every number above is computed by the reference modules in this folder.")
    print("=" * 70)


if __name__ == "__main__":
    main()
