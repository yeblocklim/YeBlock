# SPDX-License-Identifier: Apache-2.0
#
# Status: first-phase reference excerpt (pre-alpha). Interfaces and protocol logic only,
# not the production implementation, and subject to change as the spec matures.
# Scope and rationale: reference/README.md.
"""YeBlock LIM - Economic security of compute verification (original mechanism design).

Pillar 1 (Compute). This module is NOT a wrapper around a standard; it is one of the
protocol's own mechanism designs. Crypto primitives we borrow (see crypto/hybrid_kem.py);
the *economics that make a permissionless inference market honest* we designed ourselves.

The thesis (ARCHITECTURE.md, Pillar 1 "Verification"; threat model in lim-protocol.md §7):
decentralized compute cannot prove every single inference cheaply, so the protocol does not
try to make cheating *impossible* - it makes cheating *unprofitable in expectation*. An
operator that returns fabricated tokens (skipping the real forward pass) saves compute cost
but risks detection-and-slashing. We size the audit rate and redundancy so the expected gain
of that gamble is strictly negative.

Model. For one workload:
  c = honest_cost        operator's real cost to compute the task (e.g. GPU-seconds → $)
  r = reward             what the operator is paid for the task
  S = stake_at_risk      collateral slashed if the operator is caught cheating
  p = audit_prob         effective probability this task's correctness is checked

A rational operator compares being honest vs. cheating this task:
  honest payoff           =  r - c
  cheat, undetected (1-p) =  r           (kept reward, paid no compute)  → +c vs honest
  cheat, detected   (p)   = -S           (reward withheld, stake slashed) → -(S + r - c) vs honest

Expected advantage of cheating over honesty:
  E[Δ] = (1-p)·c + p·(-(S + r - c))
       = c - p·(S + r)

Cheating is unprofitable  ⇔  E[Δ] < 0  ⇔  p > c / (S + r).

So the *minimum effective audit probability* the protocol must guarantee is:

      p_min = c / (S + r)

Two levers reach p_min:
  - spot-check sampling  - audit a random fraction of tasks (cheap, covers the long tail);
  - forced redundancy    - run a high-value task on k operators and cross-check, so a single
                           cheater is caught unless every cross-checker colludes identically.
With k cross-checked replicas and an independent per-operator collusion rate q, a lone
cheater is detected with probability  1 - q^(k-1)  (every other replica must also cheat the
same way to hide it). We escalate k only when sampling alone cannot reach p_min.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkloadEconomics:
    honest_cost: float  # c - real cost to compute the task honestly (settlement units)
    reward: float  # r - payment for the task
    stake_at_risk: float  # S - collateral slashable on a proven cheat

    def __post_init__(self) -> None:
        if self.honest_cost < 0 or self.reward < 0 or self.stake_at_risk < 0:
            raise ValueError("economic quantities must be non-negative")


def min_audit_probability(w: WorkloadEconomics) -> float:
    """Smallest effective audit probability that makes cheating unprofitable: p_min = c/(S+r).

    Usually in [0, 1]. If c >= S + r the result exceeds 1, meaning no audit rate alone can
    deter cheating and the stake requirement has to be raised instead.
    """
    denom = w.stake_at_risk + w.reward
    if denom == 0:
        return float("inf")
    return w.honest_cost / denom


def expected_cheating_advantage(w: WorkloadEconomics, audit_prob: float) -> float:
    """E[Δ] = c - p·(S + r). Negative ⇒ honesty dominates."""
    _check_prob(audit_prob)
    return w.honest_cost - audit_prob * (w.stake_at_risk + w.reward)


def is_cheating_unprofitable(w: WorkloadEconomics, audit_prob: float) -> bool:
    """True iff a rational operator strictly prefers honest execution at this audit rate."""
    return expected_cheating_advantage(w, audit_prob) < 0


def required_stake_for(w_without_stake: WorkloadEconomics, audit_prob: float) -> float:
    """Invert the inequality for the stake lever: minimum S such that cheating is unprofitable
    at a given audit probability.

        c - p·(S + r) < 0  ⇔  S > c/p - r
    """
    _check_prob(audit_prob)
    if audit_prob == 0:
        return float("inf")
    return max(0.0, w_without_stake.honest_cost / audit_prob - w_without_stake.reward)


def detection_probability(cross_check_replicas: int, collusion_rate: float) -> float:
    """Probability a lone cheater is caught when a task runs on k cross-checked replicas.

    A cheat hides only if every *other* replica colludes identically: P(hidden) = q^(k-1).
    Hence P(detected) = 1 - q^(k-1). With k = 1 there is no cross-check ⇒ 0 from redundancy.
    """
    if cross_check_replicas < 1:
        raise ValueError("replicas must be >= 1")
    _check_prob(collusion_rate)
    if cross_check_replicas == 1:
        return 0.0
    return 1.0 - collusion_rate ** (cross_check_replicas - 1)


def recommended_redundancy(
    w: WorkloadEconomics,
    *,
    base_audit_prob: float,
    collusion_rate: float = 0.10,
    max_replicas: int = 5,
) -> int:
    """Choose the redundancy factor k for a workload.

    Use cheap sampling when it already clears p_min. Otherwise add cross-check replicas
    (minimum 2, since you need a second opinion to compare against) until the combined
    detection probability clears p_min, capped at ``max_replicas``. Higher-value workloads
    have a higher p_min, so they pull in more replicas on their own.
    """
    _check_prob(base_audit_prob)
    p_min = min_audit_probability(w)

    if p_min > 1.0:
        # Sampling/redundancy cannot fix this; caller must raise the stake requirement.
        return max_replicas
    if base_audit_prob >= p_min:
        return 1  # spot-check sampling alone suffices

    for k in range(2, max_replicas + 1):
        # Effective detection = sampling OR cross-check disagreement.
        eff = base_audit_prob + (1.0 - base_audit_prob) * detection_probability(k, collusion_rate)
        if eff >= p_min:
            return k
    return max_replicas


def _check_prob(p: float) -> None:
    if not (0.0 <= p <= 1.0):
        raise ValueError(f"probability out of range: {p!r}")
