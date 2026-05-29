# LIM Protocol — Design Document

> *Version: Draft v0.1 — Pre-Alpha*
>
> This document specifies the **Liquid Intelligence Mesh (LIM) protocol** at the level of primitives, composition rules, and choreography. It is the source-of-truth for implementers. Where the document and an implementation disagree, the document wins until amended.

## Table of Contents

- [1. Scope](#1-scope)
- [2. Terminology](#2-terminology)
- [3. Primitives](#3-primitives)
- [4. Composition Rules](#4-composition-rules)
- [5. Request Flow](#5-request-flow)
- [6. Settlement Pre-image](#6-settlement-pre-image)
- [7. Threat Model](#7-threat-model)
- [8. Versioning & Algorithm Agility](#8-versioning--algorithm-agility)
- [9. Related Work](#9-related-work)
- [10. Open Questions](#10-open-questions)

---

## 1. Scope

LIM specifies **how an inference workload travels** from a user, through a network of independent operators, to a compute provider, and back — including how it is paid for, how it is verified, and how its supporting artifacts (weights, adapters, receipts) are distributed.

LIM **does not specify**:

- Which models exist on the network (any model an author publishes).
- Which inference runtimes operators use (any runtime that conforms to the execution interface).
- Which chain settlement happens on (any chain capable of executing the settlement contracts).
- What policies applications enforce (any policy that does not violate the protocol).

This separation is deliberate. Specifying these would couple the protocol to political and product decisions that should remain at the application layer.

## 2. Terminology

| Term | Definition |
|---|---|
| **Workload** | A single inference request — input plus the parameters needed to produce output. |
| **Model Identity** | A canonical reference to a base model + zero or more LoRA adapters in a deterministic order. |
| **Operator** | A network participant that executes workloads. |
| **Author** | A network participant that publishes a base model or LoRA adapter. |
| **Storage Provider** | A network participant that hosts content-addressed weight blobs. |
| **Gateway** | A network participant that translates application-shaped requests into LIM protocol calls. |
| **Receipt** | A signed record that a specific workload was executed against a specific model identity by a specific operator at a specific time. |
| **Settlement Bundle** | A batch of receipts submitted to the chain for atomic payout. |
| **Stake** | Economic collateral locked by operators, gateways, and storage providers; slashable on protocol violation. |

## 3. Primitives

LIM is built on a small set of primitives. Everything else is composition.

### 3.1 Content-Addressed Identity

Every artifact — base model, LoRA adapter, receipt — has a single canonical identifier that is the cryptographic hash of its content under a forward-secure hash function. There is no separate "name registry" that can drift from the bytes.

```
identity := H(content)
```

Implications:

- Two artifacts with the same content have the same identity. Plagiarism is mechanically detectable.
- An identity cannot be silently changed. Any change produces a new identity.
- Replication is trivial: any byte-equal copy is functionally identical.

### 3.2 Forward-Secure Signatures

Every signed object includes:

- The signer's **identity** (a public key).
- The **algorithm tag** (e.g. `dilithium3`, `falcon512`, `ed25519+dilithium3-hybrid`).
- The **signature bytes**.

Signatures are verified against the algorithm tag, not against a fixed scheme. This allows the protocol to evolve cryptographic primitives without invalidating historical signatures.

### 3.3 Encrypted Channels

Channels between user, gateway, and operator use **hybrid KEM** (classical + post-quantum). The user terminates encryption; intermediate parties carry ciphertext.

```
channel := KEM_encapsulate(user_pubkey, classical_kem || pq_kem)
```

Recorded ciphertext from any layer (gateway, operator, network observer) is not retroactively decryptable by a future quantum adversary, because the post-quantum half of the KEM is required to derive the session key.

### 3.4 Stake Commitments

Every operator, gateway, and storage provider publishes a **stake commitment** — a reference to locked collateral on the settlement chain plus the cryptographic identity it secures.

```
stake := { identity, chain_address, amount, slashing_conditions }
```

Stake amount sets the upper bound on the cost of misbehavior. Slashing conditions enumerate exactly which protocol violations result in stake loss.

## 4. Composition Rules

### 4.1 Model Composition

A model identity is a deterministic composition expression:

```
model_id := compose(base_id, [lora_id_1, lora_id_2, ..., lora_id_n], composition_params)
```

Where:

- `base_id` is the content hash of the base model weights.
- `lora_id_i` are content hashes of LoRA adapters, applied in order.
- `composition_params` are scalars controlling how each adapter is mixed (e.g. per-adapter alpha values).

The result is itself content-addressed. Two requests that compose the same base, same LoRAs, in the same order, with the same params — produce the same model identity. The runtime can therefore cache compiled models by identity.

### 4.2 LoRA Stacking

LoRA adapters are *commutative under addition* in their underlying linear algebra, but **the protocol fixes a canonical order** so that two compositions of the same set of adapters produce the same identity. The canonical order is lexicographic by adapter content hash.

This is a deliberate trade-off: it loses a small amount of expressiveness (some application-specific orderings may be preferable) in exchange for a large reduction in identity proliferation and cache fragmentation.

### 4.3 Royalty Manifests

Every author-published artifact carries a **royalty manifest** specifying how settlement payouts split between the author, prior authors (if the artifact is a derivative), and any explicitly named collaborators.

```
manifest := {
    author_identity,
    parent_identities: [...],     // for derivative works
    splits: [{ identity, basis_points }],
    constraints: { min_per_inference, currency_class }
}
```

Manifests are signed and immutable. Updating an artifact means publishing a new artifact (with a new identity); the old one's payouts continue to flow to its existing manifest.

## 5. Request Flow

The detailed request flow extends the high-level lifecycle in [ARCHITECTURE.md](../ARCHITECTURE.md#inference-request-lifecycle) with protocol-level specifics.

### 5.1 Phase A — Resolution

1. The application constructs a model identity (base + LoRAs + composition params).
2. The gateway resolves each content hash through the storage layer to obtain replica locations.
3. The gateway selects a routing target — an operator with the right hardware class, sufficient stake, and acceptable latency profile.

### 5.2 Phase B — Execution

4. The user encrypts the prompt against an ephemeral session key derived via hybrid KEM with the operator.
5. The gateway forwards the encrypted prompt to the operator with routing metadata. The gateway never sees the prompt content.
6. The operator pulls the required weights (using cache for hot artifacts), composes the model, runs inference.
7. The operator streams the encrypted response back to the user.

### 5.3 Phase C — Receipt

8. The operator signs an execution receipt covering: model identity, byte counts, latency class, timestamp, and a cryptographic commitment to the (encrypted) input/output.
9. The receipt is submitted to a *receipt aggregator* (typically the gateway).
10. The aggregator includes the receipt in the next settlement bundle.

### 5.4 Phase D — Settlement

11. The settlement bundle is published on-chain.
12. The settlement contract verifies signatures, looks up royalty manifests for each model identity, and disburses payouts atomically.
13. Storage providers and operators are paid; LoRA author royalties flow to manifest-specified recipients.

## 6. Settlement Pre-image

The **settlement pre-image** is the off-chain bundle the chain consumes. Its precise schema is normative:

```
SettlementBundle := {
    version: u8,                    // protocol version
    period_start: timestamp,
    period_end: timestamp,
    receipts: [ExecutionReceipt],
    aggregator_signature: Signature
}

ExecutionReceipt := {
    workload_id: hash,
    model_identity: hash,
    operator_identity: pubkey,
    bytes_in: u64,
    bytes_out: u64,
    latency_class: enum { interactive, batch, bulk },
    timestamp: timestamp,
    operator_signature: Signature
}
```

A receipt is **valid** if and only if:

- The operator signature verifies against the operator's published public key (with the algorithm tag indicated).
- The operator's stake commitment is current at `timestamp`.
- The model identity resolves to a live royalty manifest.
- The receipt has not been included in a previously-finalized bundle (deduplication).

Receipts that fail any check are dropped at validation time; they consume no chain resources.

## 7. Threat Model

### 7.1 In Scope

The protocol must be secure against:

- **Byzantine operators** who execute incorrectly to save compute, claim payouts they did not earn, or attempt to learn user content.
- **Byzantine gateways** that route unfairly, censor users, or fabricate receipts.
- **Byzantine storage providers** that delete replicas while continuing to claim storage fees.
- **Network observers** with passive recording capability, including future quantum adversaries replaying historical traffic.
- **Author identity squatting** — adversaries publishing duplicate or near-duplicate artifacts to capture royalty streams that should flow elsewhere.

### 7.2 Out of Scope

- **Endpoint compromise.** A user whose device is compromised cannot be protected by the protocol; their session keys are at risk regardless.
- **Content moderation.** The protocol is policy-neutral. Applications and gateways enforce policy; the protocol does not.
- **Sybil resistance at the user layer.** Sybil resistance for users is an application/gateway concern. The protocol resists Sybil at the *operator and storage* layers via stake.

### 7.3 Defense Summary

| Threat | Defense |
|---|---|
| Operator returning fake output | Spot-check sampling + stake slashing; future zkML / TEE attestation. |
| Operator reading prompts | E2EE channels; future confidential inference (TEE). |
| Storage provider deleting replicas | Challenge-response proofs of retrievability; payment conditional on responses. |
| Gateway censoring users | Multiple competing gateways; users freely choose. |
| Receipt forgery | Forward-secure signatures + deduplication on settlement. |
| Future quantum decryption of recorded traffic | Hybrid KEM ensures session keys cannot be derived without the post-quantum half. |
| Royalty stream theft | Content-addressed identity + first-publisher precedence + signed manifests. |

## 8. Versioning & Algorithm Agility

### 8.1 Protocol Versioning

Every signed protocol object carries a `version` field. The version specifies the **wire format** and **mandatory algorithms**.

- Backward-compatible changes (additions to optional fields, new algorithm tags) bump the minor version.
- Breaking changes (removed fields, changed semantics) bump the major version and require a coordinated rollout.

Operators MUST support at least the current major version and the previous major version simultaneously during rollout windows.

### 8.2 Algorithm Agility

Cryptographic primitives are referenced by tag, not hard-coded. Adding a new primitive requires:

1. A specification PR documenting the new tag, its semantics, and its security parameters.
2. At least two independent implementations.
3. A discussion-period soak time of at least 90 days.
4. A coordinated activation window.

Removing a primitive requires:

1. A deprecation notice with a sunset date no less than 12 months out.
2. Migration tooling for all artifacts signed under the deprecated primitive.
3. A coordinated retirement window.

This conservative approach is intentional. The protocol is intended to outlive its founders.

## 9. Related Work

LIM does not exist in a vacuum. It draws from — and consciously diverges from — three strands of prior art. We catalogue them here so that the protocol's positioning is legible to readers familiar with adjacent fields.

### 9.1 Decentralized Compute Networks

Networks such as **Bittensor**, **Akash**, **Render**, **Gensyn**, and **Ritual** address some subset of "decentralize the GPU." Each has a substantive contribution; none of them addresses the protocol surface LIM does.

| Strand | What it gets right | Where LIM diverges |
|---|---|---|
| **Bittensor** | Subnet structure for specialized inference; reputation via validator scoring. | Subnet competition is intra-network; LIM treats the network as a single composable mesh. Bittensor settles on its own L1; LIM is chain-agnostic. |
| **Akash** | Permissionless compute auctions; container-shaped workloads. | Akash workloads are arbitrary containers — useful but not inference-aware. LIM specifies a conformance suite for inference runtimes; routing knows what it is routing. |
| **Render** | Token-incentivized GPU contribution at scale, originally for rendering. | Render's design is rendering-shaped. LIM is inference-shaped — LoRA composition, royalty settlement, and confidential channels are first-class concerns. |
| **Gensyn** | Verifiable training via probabilistic proofs. | Training, not inference. The cost-of-verification curve is different at inference time, where p99 latency budgets dominate. |
| **Ritual** | Inference oracle for smart contracts; verifiable execution proofs. | Smart-contract-side inference, not user-side. Ritual is an oracle; LIM is a substrate. The two are complementary, not competing. |

LIM's distinguishing claims relative to this strand are: **content-addressed weights** (Pillar 2), **LoRA-granular royalty settlement** (Pillar 3), and **end-to-end encrypted operator-blind execution** (Pillar 4). No project we are aware of bundles these three.

### 9.2 Content-Addressed Storage

LIM's storage layer borrows directly from **IPFS / IPLD**, **Filecoin**, **Arweave**, and **Swarm**. Content-addressed storage is a settled idea; we do not claim novelty here.

What LIM contributes is the **economic binding** between a stored weight and an active settlement: a model is alive on LIM as long as its replication market clears. This is a different durability model than Filecoin (which prices storage in deal-time chunks) or Arweave (which front-loads a perpetual endowment). LIM treats replication as a continuous market, settled per-block alongside compute and royalties.

### 9.3 Privacy-Preserving Inference

The privacy literature splits into roughly three camps: **homomorphic encryption** (FHE inference, e.g. Concrete-ML), **secure multi-party computation** (MPC, e.g. Crypten), and **trusted execution environments** (TEE, e.g. Nvidia Confidential Computing, AMD SEV-SNP, Intel TDX).

LIM's Phase A privacy story uses end-to-end encrypted channels — strong against passive observers, weak against the operator running inference. Phase B layers TEE-attested execution on top, raising the bar to "operator cannot inspect even with hardware access." We do not currently target FHE/MPC inference because their performance overhead exceeds what end-users will tolerate at the latencies modern inference demands; we keep them in scope as a future tier when their performance improves.

### 9.4 Royalty-Aware Composition

The closest prior art for LoRA-granular royalty settlement is the **NFT royalty enforcement** debate (EIP-2981, ERC-6147, etc.) and academic work on **fractional ownership** in creative industries. LIM's contribution is to apply these patterns to *behavioral artifacts* (LoRA adapters as fine-grained skills) rather than to whole-asset ownership.

We are explicit that royalty enforcement is **protocol-mandated**, not socially-encouraged. Settlement contracts honor manifests automatically. There is no opt-out at the protocol layer; an operator that wishes to bypass royalties cannot do so through LIM at all.

### 9.5 Post-Quantum Migration

The cryptographic community has produced standardized post-quantum primitives (NIST PQC: ML-KEM / Kyber, ML-DSA / Dilithium, SLH-DSA / SPHINCS+, FN-DSA / Falcon) that LIM uses as-is. We claim no novelty in primitive design.

Our contribution is **applying them across an entire stack from day zero** rather than retrofitting them into a classical-only protocol. Most production systems will face a costly migration when classical schemes break; LIM does not, because its data-at-rest and channel security are hybrid post-quantum from v1.

## 10. Open Questions

The following are **explicitly unresolved** as of this draft. Listing them in public is deliberate: a protocol that pretends every question is settled is a protocol that has not been examined hard enough. Contributions to any of them are welcome — open a discussion.

1. **Verification floor.** What is the minimum acceptable verification regime for compute operators in steady state? Spot-check sampling alone may be insufficient for high-value workloads; full zkML is impractical for current models. The space between is undefined.

2. **Royalty manifest expressiveness.** Manifests are currently flat split tables. Should they support richer expressions (e.g. per-currency-class splits, time-decaying royalties, charitable destinations)? Each addition increases complexity at the settlement layer.

3. **Gateway accountability.** Gateways are trust-minimized but not trust-free; a malicious gateway can degrade user experience even if it cannot forge receipts. What incentives ensure gateway quality without imposing a registration regime?

4. **Storage replication economics.** The protocol describes a replication market without specifying its mechanics. Should it be a per-replica auction, a continuous fee model, or something else?

5. **Cross-chain settlement.** The protocol is currently chain-agnostic in theory but assumes a single settlement chain in any given deployment. Multi-chain settlement (where receipts can be redeemed on the user's chain of choice) is a desired but unspecified extension.

These questions are not blockers for pre-alpha. They are open work for the path to mainnet.

---

## Status of This Document

This is a **design document, not an implementation guide**. It describes what the protocol is intended to be when implemented. Implementations may deviate during pre-alpha; deviations should be documented as known gaps with target alignment dates.

The document will be revised as the design matures. Each revision will increment the draft version and append a change log at the bottom.

### Change Log

- **v0.1** — Initial public draft.

---

## See Also

- [README](../README.md)
- [ARCHITECTURE.md](../ARCHITECTURE.md)
