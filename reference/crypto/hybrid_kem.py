# SPDX-License-Identifier: Apache-2.0
#
# Status: first-phase reference excerpt (pre-alpha). Interfaces and protocol logic only,
# not the production implementation, and subject to change as the spec matures.
# Scope and rationale: reference/README.md.
"""YeBlock LIM - Hybrid key establishment (reference).

Pillars 4 (Privacy) and 5 (Post-Quantum). Transcribed from docs/lim-protocol.md §3.3
("Encrypted Channels") and invariant I-4 ("End-to-End Encryption is Non-Optional").

Channel session keys are derived from a HYBRID KEM: a classical KEM and a post-quantum KEM
combined so that the session key cannot be recovered without the post-quantum half. This is the
operational defense against "Harvest Now, Decrypt Later": traffic recorded today is not
retroactively decryptable by a future quantum adversary.

Important: the project does NOT invent cryptography (see README "What YeBlock LIM Is Not").
The classical and post-quantum KEMs are standardized primitives supplied by a vetted backend
(x25519 + ML-KEM-768 / FIPS 203). This module only specifies how they are *combined* and how
the combination is *tagged* for agility - it deliberately does not implement either primitive.
"""

from __future__ import annotations

import hashlib
import hmac
from abc import ABC, abstractmethod
from dataclasses import dataclass

# Deployed default. Matches the X25519MLKEM768 hybrid shipping in browsers / CDNs / TLS stacks.
DEFAULT_KEM_TAG = "x25519+ml-kem-768"

# Recognized tags (invariant I-3). Bare classical tags exist only as the classical half of a
# hybrid; a bare classical KEM is NOT acceptable for protocol channels.
HYBRID_TAGS = frozenset({"x25519+ml-kem-768"})
CLASSICAL_HALF = {"x25519+ml-kem-768": "x25519"}
PQ_HALF = {"x25519+ml-kem-768": "ml-kem-768"}


@dataclass(frozen=True)
class KemShare:
    """One leg of a hybrid encapsulation: ciphertext plus the shared secret it yields."""

    ciphertext: bytes
    shared_secret: bytes


class Kem(ABC):
    """A single standardized KEM primitive (classical OR post-quantum).

    Implementations wrap audited libraries; this interface never sees algorithm internals.
    """

    @property
    @abstractmethod
    def tag(self) -> str: ...

    @abstractmethod
    def encapsulate(self, recipient_public_key: bytes) -> KemShare: ...

    @abstractmethod
    def decapsulate(self, ciphertext: bytes, recipient_secret_key: bytes) -> bytes: ...


@dataclass(frozen=True)
class HybridEncapsulation:
    """The wire object an initiator sends to open a channel (see ChannelOffer in protocol.ts)."""

    kem: str  # hybrid tag, e.g. "x25519+ml-kem-768"
    classical_ct: bytes
    pq_ct: bytes


def _combine(classical_secret: bytes, pq_secret: bytes, transcript: bytes) -> bytes:
    """Combine two shared secrets into one session key.

    Uses an HMAC-based KDF (extract-then-expand) over the concatenation of BOTH secrets and the
    handshake transcript. Because the post-quantum secret is an input, the session key is
    unrecoverable without it - even by an adversary who breaks the classical KEM later.
    """
    ikm = classical_secret + pq_secret
    prk = hmac.new(b"yeblock-lim/hybrid-kem/v1", ikm, hashlib.sha3_256).digest()
    return hmac.new(prk, transcript + b"\x01", hashlib.sha3_256).digest()


class HybridKem:
    """Compose a classical and a post-quantum KEM into a single agile channel primitive."""

    def __init__(self, classical: Kem, post_quantum: Kem, tag: str = DEFAULT_KEM_TAG) -> None:
        if tag not in HYBRID_TAGS:
            raise ValueError(f"unsupported hybrid KEM tag: {tag!r}")
        if classical.tag != CLASSICAL_HALF[tag] or post_quantum.tag != PQ_HALF[tag]:
            raise ValueError(f"backend KEMs do not match hybrid tag {tag!r}")
        self._classical = classical
        self._pq = post_quantum
        self._tag = tag

    @property
    def tag(self) -> str:
        return self._tag

    def encapsulate(
        self,
        recipient_classical_pk: bytes,
        recipient_pq_pk: bytes,
        transcript: bytes,
    ) -> tuple[HybridEncapsulation, bytes]:
        """Initiator side: produce the wire encapsulation and the derived session key."""
        c = self._classical.encapsulate(recipient_classical_pk)
        q = self._pq.encapsulate(recipient_pq_pk)
        session_key = _combine(c.shared_secret, q.shared_secret, transcript)
        return (
            HybridEncapsulation(kem=self._tag, classical_ct=c.ciphertext, pq_ct=q.ciphertext),
            session_key,
        )

    def decapsulate(
        self,
        enc: HybridEncapsulation,
        classical_sk: bytes,
        pq_sk: bytes,
        transcript: bytes,
    ) -> bytes:
        """Recipient side: recover the same session key from the encapsulation."""
        if enc.kem != self._tag:
            raise ValueError(f"KEM tag mismatch: offer={enc.kem!r} self={self._tag!r}")
        classical_secret = self._classical.decapsulate(enc.classical_ct, classical_sk)
        pq_secret = self._pq.decapsulate(enc.pq_ct, pq_sk)
        return _combine(classical_secret, pq_secret, transcript)
