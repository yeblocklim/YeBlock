# SPDX-License-Identifier: Apache-2.0
#
# Status: first-phase reference excerpt (pre-alpha). Interfaces and protocol logic only,
# not the production implementation, and subject to change as the spec matures.
# Scope and rationale: reference/README.md.
"""YeBlock LIM - Walkthrough of the original protocol mechanisms.

Run it:

    python reference/protocol/demo.py

This exercises the self-developed mechanisms end to end with worked examples, so the
logic is visible and checkable without any deployed system:

  1. economic_security  - why cheating is unprofitable, and how redundancy scales with value;
  2. routing            - how a confidential, high-value request picks its operator shard;
  3. royalty_waterfall  - how one inference's royalty flows, integer-exact, down a LoRA lineage;
  4. idea_market        - YeBlock LIME: escrow-conserving settlement of an AI+human pipeline,
                          and perpetual revenue down an idea lineage;
  5. energy_market      - YeBlock LEM: energy-aware batch routing, trustless hosting splits,
                          and cross-checked JouleCredit minting;
  6. payment_rail       - YeBlock LIP: streaming pay, policy-bounded agent wallets, and
                          atomic receipt-anchored A2A clearing.

Nothing here touches a network or a key. It is the protocol's logic, demonstrated.
"""

from __future__ import annotations

import os
import sys

# Make the module imports work no matter where the script is launched from.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import economic_security as es  # noqa: E402
import energy_market as em  # noqa: E402
import idea_market as im  # noqa: E402
import payment_rail as pr  # noqa: E402
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


def demo_idea_market() -> None:
    rule("4 · YeBlock LIME idea market - escrow-conserving AI+human pipeline settlement")

    capsule = im.IdeaCapsule(
        capsule_id="idea-petcare-app", author="dana",
        ask=1_000_000, royalty_bps=1_500,  # author keeps 15% of escrow above step fees
    )
    steps = [
        im.TaskStep("step-market-research", im.StepKind.MACHINE, "op-a", fee=120_000),
        im.TaskStep("step-mvp-build", im.StepKind.MACHINE, "op-c", fee=300_000),
        im.TaskStep("step-vet-signoff", im.StepKind.HUMAN, "human-vet", fee=150_000, stake=50_000),
        im.TaskStep("step-field-photos", im.StepKind.HUMAN, "human-photog", fee=80_000,
                    stake=30_000, qa_passed=False),  # non-delivery → slashed
    ]
    escrow = capsule.ask

    print(f"\n  capsule '{capsule.capsule_id}' by {capsule.author}: escrow = {escrow:,}")
    print("  pipeline: 2 machine steps + 2 reverse-hired human steps (1 fails QA)")

    s = im.settle_execution(capsule, steps, escrow)
    print("\n  payouts:")
    for ident, amt in sorted(s.payouts.items(), key=lambda t: -t[1]):
        print(f"    {ident:<16} {amt:>10,}")
    print(f"  funder refund (residual + slashes): {s.funder_refund:,}")
    for ident, amt in s.slashed.items():
        print(f"  slashed: {ident} loses stake {amt:,} -> flows to the escrow side")
    total_stakes_slashed = sum(s.slashed.values())
    print(f"\n  conservation: payouts + refund = {s.total_disbursed():,}"
          f"  == escrow + slashed stakes = {escrow + total_stakes_slashed:,}"
          f"  -> {s.total_disbursed() == escrow + total_stakes_slashed}")

    # Perpetual revenue down an idea lineage (a derivative idea keeps paying its ancestor).
    capsules = {
        "idea-petcare-app": capsule,
        "idea-petcare-pro": im.IdeaCapsule(
            capsule_id="idea-petcare-pro", author="erik",
            ask=0, royalty_bps=0, parents=("idea-petcare-app",),
        ),
    }
    gross = 500_001
    rev = im.idea_revenue("idea-petcare-pro", gross, capsules)
    print(f"\n  derivative 'idea-petcare-pro' earns {gross:,} downstream:")
    for ident, amt in sorted(rev.items(), key=lambda t: -t[1]):
        print(f"    {ident:<8} {amt:>10,}  ({amt / gross * 100:5.2f}%)")
    print(f"  sum == gross? {sum(rev.values()) == gross}  <- same waterfall LoRAs use")


