# The LIM Lexicon

> A protocol is a vocabulary. This page collects every term LIM coined or repurposed, with a precise one-paragraph definition. When the protocol documentation uses a capitalized term — *Inference Liquidity*, *Cognitive Settlement*, *Stakeholder Compute* — its meaning is fixed here.

The lexicon is intentionally compact. Every entry has a definition, why the term exists, and where it appears in the spec. Terms that are common in adjacent fields (HTTP, KEM, LoRA, content-addressed) are not redefined here; only LIM-original concepts are.

---

## A — F

### Algorithm Agility

The property that every signed object in LIM carries an explicit algorithm tag, so the protocol can migrate to new cryptographic primitives without invalidating historical signatures or stored receipts. Operationalized as: any new primitive is added by tag without breaking the wire format; deprecated primitives are sunset over a multi-month window with migration tooling. *See: [lim-protocol.md §8](./lim-protocol.md#8-versioning--algorithm-agility)*

### Cognitive Bandwidth

The aggregate inference throughput of the network, measured as tokens-per-second across all online operators weighted by quality class. Distinct from raw FLOPS because LIM's bottleneck is end-to-end protocol routing, not silicon. The product of *available* cognitive bandwidth and *priced* cognitive bandwidth defines the network's market clearing point.

### Cognitive Settlement

The atomic on-chain settlement step where compute, storage, and LoRA-author payouts are dispatched from a single bundle of execution receipts. Distinguished from generic blockchain settlement because the unit being settled is *reasoning work*, not asset movement. Settlement is **batched** — many receipts per chain transaction — to keep the on-chain footprint sub-linear in inference volume. *See: [lim-protocol.md §6](./lim-protocol.md#6-settlement-pre-image)*

### Composable Cognition

The design property that any output produced by one LIM-native model can be the input to another, without bespoke integration. Composability operates at three levels: *identity* (every artifact has a content hash), *interface* (every operator speaks the same execution contract), and *settlement* (a chain of compositions resolves to a single royalty waterfall). Composable Cognition is to LIM what *composable money* was to DeFi.

### Conformance Suite

The standardized set of inputs, expected outputs, and tolerance bounds that an inference runtime must pass to be eligible for routing. The conformance suite is itself content-addressed and signed; passing operators can attest to a specific suite version. Updates to the suite go through the same RFC process as protocol changes.

### Content-Addressed Identity

Every artifact in LIM — base model, LoRA adapter, conformance suite, royalty manifest — is identified by the cryptographic hash of its bytes under a forward-secure hash function. There is no separate name registry. Two artifacts with the same content have the same identity; a single byte changed produces a new identity. This is the foundation of LIM's Composable Cognition and Cryptographic Permanence guarantees. *See: [lim-protocol.md §3.1](./lim-protocol.md#31-content-addressed-identity)*

### Cryptographic Permanence

The guarantee that a published artifact remains addressable and verifiable indefinitely, as long as a single replica is maintained and a settlement chain exists to honor its references. The combination of content-addressed identity, hybrid post-quantum signatures, and replication-market storage produces an artifact lifetime that is bounded by economic demand, not by vendor decision. *See also: Storage Replication Market.*

### Economic Verification

The baseline mechanism by which LIM holds operators accountable: spot-check sampling combined with slashable stake commitments. Economic verification trades cryptographic certainty for operational practicality — it cannot prove a single inference was correct, but it makes systematic deviation from protocol rules unprofitable. Heavyweight cryptographic verification (zkML, TEE attestation) layers on top of economic verification as a future privacy/integrity tier, not as a replacement. *See: Stake Commitment.*

### Forward-Secure Mesh

The composite guarantee that LIM gives across all five pillars: every channel, every signature, every storage commitment is constructed so that traffic recorded today cannot be retroactively decrypted, forged, or repudiated by an adversary with future cryptographic capabilities — including quantum capabilities. The Forward-Secure Mesh is the operational manifestation of Pillar 5. *See: Hybrid KEM, Algorithm Agility.*

## G — N

### Gateway

A network participant that translates application-shaped requests into LIM protocol calls. Gateways do *not* see prompt content — they handle session lifecycle, identity, rate control, and bundle aggregation, but the encryption between user and operator is end-to-end. Multiple gateways can compete; the YeBlock-operated gateway is the reference implementation, not a privileged role. *See: [ARCHITECTURE.md §System Layers](../ARCHITECTURE.md#system-layers)*

### Hybrid KEM

A key encapsulation mechanism that derives a session key from the combination of a classical KEM (e.g., X25519) *and* a post-quantum KEM (e.g., ML-KEM / Kyber-class). The session key cannot be recovered without the post-quantum half, so traffic encrypted today is not retroactively decryptable by a quantum adversary that records ciphertext for later cryptanalysis. *See: [lim-protocol.md §3.3](./lim-protocol.md#33-encrypted-channels)*

### Inference-as-a-Public-Good

The doctrine that AI inference, like the public internet, is more valuable to humanity when it is open, permissionless, and cryptographically durable than when it is captured by a small number of vendors. LIM is the protocol implementation of this doctrine. The doctrine is not a claim that inference should be *free* — it is a claim that the *infrastructure for paying for inference* should be open.

### Inference Liquidity

The state in which compute capacity, model weights, and economic settlement flow frictionlessly to demand. The DeFi analogy is direct: liquidity in DeFi means anyone can swap, lend, or borrow without permission; Inference Liquidity means anyone can serve, consume, or compose cognition without permission. The Liquid in *Liquid Intelligence Mesh* refers to this property.

### LoRA Royalty Streams

The on-chain payment flow from inference settlement to LoRA adapter authors, defined by the signed royalty manifest attached to each adapter. Streams are settled per-inference, not per-month — an author whose LoRA is composed into 1,000 inferences in a minute receives 1,000 micropayments in the next settlement bundle. Streams are non-revocable and non-pausable at the protocol layer. *See: Royalty Manifest.*

### LoRA Stacking (Canonical Order)

The protocol-defined ordering in which LoRA adapters are applied during model composition. LoRAs are mathematically commutative under their underlying linear update, but LIM fixes a canonical lexicographic order by content hash to ensure that two compositions of the same set of adapters produce the same model identity. This trade-off costs a small amount of expressiveness and gains massive cache efficiency. *See: [lim-protocol.md §4.2](./lim-protocol.md#42-lora-stacking)*

### Model Identity

A deterministic composition expression — `compose(base, [lora₁, lora₂, …, loraₙ], params)` — whose result is itself content-addressed. Two requests with the same base, same LoRAs in canonical order, and same composition parameters produce the same Model Identity, allowing operators to cache compiled models across requests. Model Identity is the unit at which routing, settlement, and cache decisions are made.

## O — Z

### Open Inference Standard

LIM's positioning as a *standard*, not a product. By analogy: HTTP is a standard, not Apache or Nginx; the EVM is a standard, not Geth or Parity. LIM is the standard; YeBlock's reference implementation is one of what we hope will be many. The distinction matters because standards survive their first implementations; products do not.

### Permissionless Cognition

The user-facing manifestation of *Inference-as-a-Public-Good*: the ability to serve, consume, compose, or monetize AI inference without registering with a gatekeeper, signing a corporate ToS, or having one's account subject to unilateral revocation. Permissionless Cognition is the floor of the LIM social contract.

### Receipt

A signed record that a specific workload was executed against a specific model identity by a specific operator at a specific time. Receipts are the unit of payment in LIM. They are forward-secure, deduplicatable, and verifiable in `O(log n)` of the bundle they belong to. *See: [lim-protocol.md §6](./lim-protocol.md#6-settlement-pre-image)*

### Royalty Manifest

A signed, immutable specification attached to every author-published artifact (base model, LoRA adapter) that defines how settlement payouts split between the author, parent authors (for derivatives), and explicitly named collaborators. Manifests are content-addressed; updating a manifest requires publishing a new artifact with a new identity. The old manifest continues to govern the old artifact's payouts. *See: [lim-protocol.md §4.3](./lim-protocol.md#43-royalty-manifests)*

### Settlement Bundle

A batch of execution receipts submitted to the settlement chain in a single transaction. Bundles are produced on a fixed cadence (target: every 10–60 seconds) by aggregators and validated atomically by the settlement contract. Bundling collapses thousands of inference receipts into a single chain transaction — the protocol's mechanism for sub-linear on-chain footprint. *See: [lim-protocol.md §6](./lim-protocol.md#6-settlement-pre-image)*

### Stake Commitment

A reference to economic collateral locked on the settlement chain by an operator, gateway, or storage provider, plus the cryptographic identity it secures. The amount sets the upper bound on the cost of misbehavior; the slashing conditions enumerate exactly which protocol violations result in stake loss. Stake commitments are LIM's mechanism for replacing trust with skin-in-the-game. *See: [lim-protocol.md §3.4](./lim-protocol.md#34-stake-commitments)*

### Stakeholder Compute

The model in which compute operators are not contractors paid a hourly wage, but stakeholders whose ownership of the network — through stake, governance rights, and earned reputation — scales with their contribution. Stakeholder Compute is what distinguishes LIM from a GPU rental marketplace: in a rental marketplace, the operators are inventory; in LIM, the operators are owners.

### Storage Replication Market

The continuous market in which storage providers earn fees for keeping replicas of LIM artifacts available, and demand-side participants (model authors, application operators, even individual users) pay to keep specific artifacts alive. The replication count for any artifact is a market outcome, not a central decree — there is no protocol authority that can force or prohibit replication. An artifact persists as long as a single replica continues to be paid for. *See: Pillar 2.*

### The Third Unbundling

The framing thesis behind LIM: that the open internet has unbundled *content* (Web 1 → Web 2) and *money* (Web 2 → Web 3), and is now in the early stages of unbundling *intelligence* (Web 3 → Web ∞). LIM is the protocol layer of this third unbundling, in the same sense that HTTP and the EVM were the protocol layers of the first two. *See: [README — The Third Unbundling](../README.md#the-third-unbundling)*

### Verifiable Execution

The property that an operator's claim to have executed an inference can be independently checked — economically (via stake-slashing on detected deviation), statistically (via spot-check sampling), or cryptographically (via zkML or TEE attestation, in future tiers). Verifiable Execution is the mechanism by which LIM replaces the trust assumption of "the operator did what they said" with a checked invariant.

---

## Style Note

Capitalized lexicon terms in protocol documents (`Receipt`, `Settlement Bundle`, `Stake Commitment`) refer to the precise definitions on this page. Lowercased forms in narrative documents (`receipt`, `settlement`) are the colloquial usage. When the two diverge, the lexicon wins.

## See Also

- [README](../README.md) — High-level project narrative.
- [ARCHITECTURE.md](../ARCHITECTURE.md) — System architecture and design invariants.
- [lim-protocol.md](./lim-protocol.md) — Full protocol specification.
