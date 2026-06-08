# SPDX-License-Identifier: Apache-2.0
#
# Status: first-phase reference excerpt (pre-alpha). Interfaces and protocol logic only,
# not the production implementation, and subject to change as the spec matures.
# Scope and rationale: reference/README.md.
"""YeBlock LIM - Derivative-aware royalty waterfall (original mechanism design).

Pillar 3 (Decentralized AI). LoRA adapters are built on other adapters - a "legal-contract"
LoRA may derive from a "formal-English" LoRA, which derives from a base style LoRA. The royalty
manifest captures this with a `parents` field (lim-protocol.md §4.3). Paying only the top author
would orphan the lineage that made the work possible; paying everyone naively double-counts.

This module is the protocol's own distribution rule: when an inference settles, the gross
royalty for an artifact flows *down its derivation lineage* - a fixed parent share is carried
upstream and recursively distributed, the remainder is split locally per the manifest. Two
properties make it settlement-grade:

  1. Integer-exact (no value leaks). All arithmetic is in the smallest settlement unit using a
     largest-remainder allocation, so the sum of all payouts equals the gross EXACTLY - never
     off by rounding. This matters because a receipt is a payment instrument (invariant I-5).
  2. Cycle-safe and depth-bounded. Manifests are immutable and content-addressed, so a true
     cycle is impossible, but a malformed registry is handled defensively: a revisited artifact
     or the depth cap collapses to a leaf (its share goes to its local author), so a single bad
     manifest can never make settlement diverge or revert.

This off-chain computation is the exact mirror of IRoyaltyRegistry.resolveSplits on-chain.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

ContentId = str
Identity = str

BASIS_POINTS = 10_000
MAX_LINEAGE_DEPTH = 8  # defensive bound on derivation depth


@dataclass(frozen=True)
class Manifest:
    artifact: ContentId
    author: Identity
    # Local payout slices; basis points MUST sum to 10_000.
    splits: tuple[tuple[Identity, int], ...]
    # Upstream artifacts this one derives from.
    parents: tuple[ContentId, ...] = ()
    # Fraction of THIS artifact's gross that flows upstream before the local split, in bps.
    parent_share_bps: int = 0

    def __post_init__(self) -> None:
        total = sum(bps for _, bps in self.splits)
        if total != BASIS_POINTS:
            raise ValueError(f"manifest {self.artifact}: splits sum to {total}, expected {BASIS_POINTS}")
        if not (0 <= self.parent_share_bps <= BASIS_POINTS):
            raise ValueError(f"manifest {self.artifact}: parent_share_bps out of range")
        if self.parent_share_bps > 0 and not self.parents:
            raise ValueError(f"manifest {self.artifact}: parent share set but no parents")


def largest_remainder(gross: int, weights_bps: list[int]) -> list[int]:
    """Split ``gross`` into integer parts proportional to ``weights_bps``, summing EXACTLY to
    ``gross``. Uses the largest-remainder (Hamilton) method: floor every share, then hand the
    leftover units one-by-one to the entries with the biggest fractional remainder. Ties break
    by index for determinism.
    """
    total_w = sum(weights_bps)
    if total_w <= 0:
        return [0] * len(weights_bps)

    floors: list[int] = []
    remainders: list[tuple[int, int]] = []  # (remainder_numerator, index)
    for i, w in enumerate(weights_bps):
        num = gross * w
        floors.append(num // total_w)
        remainders.append((num % total_w, i))

    leftover = gross - sum(floors)
    # Distribute leftover units to largest remainders first (then smallest index).
    remainders.sort(key=lambda t: (-t[0], t[1]))
    for k in range(leftover):
        floors[remainders[k][1]] += 1
    return floors


def distribute(
    artifact: ContentId,
    gross: int,
    registry: dict[ContentId, Manifest],
    *,
    _depth: int = 0,
    _seen: frozenset[ContentId] = frozenset(),
) -> dict[Identity, int]:
    """Recursively distribute ``gross`` (smallest settlement units) across ``artifact``'s
    lineage. Returns identity → integer payout; the sum equals ``gross`` exactly.
    """
    if gross <= 0:
        return {}

    manifest = registry.get(artifact)
    # Treat unknown / revisited / too-deep artifacts as leaves to keep settlement total-preserving.
    is_leaf = (
        manifest is None
        or artifact in _seen
        or _depth >= MAX_LINEAGE_DEPTH
        or manifest.parent_share_bps == 0
    )

    payouts: dict[Identity, int] = defaultdict(int)

    if is_leaf:
        local_manifest = manifest
        if local_manifest is None:
            # No manifest at all: the artifact id itself receives the funds (cannot be lost).
            payouts[artifact] += gross
            return dict(payouts)
        _split_local(local_manifest, gross, payouts)
        return dict(payouts)

    assert manifest is not None
    # Split gross into [local, parents] exactly.
    local_gross, parents_gross = largest_remainder(
        gross, [BASIS_POINTS - manifest.parent_share_bps, manifest.parent_share_bps]
    )

    # Local split.
    _split_local(manifest, local_gross, payouts)

    # Parents split: equal weight per parent, then recurse.
    if parents_gross > 0 and manifest.parents:
        per_parent = largest_remainder(parents_gross, [1] * len(manifest.parents))
        child_seen = _seen | {artifact}
        for parent, amount in zip(manifest.parents, per_parent):
            sub = distribute(parent, amount, registry, _depth=_depth + 1, _seen=child_seen)
            for ident, amt in sub.items():
                payouts[ident] += amt

    return dict(payouts)


def _split_local(manifest: Manifest, gross: int, into: dict[Identity, int]) -> None:
    """Apply a manifest's local split table to ``gross`` (integer-exact) and accumulate."""
    if gross <= 0:
        return
    identities = [ident for ident, _ in manifest.splits]
    weights = [bps for _, bps in manifest.splits]
    amounts = largest_remainder(gross, weights)
    for ident, amt in zip(identities, amounts):
        into[ident] += amt