def demo_energy_market() -> None:
    rule("5 · YeBlock LEM energy mesh - energy-aware routing, hosting splits, JouleCredits")

    operators = [
        rt.Operator("op-hydro", reputation=0.85, price_per_1k_tokens=0.05, est_latency_ms=900,
                    stake=40, vram_gb=24, region="quebec"),
        rt.Operator("op-urban", reputation=0.90, price_per_1k_tokens=0.05, est_latency_ms=150,
                    stake=40, vram_gb=24, region="us-east"),
    ]
    profiles = {
        "op-hydro": em.EnergyProfile(energy_cost_per_kwh=0.02, carbon_intensity=20,
                                     in_surplus_window=True),
        "op-urban": em.EnergyProfile(energy_cost_per_kwh=0.18, carbon_intensity=400),
    }
    workload = es.WorkloadEconomics(honest_cost=0.5, reward=1.0, stake_at_risk=10.0)
    req = rt.RoutingRequest(min_vram_gb=16, workload=workload, stake_floor=10)

    print("\n  op-hydro: cheap clean power (0.02/kWh, 20g CO2, surplus window) but 900ms away")
    print("  op-urban: expensive grid (0.18/kWh, 400g CO2) but 150ms close")
    for cls in ("interactive", "batch"):
        scored = em.energy_aware_scores(operators, profiles, req, latency_class=cls)
        winner = scored[0][0].identity
        print(f"    {cls:<12} winner: {winner}"
              f"  ({'latency dominates' if cls == 'interactive' else 'energy signals applied'})")

    gross = 1_000_001
    hw, en = em.split_hosting_revenue(gross, hardware_bps=6_000)
    print(f"\n  hosting split of {gross:,} at 60/40: hardware={hw:,} energy={en:,}"
          f"  sum-exact? {hw + en == gross}")

    primary = em.MeterReading("meter-1", joules=3_600_000)
    honest_checks = [em.MeterReading("meter-2", 3_590_000), em.MeterReading("meter-3", 3_605_000)]
    ok, mintable = em.validate_attestation(primary, honest_checks)
    print(f"\n  honest attestation: accepted={ok}, mintable={mintable:,} J (min of claim vs corroboration)")
    liar = em.MeterReading("meter-1", joules=5_000_000)
    ok2, _ = em.validate_attestation(liar, honest_checks)
    print(f"  over-report 5.0 MJ vs ~3.6 MJ corroborated: accepted={ok2} -> 'energy-over-report' slash")
    deterred = em.over_report_unprofitable(
        credit_value=100.0, metering_cost=80.0, stake_at_risk=500.0, detection_prob=0.5)
    print(f"  cheating unprofitable at 50% redundant-meter coverage? {deterred}")


def demo_payment_rail() -> None:
    rule("6 · YeBlock LIP payment rail - streaming pay, agent wallets, atomic A2A clearing")

    stream = pr.PaymentStream("stream-1", payer="agent-buyer", payee="op-a",
                              rate_per_unit=3, unit=pr.StreamUnit.TOKENS)
    a1 = stream.checkpoint(12_000, receipt="rcpt-chunk-1")
    a2 = stream.close(8_000, final_receipt="rcpt-chunk-2")
    print(f"\n  stream: 12,000 tokens -> {a1:,} units, then 8,000 tokens + close -> {a2:,} units")
    print(f"  settled total = {stream.settled_total:,}  open = {stream.open}  (paused == settled)")

    rail = pr.Rail(fee_bps=30, burn_share_bps=5_000)
    rail.set_policy(pr.WalletPolicy(
        owner="alice", agent="agent-buyer",
        per_call_limit=50_000, daily_limit=100_000,
        allowlist=frozenset({"op-a", "agent-researcher"}),
    ))

    rail.clear(pr.Payment("agent-buyer", "op-a", 36_000, receipt="rcpt-chunk-1"))
    print("\n  cleared 36,000 to op-a within policy")
    for bad, label in (
        (pr.Payment("agent-buyer", "op-a", 60_000, "rcpt-x"), "per-call limit"),
        (pr.Payment("agent-buyer", "shady-svc", 1_000, "rcpt-y"), "allowlist"),
        (pr.Payment("agent-buyer", "op-a", 1_000, "rcpt-chunk-1"), "receipt re-use"),
    ):
        try:
            rail.clear(bad)
        except pr.PaymentError as e:
            print(f"  rejected ({label}): {e}")

    pipeline = [
        pr.Payment("agent-buyer", "agent-researcher", 10_000, "rcpt-p1"),
        pr.Payment("agent-researcher", "op-a", 4_000, "rcpt-p2"),
    ]
    rail.clear_batch(pipeline)
    gross = 36_000 + 10_000 + 4_000
    print(f"\n  pipeline batch cleared atomically; burned={rail.burned:,} treasury={rail.treasury:,}")
    print(f"  conservation (balances + burned + treasury == gross cleared)? "
          f"{rail.conservation_check(gross)}")


def main() -> None:
    print("YeBlock LIM - original protocol mechanisms, demonstrated")
    demo_economic_security()
    demo_routing()
    demo_royalty_waterfall()
    demo_idea_market()
    demo_energy_market()
    demo_payment_rail()
    print("\n" + "=" * 70)
    print("done. every number above is computed by the reference modules in this folder.")
    print("=" * 70)


if __name__ == "__main__":
    main()
