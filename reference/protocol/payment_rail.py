# SPDX-License-Identifier: Apache-2.0
#
# Status: first-phase reference excerpt (pre-alpha). Interfaces and protocol logic only,
# not the production implementation, and subject to change as the spec matures.
# Scope and rationale: reference/README.md.
"""YeBlock LIM - YeBlock LIP payment rail mechanisms (original mechanism design).

Liquid Economy §11.3 (lim-protocol.md). Human payment rails are low-frequency / high-value;
the machine economy is the inverse - per-token amounts at agent frequency, with multi-party
fan-out on every call. YeBlock LIP generalizes the protocol's internal settlement into that
rail.
Three mechanisms, all recompositions of §3-§6 primitives:

  1. Streaming pay. A stream accrues value continuously (per token / second / joule) and
     checkpoints against signed receipts. Closing a stream IS a settlement act: when a
     stream stops, everything consumed up to that point has already been paid for. Accrual
     is integer arithmetic - what is owed is exact.
  2. Agent wallets. An owner-set policy (per-call limit, daily limit, allowlist) is enforced
     by the rail at validation time. A payment outside policy does not "fail and get
     retried" - it is invalid, the same way a malformed receipt is invalid.
  3. Receipt-anchored A2A clearing. Every payment names the signed receipt that justifies it
     (invariant I-5, extended: receipts are the ONLY payment pre-image). A receipt can be a
     payment pre-image exactly once, so the design itself prevents double-pay; no monitoring
     is needed. Batch clearing is atomic: a multi-agent pipeline settles entirely or not at
     all.

Honest boundary, restated from the spec: rail throughput figures anywhere in project
material are design-capacity targets pending public testnet measurement; fee parameters
(including any burn schedule) are governance decisions, not protocol constants.

The on-chain mirror of this file is IPaymentRail.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from royalty_waterfall import largest_remainder

ContentId = str
Identity = str

BASIS_POINTS = 10_000


class StreamUnit(Enum):
    TOKENS = "tokens"
    SECONDS = "seconds"
    JOULES = "joules"


class PaymentError(Exception):
    """A payment that the rail rejects at validation time (policy or receipt violation)."""


@dataclass
class PaymentStream:
    """A continuously settled channel. Value owed = units consumed × rate, integer-exact."""

    stream_id: ContentId
    payer: Identity
    payee: Identity
    rate_per_unit: int  # smallest settlement units
    unit: StreamUnit
    open: bool = True
    settled_total: int = 0
    last_checkpoint_receipt: ContentId | None = None

    def checkpoint(self, units_consumed: int, receipt: ContentId) -> int:
        """Settle the units consumed since the last checkpoint against a signed receipt.

        Returns the amount settled by this checkpoint. The receipt is the proof of delivery
        for exactly these units; without it the checkpoint is invalid (I-5).
        """
        if not self.open:
            raise PaymentError(f"stream {self.stream_id} is closed")
        if units_consumed < 0:
            raise PaymentError("units consumed cannot be negative")
        amount = units_consumed * self.rate_per_unit
        self.settled_total += amount
        self.last_checkpoint_receipt = receipt
        return amount

    def close(self, final_units: int, final_receipt: ContentId) -> int:
        """Final checkpoint and close in one act; nothing consumed is left unpaid."""
        amount = self.checkpoint(final_units, final_receipt)
        self.open = False
        return amount


@dataclass(frozen=True)
class WalletPolicy:
    """Owner-set spending policy for an agent-held wallet. Enforced by the rail, not by the
    agent's good behavior."""

    owner: Identity
    agent: Identity
    per_call_limit: int
    daily_limit: int
    allowlist: frozenset[Identity] = frozenset()  # empty = any payee
    revoked: bool = False

    def check(self, payee: Identity, amount: int, spent_today: int) -> str | None:
        """Return None if the payment is within policy, else the violation."""
        if self.revoked:
            return "policy-revoked"
        if amount > self.per_call_limit:
            return "per-call-limit-exceeded"
        if spent_today + amount > self.daily_limit:
            return "daily-limit-exceeded"
        if self.allowlist and payee not in self.allowlist:
            return "payee-not-allowlisted"
        return None


@dataclass(frozen=True)
class Payment:
    """The atomic unit of A2A clearing: an amount and the receipt that justifies it."""

    payer: Identity
    payee: Identity
    amount: int
    receipt: ContentId


@dataclass
class Rail:
    """Receipt-anchored clearing with policy enforcement and governance-set fees.

    The fee (and the share of it that is burned) are PARAMETERS - governance decisions the
    mechanism executes, not constants it hard-codes. Fee splitting is integer-exact.
    """

    fee_bps: int = 30  # 0.30% — illustrative governance parameter
    burn_share_bps: int = 5_000  # half of the fee burned, half to the treasury
    policies: dict[Identity, WalletPolicy] = field(default_factory=dict)
    spent_today: dict[Identity, int] = field(default_factory=dict)
    used_receipts: set[ContentId] = field(default_factory=set)
    balances: dict[Identity, int] = field(default_factory=dict)
    burned: int = 0
    treasury: int = 0

    def set_policy(self, policy: WalletPolicy) -> None:
        self.policies[policy.agent] = policy

    def _validate(self, p: Payment) -> None:
        if p.amount <= 0:
            raise PaymentError("amount must be positive")
        if p.receipt in self.used_receipts:
            # A receipt is a payment pre-image exactly once (I-5 extended).
            raise PaymentError(f"receipt {p.receipt} already cleared")
        policy = self.policies.get(p.payer)
        if policy is not None:
            violation = policy.check(p.payee, p.amount, self.spent_today.get(p.payer, 0))
            if violation is not None:
                raise PaymentError(f"policy violation by {p.payer}: {violation}")

    def _apply(self, p: Payment) -> None:
        fee, _net_check = largest_remainder(p.amount, [self.fee_bps, BASIS_POINTS - self.fee_bps])
        burn, to_treasury = largest_remainder(fee, [self.burn_share_bps, BASIS_POINTS - self.burn_share_bps])
        net = p.amount - fee

        self.used_receipts.add(p.receipt)
        self.spent_today[p.payer] = self.spent_today.get(p.payer, 0) + p.amount
        self.balances[p.payee] = self.balances.get(p.payee, 0) + net
        self.burned += burn
        self.treasury += to_treasury

    def clear(self, p: Payment) -> None:
        """Single A2A payment: validate, then apply. Net + fee == amount exactly."""
        self._validate(p)
        self._apply(p)

    def clear_batch(self, payments: list[Payment]) -> None:
        """Atomic multi-leg clearing for agent pipelines: every leg validates BEFORE any leg
        applies, so a pipeline settles entirely or not at all (no half-settled state).
        Duplicate receipts within the batch are caught by the pre-validation pass."""
        seen: set[ContentId] = set()
        for p in payments:
            self._validate(p)
            if p.receipt in seen:
                raise PaymentError(f"receipt {p.receipt} duplicated within batch")
            seen.add(p.receipt)
        for p in payments:
            self._apply(p)

    def conservation_check(self, gross_cleared: int) -> bool:
        """Every cleared unit is a payee balance, burned, or in the treasury - exactly."""
        return sum(self.balances.values()) + self.burned + self.treasury == gross_cleared
