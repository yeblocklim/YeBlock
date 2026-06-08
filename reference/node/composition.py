# SPDX-License-Identifier: Apache-2.0
#
# Status: first-phase reference excerpt (pre-alpha). Interfaces and protocol logic only,
# not the production implementation, and subject to change as the spec matures.
# Scope and rationale: reference/README.md.
"""YeBlock LIM - Model identity & LoRA composition (reference).

Pillars 1 (Compute) and 3 (Decentralized AI). Transcribed from
docs/lim-protocol.md §4 ("Composition Rules").

The *protocol-defined* logic here is concrete and authoritative: how a model identity is
derived, and the canonical order in which LoRA adapters are applied. Two participants that
follow this file compute byte-identical identities and therefore share cache keys and routing
decisions. The parts that touch real weights and real silicon (loading a base model, fusing
adapters, running a forward pass) are expressed as an interface - the engine, not the contract.

A conformant operator typically backs `InferenceEngine` with vLLM or SGLang multi-LoRA
serving; nothing in the protocol requires a specific runtime, only that it satisfies the
conformance suite.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

# A content identity is "<hash-tag>:<hex>" - see reference/types/protocol.ts §3.1.
ContentId = str

_DEFAULT_HASH_TAG = "sha3-256"


def content_id(data: bytes, hash_tag: str = _DEFAULT_HASH_TAG) -> ContentId:
    """Return the self-describing content identity of ``data``.

    The hash is tagged so the protocol can migrate hash functions without ambiguity
    (invariant I-3). Identity is a pure function of bytes (invariant I-1).
    """
    if hash_tag == "sha3-256":
        digest = hashlib.sha3_256(data).hexdigest()
    elif hash_tag == "blake3-256":
        # blake3 is provided by the operator's crypto backend; shown here for tag completeness.
        raise NotImplementedError("blake3-256 supplied by the node crypto backend")
    else:
        raise ValueError(f"unknown hash tag: {hash_tag!r}")
    return f"{hash_tag}:{digest}"


ALPHA_UNIT = 1000  # milli-units: 1000 == mix weight 1.0


@dataclass(frozen=True)
class CompositionParams:
    """Scalars controlling how each adapter is mixed.

    ``alpha_milli`` maps an adapter ContentId to its mix weight in milli-units (1000 == 1.0).
    Integers, not floats: float-to-string is not portable across languages, and the model
    identity below must be byte-identical for every implementation. An absent adapter is 1000.
    """

    alpha_milli: dict[ContentId, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for cid, weight in self.alpha_milli.items():
            if not isinstance(weight, int) or weight < 0:
                raise ValueError(f"alpha_milli[{cid!r}] must be a non-negative integer")

    def canonical_bytes(self) -> bytes:
        # Sorted "<cid>=<int>" pairs joined by \x1f. No floats, no JSON whitespace ambiguity.
        pairs = (f"{cid}={self.alpha_milli[cid]}" for cid in sorted(self.alpha_milli))
        return "\x1f".join(pairs).encode("utf-8")


@dataclass(frozen=True)
class ModelIdentity:
    base: ContentId
    loras: tuple[ContentId, ...]  # stored in CANONICAL order
    params: CompositionParams
    id: ContentId


def canonical_lora_order(loras: list[ContentId]) -> tuple[ContentId, ...]:
    """Canonical LoRA ordering: lexicographic by adapter ContentId (§4.2).

    LoRA updates are commutative under their underlying linear algebra, so the protocol is free
    to fix an order. Fixing one means the same *set* of adapters always yields the same model
    identity and the same compiled-model cache key, eliminating identity proliferation. Exact
    duplicates collapse to a single entry.
    """
    return tuple(sorted(set(loras)))


def derive_model_identity(
    base: ContentId,
    loras: list[ContentId],
    params: CompositionParams | None = None,
) -> ModelIdentity:
    """Compute the content-addressed identity of a base+LoRA composition (§4.1).

    ``model_id := H(base ‖ canonical(loras) ‖ params)``. Recomputable by any participant, which
    is what lets routing, settlement, and caching all agree on what "the model" is.
    """
    params = params or CompositionParams()
    ordered = canonical_lora_order(loras)

    preimage = b"\x00".join(
        [
            b"yeblock-lim/model-id/v1",
            base.encode("utf-8"),
            b"\x1f".join(a.encode("utf-8") for a in ordered),
            params.canonical_bytes(),
        ]
    )
    return ModelIdentity(
        base=base,
        loras=ordered,
        params=params,
        id=content_id(preimage),
    )


class WeightStore(ABC):
    """Pillar 2 boundary: resolve a ContentId to bytes from content-addressed storage.

    An artifact is alive as long as a single paid replica exists; resolution may hit a local
    hot cache, a peer, or the wider replication market.
    """

    @abstractmethod
    def fetch(self, cid: ContentId) -> bytes: ...

    @abstractmethod
    def is_cached(self, cid: ContentId) -> bool: ...


class InferenceEngine(ABC):
    """Pillar 1 boundary: an operator's inference runtime (e.g. vLLM / SGLang).

    Must pass the conformance suite to be eligible for routing. The protocol cares only that
    a given ``ModelIdentity`` produces deterministic-enough output to survive spot-checks.
    """

    @abstractmethod
    def load_base(self, base: ContentId, weights: bytes) -> None: ...

    @abstractmethod
    def attach_loras(self, identity: ModelIdentity, adapters: dict[ContentId, bytes]) -> None: ...

    @abstractmethod
    def generate(self, identity: ModelIdentity, prompt_ciphertext: bytes) -> bytes:
        """Run inference over an end-to-end-encrypted prompt and return encrypted output.

        The engine operates on ciphertext envelopes; plaintext keys are held by the user
        (invariant I-4). Confidential-tier execution additionally runs inside a TEE.
        """


class CompositionRuntime:
    """Glue an operator uses to serve a composed model. Pure orchestration; no crypto here."""

    def __init__(self, store: WeightStore, engine: InferenceEngine) -> None:
        self._store = store
        self._engine = engine

    def prepare(self, identity: ModelIdentity) -> None:
        """Ensure base + adapters are resident before the engine serves ``identity``.

        Hot operators pay no per-request storage fee; cold operators amortize the fetch across
        subsequent requests (ARCHITECTURE.md, request lifecycle step 6).
        """
        if not self._store.is_cached(identity.base):
            self._engine.load_base(identity.base, self._store.fetch(identity.base))
        adapters = {cid: self._store.fetch(cid) for cid in identity.loras}
        self._engine.attach_loras(identity, adapters)
