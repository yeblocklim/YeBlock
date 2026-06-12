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
| [`types/protocol.ts`](./types/protocol.ts) | All five | [lim-protocol §2–§6, §11](../docs/lim-protocol.md) | The canonical wire data model — content identity, signatures, model identity, royalty manifest, stake, receipt, settlement bundle, plus the Liquid Economy objects (IdeaCapsule, energy attestation, payment stream, agent wallet policy). |
| [`sdk/client.ts`](./sdk/client.ts) | 3 · Decentralized AI / 4 · Privacy | [lim-protocol §5, §11](../docs/lim-protocol.md#5-request-flow) | The developer-facing SDK shape: base model + LoRA stack, end-to-end-encrypted requests, streamed responses, and the design-stage Liquid Economy surfaces (`ideas`, `payments`, `energy`). |
| [`node/composition.py`](./node/composition.py) | 1 · Compute / 3 · AI | [lim-protocol §4](../docs/lim-protocol.md#4-composition-rules) | Model-identity derivation and the canonical (lexicographic-by-hash) LoRA ordering an operator must reproduce. |
| [`node/receipts.py`](./node/receipts.py) | 1 · Compute | [lim-protocol §6](../docs/lim-protocol.md#6-settlement-pre-image) | How an operator builds, signs, and how a verifier validates an execution receipt (the four-condition validity predicate). |
| [`crypto/hybrid_kem.py`](./crypto/hybrid_kem.py) | 4 · Privacy / 5 · Post-Quantum | [lim-protocol §3.3](../docs/lim-protocol.md#33-encrypted-channels) | The hybrid (classical + post-quantum) key-establishment envelope and the algorithm-agility tag scheme. |
| [`contracts/IRoyaltyRegistry.sol`](./contracts/IRoyaltyRegistry.sol) | 3 · AI | [lim-protocol §4.3](../docs/lim-protocol.md#43-royalty-manifests) | On-chain royalty-manifest registration and split resolution. |
| [`contracts/IStakeVault.sol`](./contracts/IStakeVault.sol) | 1 · Compute / 2 · Storage | [ARCHITECTURE I-7](../ARCHITECTURE.md#i-7-stake-is-the-unit-of-trust) | Stake commitments and slashing — the unit of trust for operators, gateways, and storage providers. |
| [`contracts/ISettlement.sol`](./contracts/ISettlement.sol) | All five | [lim-protocol §6](../docs/lim-protocol.md#6-settlement-pre-image) | Atomic settlement of a receipt bundle: compute, storage, and LoRA-author payouts in one transaction. |
| [`contracts/IIdeaRegistry.sol`](./contracts/IIdeaRegistry.sol) | Liquid Economy (YeBlock LIME) | [lim-protocol §11.1](../docs/lim-protocol.md#111-yeblock-lime--idea-registry--escrow) | IdeaCapsule registration (Proof of Priority), escrow, human-task lifecycle, and idea lineage. |
| [`contracts/IEnergyCredit.sol`](./contracts/IEnergyCredit.sol) | Liquid Economy (YeBlock LEM) | [lim-protocol §11.2](../docs/lim-protocol.md#112-yeblock-lem--energy-attestation) | TEE-attested energy attestations, JouleCredit minting/retirement, and two-seat hosting splits. |
| [`contracts/IPaymentRail.sol`](./contracts/IPaymentRail.sol) | Liquid Economy (YeBlock LIP) | [lim-protocol §11.3](../docs/lim-protocol.md#113-yeblock-lip--payment-rail) | Payment streams, agent wallet policy enforcement, and receipt-anchored A2A clearing. |

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
| [`protocol/idea_market.py`](./protocol/idea_market.py) | Liquid Economy (YeBlock LIME) | Escrow-conserving settlement of an AI+human execution pipeline: machine and reverse-hired human steps under one receipt/stake/slash regime, the author's licensed-execution share, and perpetual idea-lineage revenue replayed through the *same* waterfall LoRAs use. Off-chain mirror of `IIdeaRegistry.settle`. |
| [`protocol/energy_market.py`](./protocol/energy_market.py) | Liquid Economy (YeBlock LEM) | Energy-aware scoring layered on the standard matcher (batch/bulk only — interactive routing is structurally untouched), integer-exact two-seat hosting splits, and JouleCredit attestation with redundant-meter cross-checks priced by the same cheating-unprofitable inequality as compute. |
| [`protocol/payment_rail.py`](./protocol/payment_rail.py) | Liquid Economy (YeBlock LIP) | Streaming pay with receipt-anchored checkpoints, owner-set agent-wallet policy enforced at validation time, atomic batch A2A clearing (a pipeline settles entirely or not at all), and exact-sum fee/burn accounting with governance-set parameters. |

These six are intentionally *runnable and checkable*: identity derivation, the `p_min`
inequality, and every exact-sum distribution (waterfall, escrow, hosting split, fee/burn)
can each be verified independently of any deployed system — `python protocol/demo.py` walks
all of them. They encode design decisions, so they live here as the source of truth and move
with the spec.

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
