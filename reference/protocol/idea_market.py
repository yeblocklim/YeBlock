# SPDX-License-Identifier: Apache-2.0
#
# Status: first-phase reference excerpt (pre-alpha). Interfaces and protocol logic only,
# not the production implementation, and subject to change as the spec matures.
# Scope and rationale: reference/README.md.
"""YeBlock LIM - YeBlock LIME idea market settlement (original mechanism design).

Liquid Economy §11.1 (lim-protocol.md). An IdeaCapsule is an encrypted, content-addressed
idea whose on-chain registration timestamp is the author's Proof of Priority. Once funded,
the capsule is decomposed into a task pipeline: machine steps run as ordinary inference
workloads; steps outside model competence are *reverse-hired* to humans, who post stake and
deliver against signed receipts under the same QA-and-slash regime as any operator.

This module is the settlement logic of that pipeline, with the same settlement-grade
properties as the rest of the protocol:

  1. Escrow conservation (no value leaks). Settling a funded capsule partitions the escrow
     EXACTLY into step fees, the idea author's licensed-execution share, and the funder's
     residual refund - integer arithmetic with a largest-remainder allocation throughout,
     because a receipt is a payment instrument (invariant I-5).
  2. Human steps are economically symmetric to machine steps. A human executor who fails QA
     plus arbitration is slashed exactly like a cheating operator; the slash flows back to
     the escrow (the damaged party), never to the protocol.
  3. Derivative ideas inherit the LoRA lineage rule. Downstream revenue for a capsule walks
     its `parents` chain through the SAME derivative-aware waterfall LoRA royalties use
     (royalty_waterfall.distribute) - cycle-safe, depth-bounded, exact-sum.

The on-chain mirror of this file is IIdeaRegistry.settle + ISettlement.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from royalty_waterfall import Manifest, distribute, largest_remainder

ContentId = str
Identity = str

BASIS_POINTS = 10_000

# Share of a derivative capsule's gross that flows upstream to its parents before the local
# split. One protocol constant (governance-tunable), mirroring the LoRA lineage default.
PARENT_SHARE_BPS = 2_000


class StepKind(Enum):
    MACHINE = "machine"  # ordinary inference workload (lim-protocol §5)
    HUMAN = "human"  # reverse-hired task (lim-protocol §11.1)


@dataclass(frozen=True)
class TaskStep:
    """One step of a decomposed capsule pipeline, priced at posting time."""

    step_id: ContentId
    kind: StepKind
    executor: Identity  # operator (machine) or human executor (human)
    fee: int  # smallest settlement units, fixed when the step is posted
    stake: int = 0  # human steps: collateral posted on acceptance
    qa_passed: bool = True  # model-based QA + sampled arbitration verdict

    def __post_init__(self) -> None:
        if self.fee < 0 or self.stake < 0:
            raise ValueError(f"step {self.step_id}: fee/stake must be non-negative")
        if self.kind is StepKind.HUMAN and self.stake <= 0:
            raise ValueError(f"step {self.step_id}: human steps require posted stake")


@dataclass(frozen=True)
class IdeaCapsule:
    capsule_id: ContentId
    author: Identity
    ask: int  # escrowed amount required to fund execution
    royalty_bps: int  # author's licensed-execution share of the escrow above step fees
    parents: tuple[ContentId, ...] = ()

    def __post_init__(self) -> None:
        if not (0 <= self.royalty_bps <= BASIS_POINTS):
            raise ValueError(f"capsule {self.capsule_id}: royalty_bps out of range")


@dataclass(frozen=True)
class Settlement:
    """Outcome of settling one funded capsule. Conservation law (checked at construction):

        escrow + slashed == paid_steps + author_share + funder_refund + slash_to_escrow
        where slash_to_escrow is already inside funder_refund.
    """

    payouts: dict[Identity, int]  # executor / author → amount
    funder_refund: int  # unspent escrow + slashes, back to the funder
    slashed: dict[Identity, int]  # human executors slashed on failed QA

    def total_disbursed(self) -> int:
        return sum(self.payouts.values()) + self.funder_refund


def settle_execution(
    capsule: IdeaCapsule,
    steps: list[TaskStep],
    escrow: int,
) -> Settlement:
    """Settle a funded capsule against its pipeline receipts, escrow-conserving.

    Order of operations (normative):
      1. Every step with a passing receipt is paid its posted fee from escrow.
      2. A failed human step is paid NOTHING and slashed: its stake flows to the escrow
         (compensating the funder for the broken pipeline), mirroring operator slashing.
      3. Of the escrow remaining after step fees, the idea author receives `royalty_bps`
         (the licensed-execution share), integer-exact.
      4. The residual returns to the funder. Nothing is created, nothing is lost.
    """
    if escrow < capsule.ask:
        raise ValueError("capsule is underfunded; settlement requires escrow >= ask")

    fees_due = sum(s.fee for s in steps if s.qa_passed)
    if fees_due > escrow:
        raise ValueError("posted step fees exceed escrow; pipeline was mis-priced")

    payouts: dict[Identity, int] = {}
    slashed: dict[Identity, int] = {}
    slash_pool = 0

    for step in steps:
        if step.qa_passed:
            payouts[step.executor] = payouts.get(step.executor, 0) + step.fee
        elif step.kind is StepKind.HUMAN:
            # Non-delivery: stake is slashed to the damaged party (the escrow), invariant I-7.
            slashed[step.executor] = slashed.get(step.executor, 0) + step.stake
            slash_pool += step.stake

    remaining = escrow - fees_due
    author_share, funder_residual = largest_remainder(
        remaining, [capsule.royalty_bps, BASIS_POINTS - capsule.royalty_bps]
    )
    if author_share > 0:
        payouts[capsule.author] = payouts.get(capsule.author, 0) + author_share

    return Settlement(
        payouts=payouts,
        funder_refund=funder_residual + slash_pool,
        slashed=slashed,
    )


def lineage_registry(capsules: dict[ContentId, IdeaCapsule]) -> dict[ContentId, Manifest]:
    """Project a capsule registry into royalty-waterfall manifests.

    A capsule's local split is 100% to its author; derivatives carry PARENT_SHARE_BPS
    upstream. This is deliberately the same Manifest shape LoRA adapters use - idea lineage
    is not a new mechanism, it is the existing waterfall applied to a new asset class.
    """
    registry: dict[ContentId, Manifest] = {}
    for cid, cap in capsules.items():
        registry[cid] = Manifest(
            artifact=cid,
            author=cap.author,
            splits=((cap.author, BASIS_POINTS),),
            parents=cap.parents,
            parent_share_bps=PARENT_SHARE_BPS if cap.parents else 0,
        )
    return registry


def idea_revenue(
    capsule_id: ContentId,
    gross: int,
    capsules: dict[ContentId, IdeaCapsule],
) -> dict[Identity, int]:
    """Distribute downstream revenue for a capsule across its idea lineage, exact-sum.

    Used when the *artifact produced by an executed idea* keeps earning (a product, a LoRA,
    a report sold repeatedly): each settlement replays this waterfall, so the original
    author - and every ancestor idea - is paid perpetually and automatically.
    """
    return distribute(capsule_id, gross, lineage_registry(capsules))
