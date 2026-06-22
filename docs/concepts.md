# The YeBlock LIM Lexicon

> A protocol is a vocabulary. This page collects every term YeBlock LIM coined or repurposed, with a precise one-paragraph definition. When the protocol documentation uses a capitalized term — *Inference Liquidity*, *Cognitive Settlement*, *Stakeholder Compute* — its meaning is fixed here.

The lexicon is intentionally compact. Every entry has a definition, why the term exists, and where it appears in the spec. Terms that are common in adjacent fields (HTTP, KEM, LoRA, content-addressed) are not redefined here; only YeBlock LIM-original concepts are.

---

## A — F

### A2A Clearing

Agent-to-Agent settlement at machine latency: in a multi-agent pipeline, each agent pays the agents (or human executors) it delegates to, with every payment anchored to a signed execution receipt. A2A Clearing is the third, outward-facing layer of YeBlock LIP — external agent systems can clear over it without running inference on the mesh. *See: [ARCHITECTURE.md — YeBlock LIP](../ARCHITECTURE.md#yeblock-lip--settlement-rail)*

### Agent Wallet

An account-abstracted wallet held by an AI agent under owner-set policy: per-call and daily spend limits, recipient allowlists, purpose constraints, and instant revocation. Keys are held in TEEs; within policy the agent pays autonomously for API calls, data, compute, other agents, and human tasks. The Agent Wallet is the unit of economic autonomy in the Liquid Economy — bounded autonomy, never unbounded custody. *See: [lim-protocol.md §11.3](./lim-protocol.md#113-yeblock-lip--payment-rail)*

### Algorithm Agility

The property that every signed object in YeBlock LIM carries an explicit algorithm tag, so the protocol can migrate to new cryptographic primitives without invalidating historical signatures or stored receipts. Operationalized as: any new primitive is added by tag without breaking the wire format; deprecated primitives are sunset over a multi-month window with migration tooling. *See: [lim-protocol.md §8](./lim-protocol.md#8-versioning--algorithm-agility)*

### Cognitive Bandwidth

The aggregate inference throughput of the network, measured as tokens-per-second across all online operators weighted by quality class. Distinct from raw FLOPS because YeBlock LIM's bottleneck is end-to-end protocol routing, not silicon. The product of *available* cognitive bandwidth and *priced* cognitive bandwidth defines the network's market clearing point.

### Cognitive Settlement

The atomic on-chain settlement step where compute, storage, and LoRA-author payouts are dispatched from a single bundle of execution receipts. Distinguished from generic blockchain settlement because the unit being settled is *reasoning work*, not asset movement. Settlement is **batched** — many receipts per chain transaction — to keep the on-chain footprint sub-linear in inference volume. *See: [lim-protocol.md §6](./lim-protocol.md#6-settlement-pre-image)*

### Composable Cognition

The design property that any output produced by one YeBlock LIM-native model can be the input to another, without bespoke integration. Composability operates at three levels: *identity* (every artifact has a content hash), *interface* (every operator speaks the same execution contract), and *settlement* (a chain of compositions resolves to a single royalty waterfall). Composable Cognition is to YeBlock LIM what *composable money* was to DeFi.

### Conformance Suite

The standardized set of inputs, expected outputs, and tolerance bounds that an inference runtime must pass to be eligible for routing. The conformance suite is itself content-addressed and signed; passing operators can attest to a specific suite version. Updates to the suite go through the same RFC process as protocol changes.

### Content-Addressed Identity

Every artifact in YeBlock LIM — base model, LoRA adapter, conformance suite, royalty manifest — is identified by the cryptographic hash of its bytes under a forward-secure hash function. There is no separate name registry. Two artifacts with the same content have the same identity; a single byte changed produces a new identity. This is the foundation of YeBlock LIM's Composable Cognition and Cryptographic Permanence guarantees. *See: [lim-protocol.md §3.1](./lim-protocol.md#31-content-addressed-identity)*

### Cryptographic Permanence

The guarantee that a published artifact remains addressable and verifiable indefinitely, as long as a single replica is maintained and a settlement chain exists to honor its references. The combination of content-addressed identity, hybrid post-quantum signatures, and replication-market storage produces an artifact lifetime that is bounded by economic demand, not by vendor decision. *See also: Storage Replication Market.*

### Economic Verification

The baseline mechanism by which YeBlock LIM holds operators accountable: spot-check sampling combined with slashable stake commitments. Economic verification trades cryptographic certainty for operational practicality — it cannot prove a single inference was correct, but it makes systematic deviation from protocol rules unprofitable. Heavyweight cryptographic verification (zkML, TEE attestation) layers on top of economic verification as a future privacy/integrity tier, not as a replacement. *See: Stake Commitment.*

### Energy Hosting

The YeBlock LEM path that matches "has power, no hardware" with "has hardware, no power": a hardware owner deploys machines at an energy provider's site, and the node's revenue splits on-chain between the hardware seat and the energy seat at a freely negotiated ratio. The split is trustless because settlement enforces it — neither party custodies the other's share. *See: [ARCHITECTURE.md — YeBlock LEM](../ARCHITECTURE.md#yeblock-lem--energy-paths)*

### Forward-Secure Mesh

The composite guarantee that YeBlock LIM gives across all five pillars: every channel, every signature, every storage commitment is constructed so that traffic recorded today cannot be retroactively decrypted, forged, or repudiated by an adversary with future cryptographic capabilities — including quantum capabilities. The Forward-Secure Mesh is the operational manifestation of Pillar 5. *See: Hybrid KEM, Algorithm Agility.*

## G — N

### Gateway

A network participant that translates application-shaped requests into YeBlock LIM protocol calls. Gateways do *not* see prompt content — they handle session lifecycle, identity, rate control, and bundle aggregation, but the encryption between user and operator is end-to-end. Multiple gateways can compete; the YeBlock-operated gateway is the reference implementation, not a privileged role. *See: [ARCHITECTURE.md §System Layers](../ARCHITECTURE.md#system-layers)*

### Human Node

A human executor wrapped in the protocol's node abstraction. When a YeBlock LIME execution pipeline reaches a step no model can perform (physical-world legwork, credentialed sign-off, final human judgment), the step is posted as a priced task; the human who accepts it posts stake, delivers against a signed receipt, is quality-checked by model-based QA plus sampled arbitration, and is slashable on non-delivery — the same regime as any compute operator. Steps that models cannot perform are assigned to humans, and model-based QA then checks what the humans deliver. *See: Reverse Hiring.*

### Hybrid KEM

A key encapsulation mechanism that derives a session key from the combination of a classical KEM (e.g., X25519) *and* a post-quantum KEM (e.g., ML-KEM / Kyber-class). The session key cannot be recovered without the post-quantum half, so traffic encrypted today is not retroactively decryptable by a quantum adversary that records ciphertext for later cryptanalysis. *See: [lim-protocol.md §3.3](./lim-protocol.md#33-encrypted-channels)*

### IdeaCapsule

The unit asset of YeBlock LIME: an idea, client-side encrypted, content-addressed, and registered on-chain with a public teaser, license terms, and pricing — signed with a post-quantum signature. The capsule is simultaneously confidential (full content readable only by the author and licensed funders) and provable (its hash and timestamp establish Proof of Priority). Executable by the mesh once funded. *See: [lim-protocol.md §11.1](./lim-protocol.md#111-yeblock-lime--idea-registry--escrow)*

### Idea Lineage

The on-chain parent-child graph of derivative ideas. A fork of an IdeaCapsule references its parent at registration; downstream revenue flows upstream through the same derivative-aware royalty waterfall that LoRA lineages use. Archival-class signatures (SLH-DSA) keep the lineage verifiable for decades. The result: ideas inherit like music copyright — a family tree with automatic, perpetual attribution. *See: Royalty Manifest.*

### Inference-as-a-Public-Good

The doctrine that AI inference, like the public internet, is more valuable to humanity when it is open, permissionless, and cryptographically durable than when it is captured by a small number of vendors. YeBlock LIM is the protocol implementation of this doctrine. The doctrine is not a claim that inference should be *free* — it is a claim that the *infrastructure for paying for inference* should be open.

### Inference Liquidity

The state in which compute capacity, model weights, and economic settlement flow frictionlessly to demand. The DeFi analogy is direct: liquidity in DeFi means anyone can swap, lend, or borrow without permission; Inference Liquidity means anyone can serve, consume, or compose cognition without permission. The Liquid in *Liquid Intelligence Mesh* refers to this property.

### JouleCredit

An auditable on-chain energy credit minted from metered, TEE-attested electricity contribution (see PoEC). Operators buy JouleCredits to offset power costs; ESG-constrained buyers retire green-attested credits for compliance; surplus-window credits (solar noon, curtailed wind) list at a discount and attract elastic workloads. A JouleCredit prices energy *into* the network without pretending to move energy *through* it. *See: [lim-protocol.md §11.2](./lim-protocol.md#112-yeblock-lem--energy-attestation)*

### Liquid Economy

The application layer of YeBlock LIM, also called the **Liquid Trinity**: three protocol-native applications — YeBlock LIME (ideas), YeBlock LEM (energy), YeBlock LIP (settlement) — composed entirely from primitives the five pillars already provide. The pillars answer *what the network is made of*; the Liquid Economy answers *what economic activity happens on it*. The three applications cover the network's input (energy), its demand side (ideas), and how value moves between participants (settlement). *See: [README — The Liquid Economy](../README.md#the-liquid-economy)*

### LoRA Royalty Streams

The on-chain payment flow from inference settlement to LoRA adapter authors, defined by the signed royalty manifest attached to each adapter. Streams are settled per-inference, not per-month — an author whose LoRA is composed into 1,000 inferences in a minute receives 1,000 micropayments in the next settlement bundle. Streams are non-revocable and non-pausable at the protocol layer. *See: Royalty Manifest.*

### LoRA Stacking (Canonical Order)

The protocol-defined ordering in which LoRA adapters are applied during model composition. LoRAs are mathematically commutative under their underlying linear update, but YeBlock LIM fixes a canonical lexicographic order by content hash to ensure that two compositions of the same set of adapters produce the same model identity. This trade-off costs a small amount of expressiveness and gains massive cache efficiency. *See: [lim-protocol.md §4.2](./lim-protocol.md#42-lora-stacking)*

### Model Identity

A deterministic composition expression — `compose(base, [lora₁, lora₂, …, loraₙ], params)` — whose result is itself content-addressed. Two requests with the same base, same LoRAs in canonical order, and same composition parameters produce the same Model Identity, allowing operators to cache compiled models across requests. Model Identity is the unit at which routing, settlement, and cache decisions are made.

## O — Z

### Open Inference Standard

YeBlock LIM's positioning as a *standard*, not a product. By analogy: HTTP is a standard, not Apache or Nginx; the EVM is a standard, not Geth or Parity. YeBlock LIM is the standard; YeBlock's reference implementation is one of what we hope will be many. The distinction matters because standards survive their first implementations; products do not.

### Permissionless Cognition

The user-facing manifestation of *Inference-as-a-Public-Good*: the ability to serve, consume, compose, or monetize AI inference without registering with a gatekeeper, signing a corporate ToS, or having one's account subject to unilateral revocation. Permissionless Cognition is the floor of the YeBlock LIM social contract.

### Proof of Energy Contribution (PoEC)

The attestation pattern by which YeBlock LEM makes energy contribution legible without trusting the contributor: smart-meter readings are signed inside a TEE, metering detail stays encrypted (only aggregates are public), credits carry post-quantum signatures for decade-scale audit validity, and over-reporting is slashed against stake with redundant-meter cross-checks. PoEC reuses the same audit-and-slash approach that keeps compute operators honest, applied to energy metering. *See: JouleCredit, Stake Commitment.*

### Proof of Priority

The guarantee produced by minting an IdeaCapsule: "this idea existed, authored by this identity, at this time." Established by the content hash plus the on-chain registration timestamp plus a post-quantum signature — so the claim remains forgery-proof even against a future quantum adversary. Proof of Priority is what makes publishing an idea safe: disclosure no longer equals forfeiture. *See: IdeaCapsule.*

### Receipt

A signed record that a specific workload was executed against a specific model identity by a specific operator at a specific time. Receipts are the unit of payment in YeBlock LIM. They are forward-secure, deduplicatable, and verifiable in `O(log n)` of the bundle they belong to. *See: [lim-protocol.md §6](./lim-protocol.md#6-settlement-pre-image)*

### Reverse Hiring

The YeBlock LIME mechanism by which the execution pipeline — not a person — hires people. When task decomposition reaches a step outside any model's competence, the pipeline posts the step as a priced human task with acceptance criteria; the accepting Human Node delivers under the standard receipt/stake/slashing regime, and model-based QA performs first-pass verification. The first half of YeBlock LIME is humans hiring AI; Reverse Hiring is AI hiring humans — intelligence and labor flowing both directions through one pipeline. *See: Human Node.*

### Royalty Manifest

A signed, immutable specification attached to every author-published artifact (base model, LoRA adapter) that defines how settlement payouts split between the author, parent authors (for derivatives), and explicitly named collaborators. Manifests are content-addressed; updating a manifest requires publishing a new artifact with a new identity. The old manifest continues to govern the old artifact's payouts. *See: [lim-protocol.md §4.3](./lim-protocol.md#43-royalty-manifests)*

### Settlement Bundle

A batch of execution receipts submitted to the settlement chain in a single transaction. Bundles are produced on a fixed cadence (target: every 10–60 seconds) by aggregators and validated atomically by the settlement contract. Bundling collapses thousands of inference receipts into a single chain transaction — the protocol's mechanism for sub-linear on-chain footprint. *See: [lim-protocol.md §6](./lim-protocol.md#6-settlement-pre-image)*

### Stake Commitment

A reference to economic collateral locked on the settlement chain by an operator, gateway, or storage provider, plus the cryptographic identity it secures. The amount sets the upper bound on the cost of misbehavior; the slashing conditions enumerate exactly which protocol violations result in stake loss. Stake commitments are YeBlock LIM's mechanism for replacing trust with skin-in-the-game. *See: [lim-protocol.md §3.4](./lim-protocol.md#34-stake-commitments)*

### Stakeholder Compute

The model in which compute operators are not contractors paid a hourly wage, but stakeholders whose ownership of the network — through stake, governance rights, and earned reputation — scales with their contribution. Stakeholder Compute is what distinguishes YeBlock LIM from a GPU rental marketplace: in a rental marketplace, the operators are inventory; in YeBlock LIM, the operators are owners.

### Storage Replication Market

The continuous market in which storage providers earn fees for keeping replicas of YeBlock LIM artifacts available, and demand-side participants (model authors, application operators, even individual users) pay to keep specific artifacts alive. The replication count for any artifact is a market outcome, not a central decree — there is no protocol authority that can force or prohibit replication. An artifact persists as long as a single replica continues to be paid for. *See: Pillar 2.*

### Streaming Pay

YeBlock LIP's continuous billing primitive: value flows per token, per second, or per watt for as long as a stream is open, and stops the instant it closes. Inference output, storage leases, and energy credits are all naturally stream-shaped assets; Streaming Pay makes their billing shape match their delivery shape. Each stream checkpoint is anchored to a signed receipt, so whenever a stream stops, everything consumed up to that point has already been paid for. *See: A2A Clearing, Receipt.*

### The Third Unbundling

The framing thesis behind YeBlock LIM: that the open internet has unbundled *content* (Web 1 → Web 2) and *money* (Web 2 → Web 3), and is now in the early stages of unbundling *intelligence* (Web 3 → Web ∞). YeBlock LIM is the protocol layer of this third unbundling, in the same sense that HTTP and the EVM were the protocol layers of the first two. *See: [README — The Third Unbundling](../README.md#the-third-unbundling)*

### Verifiable Execution

The property that an operator's claim to have executed an inference can be independently checked — economically (via stake-slashing on detected deviation), statistically (via spot-check sampling), or cryptographically (via zkML or TEE attestation, in future tiers). Verifiable Execution is the mechanism by which YeBlock LIM replaces the trust assumption of "the operator did what they said" with a checked invariant.

---

## Style Note

Capitalized lexicon terms in protocol documents (`Receipt`, `Settlement Bundle`, `Stake Commitment`) refer to the precise definitions on this page. Lowercased forms in narrative documents (`receipt`, `settlement`) are the colloquial usage. When the two diverge, the lexicon wins.

## See Also

- [README](../README.md) — High-level project narrative.
- [ARCHITECTURE.md](../ARCHITECTURE.md) — System architecture and design invariants.
- [lim-protocol.md](./lim-protocol.md) — Full protocol specification.
