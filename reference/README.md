# Reference Interfaces

> **What this directory is.** This is the *normative reference surface* of the YeBlock LIM
> protocol — the data structures, composition rules, cryptographic envelopes, and on-chain
> interfaces that any conformant implementation must speak. The snippets here are extracted
> directly from the protocol specification ([`../docs/lim-protocol.md`](../docs/lim-protocol.md))
> and the architecture document ([`../ARCHITECTURE.md`](../ARCHITECTURE.md)).
>
> **What this directory is not.** It is **not** the full implementation. Routing engines,
> inference runtimes, storage daemons, and audited settlement contracts live in separate
> repositories that open only when they reach public-test maturity (see the
> [Repository Map](../README.md#repository-map)). The files below define *contracts and
> shapes*, not production systems: protocol-defined logic (identity derivation, canonical
> LoRA ordering, receipt validity) is concrete and verifiable; everything that touches real
> hardware, real weights, or real keys is expressed as an interface to be implemented.

Every file maps to one or more of the five pillars and to a specific section of the spec, so
that the code is provably consistent with the documentation.

| File | Pillar(s) | Spec anchor | Purpose |
|---|---|---|---|
| [`types/protocol.ts`](./types/protocol.ts) | All five | [lim-protocol §2–§6](../docs/lim-protocol.md) | The canonical wire data model — content identity, signatures, model identity, royalty manifest, stake, receipt, settlement bundle. |
| [`sdk/client.ts`](./sdk/client.ts) | 3 · Decentralized AI / 4 · Privacy | [lim-protocol §5](../docs/lim-protocol.md#5-request-flow) | The developer-facing SDK shape: base model + LoRA stack, end-to-end-encrypted requests, streamed responses. |
| [`node/composition.py`](./node/composition.py) | 1 · Compute / 3 · AI | [lim-protocol §4](../docs/lim-protocol.md#4-composition-rules) | Model-identity derivation and the canonical (lexicographic-by-hash) LoRA ordering an operator must reproduce. |
| [`node/receipts.py`](./node/receipts.py) | 1 · Compute | [lim-protocol §6](../docs/lim-protocol.md#6-settlement-pre-image) | How an operator builds, signs, and how a verifier validates an execution receipt (the four-condition validity predicate). |
| [`crypto/hybrid_kem.py`](./crypto/hybrid_kem.py) | 4 · Privacy / 5 · Post-Quantum | [lim-protocol §3.3](../docs/lim-protocol.md#33-encrypted-channels) | The hybrid (classical + post-quantum) key-establishment envelope and the algorithm-agility tag scheme. |
| [`contracts/IRoyaltyRegistry.sol`](./contracts/IRoyaltyRegistry.sol) | 3 · AI | [lim-protocol §4.3](../docs/lim-protocol.md#43-royalty-manifests) | On-chain royalty-manifest registration and split resolution. |
| [`contracts/IStakeVault.sol`](./contracts/IStakeVault.sol) | 1 · Compute / 2 · Storage | [ARCHITECTURE I-7](../ARCHITECTURE.md#i-7-stake-is-the-unit-of-trust) | Stake commitments and slashing — the unit of trust for operators, gateways, and storage providers. |
| [`contracts/ISettlement.sol`](./contracts/ISettlement.sol) | All five | [lim-protocol §6](../docs/lim-protocol.md#6-settlement-pre-image) | Atomic settlement of a receipt bundle: compute, storage, and LoRA-author payouts in one transaction. |

## Original mechanism design

The files above are the protocol's *interfaces and wire shapes*. The files below are the
protocol's *original logic* — the mechanisms YeBlock LIM designs itself rather than borrows.
The dividing line is deliberate and stated throughout the docs: **cryptographic primitives we
do not invent** (we wrap NIST standards — see `crypto/hybrid_kem.py` and "What YeBlock LIM Is
Not" in the README), but **the protocol and economic mechanisms that turn a pool of untrusted,
self-interested operators into a usable, honest, fairly-paid inference market are ours**. These
are fully implemented and exact, not illustrative — they are the part a first mover in the
five-pillar design has to get right.

| File | Pillar(s) | What is original here |
|---|---|---|
| [`protocol/economic_security.py`](./protocol/economic_security.py) | 1 · Compute | The audit-and-slash economics that make cheating *unprofitable in expectation*. Derives the minimum effective audit rate `p_min = c / (S + r)`, the stake lever, cross-check detection `1 − qᵏ⁻¹`, and the redundancy a workload's value demands. Implements the doc's claim "make cheating economically irrational, not technically impossible." |
| [`protocol/routing.py`](./protocol/routing.py) | 1 · Compute / 4 · Privacy | Reputation-weighted, latency-aware operator selection with stake-floor and TEE eligibility, deterministic (auditable) tie-breaking, and a shard size driven by the economic-security redundancy rather than a fixed constant. |
| [`protocol/royalty_waterfall.py`](./protocol/royalty_waterfall.py) | 3 · AI | Derivative-aware royalty distribution down a LoRA derivation lineage, computed integer-exact (largest-remainder) so payouts sum to the gross with zero rounding leak, and cycle-safe/depth-bounded for settlement safety. The off-chain mirror of `IRoyaltyRegistry.resolveSplits`. |

These three are intentionally *runnable and checkable*: identity derivation, the `p_min`
inequality, and the exact-sum waterfall can each be verified independently of any deployed
system. They encode design decisions, so they live here as the source of truth and move with
the spec.

## Conformance, not implementation

A system is a conformant YeBlock LIM implementation if, and only if, it honors these
interfaces and the eight [design invariants](../ARCHITECTURE.md#design-invariants). Two
properties make that checkable from this directory alone:

1. **Cryptographic agility is structural.** Every signed or encrypted object carries an
   explicit algorithm tag (see `AlgorithmTag` / `KemTag` in `types/protocol.ts`). Nothing
   hard-codes a single primitive, so the protocol can absorb future standards without
   invalidating historical artifacts.
2. **Identity is content-derived.** Model and artifact identities are functions of their
   bytes, computed identically by every participant. The reference derivations in
   `node/composition.py` are the single source of truth for that computation.

## Status

These files track **Draft v0.1** of the protocol. They are illustrative of the conformance
surface and will move in lockstep with the spec; where a file and the spec disagree, the
spec wins until the file is amended. None of the code here should be read as a security
claim about a deployed system — it describes what the protocol *is*, ahead of what is *shipped*.
