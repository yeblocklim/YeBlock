# SPDX-License-Identifier: Apache-2.0
#
# Status: first-phase reference excerpt (pre-alpha). Interfaces and protocol logic only,
# not the production implementation, and subject to change as the spec matures.
# Scope and rationale: reference/README.md.
"""YeBlock LIM - Reputation-weighted, latency-aware routing (original mechanism design).

Pillar 1 (Compute). The matcher that turns a global pool of heterogeneous, untrusted operators
into a usable inference service is the protocol's own design - there is no off-the-shelf
algorithm for "route LoRA-composed inference to the cheapest *qualified* operator, with as much
redundancy as the workload's economics demand". This module implements it end to end.

It composes with the rest of the protocol:
  - eligibility uses the on-chain stake floor   (IStakeVault, invariant I-7);
  - the privacy tier constrains the operator set (confidential ⇒ TEE-attested only, Pillar 4);
  - the redundancy factor comes from economic_security.recommended_redundancy (this package);
  - the chosen shard then executes against composition.py / receipts.py.

Selection is deterministic given the same inputs, so routing decisions are auditable after the
fact - anyone can replay why a given shard was chosen.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from economic_security import WorkloadEconomics, recommended_redundancy

Identity = str


@dataclass(frozen=True)
class Operator:
    identity: Identity
    reputation: float  # [0,1]; long-run honesty × SLA × volume score
    price_per_1k_tokens: float  # quoted price (settlement units)
    est_latency_ms: float  # recent p50 first-token latency to the request region
    stake: float  # locked collateral (settlement units)
    vram_gb: int  # hardware class
    has_tee: bool = False  # TEE-attested (Intel TDX / AMD SEV-SNP / H100 CC)
    region: str = "unknown"


@dataclass(frozen=True)
class RoutingRequest:
    min_vram_gb: int  # base + LoRA stack working-set requirement
    workload: WorkloadEconomics  # economics for the redundancy decision
    confidential: bool = False  # privacy tier: requires TEE operators
    preferred_region: str | None = None  # latency bias, not a hard filter
    stake_floor: float = 0.0  # minimum stake to be eligible (from governance/contract)


@dataclass(frozen=True)
class RoutingWeights:
    """Scoring weights. Sum is irrelevant (scores are only compared, never thresholded)."""

    reputation: float = 0.5
    price: float = 0.3
    latency: float = 0.2


@dataclass
class RoutingDecision:
    shard: list[Operator] = field(default_factory=list)  # chosen operators, best-first
    redundancy: int = 1
    rejected: dict[Identity, str] = field(default_factory=dict)  # identity → reason


def _eligible(op: Operator, req: RoutingRequest) -> str | None:
    """Return None if eligible, else a human-readable rejection reason."""
    if op.vram_gb < req.min_vram_gb:
        return "insufficient-vram"
    if op.stake < req.stake_floor:
        return "below-stake-floor"
    if req.confidential and not op.has_tee:
        return "tee-required"
    return None


def _normalize(values: list[float]) -> list[float]:
    """Min-max normalize to [0,1]; a flat list maps to all-zeros (no signal in that axis)."""
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.0] * len(values)
    span = hi - lo
    return [(v - lo) / span for v in values]


def score_operators(
    operators: list[Operator],
    req: RoutingRequest,
    weights: RoutingWeights = RoutingWeights(),
) -> list[tuple[Operator, float]]:
    """Score eligible operators; higher is better. Price and latency are penalties (lower is
    better, so we use 1 - normalized), reputation is a reward. A small region bonus rewards
    co-location without hard-filtering distant operators out."""
    eligible = [op for op in operators if _eligible(op, req) is None]
    if not eligible:
        return []

    prices = _normalize([op.price_per_1k_tokens for op in eligible])
    latencies = _normalize([op.est_latency_ms for op in eligible])

    scored: list[tuple[Operator, float]] = []
    for op, price_n, lat_n in zip(eligible, prices, latencies):
        score = (
            weights.reputation * op.reputation
            + weights.price * (1.0 - price_n)
            + weights.latency * (1.0 - lat_n)
        )
        if req.preferred_region and op.region == req.preferred_region:
            score += 0.05  # tie-breaking co-location nudge
        scored.append((op, score))

    # Sort by score desc, then by identity for deterministic tie-breaking (auditability).
    scored.sort(key=lambda t: (-t[1], t[0].identity))
    return scored


def route(
    operators: list[Operator],
    req: RoutingRequest,
    weights: RoutingWeights = RoutingWeights(),
    *,
    base_audit_prob: float = 0.03,
) -> RoutingDecision:
    """Full routing decision: pick a shard sized to the workload's economic security needs.

    The shard size is not a fixed constant; it is the redundancy the economics demand
    (``recommended_redundancy``). A cheap, low-stakes call routes to a single best operator; a
    high-value call fans out to a cross-checked shard. If the eligible pool is smaller than the
    desired redundancy, the shard is as large as the pool allows, so a caller can detect
    under-provisioning when len(shard) < redundancy.
    """
    decision = RoutingDecision()
    for op in operators:
        reason = _eligible(op, req)
        if reason is not None:
            decision.rejected[op.identity] = reason

    scored = score_operators(operators, req, weights)
    if not scored:
        return decision

    decision.redundancy = recommended_redundancy(req.workload, base_audit_prob=base_audit_prob)
    decision.shard = [op for op, _ in scored[: decision.redundancy]]
    return decision
