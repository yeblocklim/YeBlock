# SPDX-License-Identifier: Apache-2.0
#
# Status: first-phase reference excerpt (pre-alpha). Interfaces and protocol logic only,
# not the production implementation, and subject to change as the spec matures.
# Scope and rationale: reference/README.md.
"""YeBlock LIM - Execution receipts (reference).

Pillar 1 (Compute). Transcribed from docs/lim-protocol.md §6 ("Settlement Pre-image") and
invariant I-5 ("Receipts are Settlement Instruments, Not Logs").

A receipt is the unit of payment. An operator signs one per inference; an aggregator batches
them into a settlement bundle; the settlement contract admits a receipt iff it satisfies the
four validity conditions below. This file makes the *building* and *validity* logic concrete
and leaves signing/verification to a pluggable, algorithm-tagged backend (invariant I-3).
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

ContentId = str
Identity = str


class LatencyClass(str, Enum):
    INTERACTIVE = "interactive"
    BATCH = "batch"
    BULK = "bulk"


@dataclass(frozen=True)
class ForwardSecureSignature:
    """A signature that verifies against its own tag, never a fixed scheme (§3.2).

    ``alg`` for any settlement-bearing object MUST be post-quantum or a hybrid that contains a
    post-quantum half (e.g. "ml-dsa-65" or "ed25519+ml-dsa-65").
    """

    alg: str
    signer: Identity
    bytes_hex: str


@dataclass(frozen=True)
class ExecutionReceipt:
    workload_id: ContentId
    model_identity: ContentId
    operator_identity: Identity
    bytes_in: int
    bytes_out: int
    latency_class: LatencyClass
    timestamp_ms: int
    operator_signature: ForwardSecureSignature

    def signing_preimage(self) -> bytes:
        """Canonical bytes that the operator signs.

        Field order is fixed and domain-separated so the same logical receipt always produces
        the same preimage across implementations.
        """
        return b"\x00".join(
            [
                b"yeblock-lim/receipt/v1",
                self.workload_id.encode("utf-8"),
                self.model_identity.encode("utf-8"),
                self.operator_identity.encode("utf-8"),
                str(self.bytes_in).encode("ascii"),
                str(self.bytes_out).encode("ascii"),
                self.latency_class.value.encode("ascii"),
                str(self.timestamp_ms).encode("ascii"),
            ]
        )


class Signer(ABC):
    """Operator-side signing backend. Concrete impls live in the node crypto module."""

    @property
    @abstractmethod
    def identity(self) -> Identity: ...

    @property
    @abstractmethod
    def alg(self) -> str:
        """Signature tag, e.g. "ml-dsa-65" or "ed25519+ml-dsa-65"."""

    @abstractmethod
    def sign(self, preimage: bytes) -> str:
        """Return the hex signature over ``preimage``."""


def build_receipt(
    signer: Signer,
    *,
    workload_id: ContentId,
    model_identity: ContentId,
    bytes_in: int,
    bytes_out: int,
    latency_class: LatencyClass,
    timestamp_ms: int | None = None,
) -> ExecutionReceipt:
    """Assemble and sign an execution receipt for a completed inference."""
    if bytes_in < 0 or bytes_out < 0:
        raise ValueError("byte counts must be non-negative")

    ts = timestamp_ms if timestamp_ms is not None else int(time.time() * 1000)
    unsigned = ExecutionReceipt(
        workload_id=workload_id,
        model_identity=model_identity,
        operator_identity=signer.identity,
        bytes_in=bytes_in,
        bytes_out=bytes_out,
        latency_class=latency_class,
        timestamp_ms=ts,
        operator_signature=ForwardSecureSignature(alg=signer.alg, signer=signer.identity, bytes_hex=""),
    )
    sig = signer.sign(unsigned.signing_preimage())
    return ExecutionReceipt(
        workload_id=unsigned.workload_id,
        model_identity=unsigned.model_identity,
        operator_identity=unsigned.operator_identity,
        bytes_in=unsigned.bytes_in,
        bytes_out=unsigned.bytes_out,
        latency_class=unsigned.latency_class,
        timestamp_ms=unsigned.timestamp_ms,
        operator_signature=ForwardSecureSignature(
            alg=signer.alg, signer=signer.identity, bytes_hex=sig
        ),
    )


# ---------------------------------------------------------------------------
# §6  The four-condition validity predicate
# ---------------------------------------------------------------------------
#
# A receipt is admitted to settlement iff ALL four hold. Failing receipts are dropped at
# validation and consume no chain resources. The resolvers below are the protocol's trust
# boundaries; a settlement client wires in concrete implementations.


class SignatureVerifier(ABC):
    @abstractmethod
    def verify(self, sig: ForwardSecureSignature, preimage: bytes) -> bool:
        """Verify ``sig`` against its own algorithm tag. Hybrid tags require BOTH halves valid."""


class StakeOracle(ABC):
    @abstractmethod
    def stake_is_current(self, operator: Identity, at_ms: int) -> bool:
        """Was the operator's stake commitment live at ``at_ms`` (invariant I-7)?"""


class ManifestResolver(ABC):
    @abstractmethod
    def resolves_to_live_manifest(self, model_identity: ContentId) -> bool:
        """Does the model identity map to a live royalty manifest (§4.3)?"""


class FinalizedSet(ABC):
    @abstractmethod
    def already_finalized(self, workload_id: ContentId) -> bool:
        """Has this workload already been paid in a finalized bundle (dedup, I-5)?"""


@dataclass
class ReceiptValidator:
    """Concrete validity logic over pluggable resolvers."""

    signatures: SignatureVerifier
    stake: StakeOracle
    manifests: ManifestResolver
    finalized: FinalizedSet

    def is_valid(self, r: ExecutionReceipt) -> bool:
        return (
            self.signatures.verify(r.operator_signature, r.signing_preimage())
            and self.stake.stake_is_current(r.operator_identity, r.timestamp_ms)
            and self.manifests.resolves_to_live_manifest(r.model_identity)
            and not self.finalized.already_finalized(r.workload_id)
        )

    def admit(self, receipts: list[ExecutionReceipt]) -> list[ExecutionReceipt]:
        """Filter a candidate batch down to the receipts a bundle may carry."""
        return [r for r in receipts if self.is_valid(r)]
