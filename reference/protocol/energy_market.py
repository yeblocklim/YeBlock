# SPDX-License-Identifier: Apache-2.0
#
# Status: first-phase reference excerpt (pre-alpha). Interfaces and protocol logic only,
# not the production implementation, and subject to change as the spec matures.
# Scope and rationale: reference/README.md.
"""YeBlock LIM - YeBlock LEM energy market mechanisms (original mechanism design).

Liquid Economy §11.2 (lim-protocol.md). YeBlock LEM starts from a physical constraint the
protocol refuses to paper over: electricity does not travel well, but intelligence does. So
YeBlock LEM never
moves a watt - it converts energy advantage into network advantage IN PLACE, through three
paths, each of which is a thin recomposition of existing primitives:

  Path A - Energy-aware routing. Batch/bulk workloads gain energy cost and carbon intensity
           as scoring signals on top of the standard reputation/price/latency matcher
           (routing.py). Interactive routing is UNCHANGED: latency dominance is never traded
           for an energy discount on user-facing calls.
  Path B - Hosting splits. "Has power, no hardware" hosts "has hardware, no power": one
           node's revenue partitions integer-exactly between the hardware seat and the
           energy seat at an on-chain ratio. Trustless because settlement enforces the
           split - neither seat custodies the other's share.
  Path C - JouleCredits. Metered, TEE-attested contribution mints auditable energy credits.
           Honesty is economic, not assumed: redundant meters cross-check every window, and
           over-reporting is slashed using the SAME expected-value inequality that keeps
           compute operators honest (economic_security.py).

The on-chain mirror of this file is IEnergyCredit; the routing extension feeds routing.py.
"""

from __future__ import annotations

from dataclasses import dataclass

import economic_security as es
import routing as rt
from royalty_waterfall import largest_remainder

Identity = str

BASIS_POINTS = 10_000


# ---------------------------------------------------------------------------
# Path A - energy-aware routing (batch/bulk only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EnergyProfile:
    """Per-operator energy signals, attested via the Path C metering pipeline."""

    energy_cost_per_kwh: float  # settlement units; what the operator actually pays
    carbon_intensity: float  # gCO2/kWh of the supply mix
    in_surplus_window: bool = False  # solar noon / curtailed wind / off-peak


@dataclass(frozen=True)
class EnergyWeights:
    """Additional scoring weights for batch/bulk routing. Zero for interactive class."""

    energy: float = 0.25
    carbon: float = 0.10
    surplus_bonus: float = 0.05  # nudge toward operators currently in a surplus window


def energy_aware_scores(
    operators: list[rt.Operator],
    profiles: dict[Identity, EnergyProfile],
    req: rt.RoutingRequest,
    *,
    latency_class: str = "batch",
    base_weights: rt.RoutingWeights = rt.RoutingWeights(),
    energy_weights: EnergyWeights = EnergyWeights(),
) -> list[tuple[rt.Operator, float]]:
    """Score operators with energy signals layered on the standard matcher.

    For ``interactive`` workloads this returns the plain routing scores - the energy layer
    is structurally absent, not just zero-weighted, so a latency regression cannot be
    introduced by configuration. For batch/bulk, cheap and clean power raises the score;
    operators without an attested profile contribute no energy signal (treated as the
    worst observed cost/carbon, never as free).
    """
    base = rt.score_operators(operators, req, base_weights)
    if latency_class == "interactive" or not base:
        return base

    eligible = [op for op, _ in base]
    worst_cost = max(
        (profiles[o.identity].energy_cost_per_kwh for o in eligible if o.identity in profiles),
        default=0.0,
    )
    worst_carbon = max(
        (profiles[o.identity].carbon_intensity for o in eligible if o.identity in profiles),
        default=0.0,
    )

    costs = [
        profiles[o.identity].energy_cost_per_kwh if o.identity in profiles else worst_cost
        for o in eligible
    ]
    carbons = [
        profiles[o.identity].carbon_intensity if o.identity in profiles else worst_carbon
        for o in eligible
    ]
    cost_n = rt._normalize(costs)
    carbon_n = rt._normalize(carbons)

    rescored: list[tuple[rt.Operator, float]] = []
    for (op, score), c_n, g_n in zip(base, cost_n, carbon_n):
        score += energy_weights.energy * (1.0 - c_n)
        score += energy_weights.carbon * (1.0 - g_n)
        prof = profiles.get(op.identity)
        if prof is not None and prof.in_surplus_window:
            score += energy_weights.surplus_bonus
        rescored.append((op, score))

    rescored.sort(key=lambda t: (-t[1], t[0].identity))
    return rescored


# ---------------------------------------------------------------------------
# Path B - hosting splits (integer-exact, settlement-enforced)
# ---------------------------------------------------------------------------


def split_hosting_revenue(gross: int, hardware_bps: int) -> tuple[int, int]:
    """Partition one node's gross revenue between the hardware seat and the energy seat.

    Integer-exact via largest remainder: hardware + energy == gross ALWAYS. The ratio is a
    free negotiation between the two seats; the protocol only enforces that the registered
    split is honored at settlement (no custody between the parties).
    """
    if not (0 <= hardware_bps <= BASIS_POINTS):
        raise ValueError("hardware_bps out of range")
    hardware, energy = largest_remainder(gross, [hardware_bps, BASIS_POINTS - hardware_bps])
    return hardware, energy


# ---------------------------------------------------------------------------
# Path C - attestation validation & over-report economics
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MeterReading:
    meter: Identity
    joules: int  # attested for the window (aggregate; detail stays encrypted)


def validate_attestation(
    primary: MeterReading,
    cross_checks: list[MeterReading],
    *,
    tolerance_bps: int = 200,  # 2% metering tolerance
) -> tuple[bool, int]:
    """Accept or reject a metering window against redundant cross-check meters.

    Returns (accepted, mintable_joules). The mintable amount is the MINIMUM of the primary
    and the cross-check median-floor - a meter can never mint more than independent
    measurement corroborates. A primary that over-reports beyond tolerance is rejected
    outright (and, on-chain, slashed under "energy-over-report").
    """
    if primary.joules < 0:
        raise ValueError("negative joules")
    if not cross_checks:
        # No corroboration → nothing mintable. Solo meters earn nothing; honesty needs witnesses.
        return False, 0

    corroborated = sorted(r.joules for r in cross_checks)[len(cross_checks) // 2]  # median
    ceiling = corroborated + (corroborated * tolerance_bps) // BASIS_POINTS
    if primary.joules > ceiling:
        return False, 0
    return True, min(primary.joules, corroborated)


def over_report_unprofitable(
    *,
    credit_value: float,  # settlement value of the joules a cheater would fake
    metering_cost: float,  # honest cost of actually supplying that energy
    stake_at_risk: float,  # meter's slashable stake
    detection_prob: float,  # from redundant-meter coverage of the window
) -> bool:
    """True iff faking an attestation loses money in expectation.

    Identical inequality to compute verification (economic_security.py): treat the faked
    credit as the "reward", the avoided energy supply as the "saved cost", and ask whether
    detection-and-slash makes the gamble negative. One economics, two resources.
    """
    w = es.WorkloadEconomics(
        honest_cost=metering_cost,
        reward=credit_value,
        stake_at_risk=stake_at_risk,
    )
    return es.is_cheating_unprofitable(w, detection_prob)
