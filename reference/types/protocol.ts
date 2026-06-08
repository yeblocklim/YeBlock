// SPDX-License-Identifier: Apache-2.0
//
// Status: first-phase reference excerpt (pre-alpha). Interfaces and protocol logic only,
// not the production implementation, and subject to change as the spec matures.
// Scope and rationale: reference/README.md.
//
// YeBlock LIM - Canonical protocol data model (reference)
//
// This file is the single, language-neutral-in-spirit definition of the objects that travel
// across the YeBlock LIM protocol. It is transcribed from docs/lim-protocol.md §2-§6 and the
// design invariants in ARCHITECTURE.md. Implementations in any language MUST preserve these
// field names, ordering semantics, and tag schemes on the wire.
//
// Nothing here performs cryptography or I/O - it is the shape, not the engine.

// ---------------------------------------------------------------------------
// §3.1  Content-addressed identity
// ---------------------------------------------------------------------------
//
// Every artifact is named solely by the hash of its bytes under a forward-secure hash.
// The identity is self-describing: "<hash-algorithm>:<lowercase-hex-digest>". A name registry
// does not exist; an identity cannot be re-pointed (invariant I-1).
//
// Example: "sha3-256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"

/** Hash algorithms permitted for content identity. Tagged for agility (I-3). */
export type HashTag = "sha3-256" | "blake3-256";

/** A content identifier: `${HashTag}:${hex}`. Branded to prevent accidental string mixing. */
export type ContentId = string & { readonly __brand: "ContentId" };

// ---------------------------------------------------------------------------
// §3.2  Forward-secure signatures  (invariant I-3)
// ---------------------------------------------------------------------------
//
// Every signed object verifies against its own algorithm tag, never a globally fixed scheme.
// Classical tags exist only inside hybrid combinations; a bare classical signature is not
// acceptable for settlement-bearing objects.
//
// FIPS mapping: ml-dsa-* = FIPS 204 (Dilithium), slh-dsa-* = FIPS 205 (SPHINCS+).

export type SignatureTag =
  | "ed25519" // classical; permitted only as the classical half of a hybrid
  | "ml-dsa-65" // post-quantum lattice signature (baseline)
  | "slh-dsa-sha2-128s" // hash-based signature (long-term archival)
  | "ed25519+ml-dsa-65"; // hybrid: both must verify

/** A public key, itself content-addressed so identities are stable across key formats. */
export type Identity = ContentId;

export interface ForwardSecureSignature {
  /** Which scheme produced `bytes`; verification dispatches on this tag. */
  readonly alg: SignatureTag;
  /** The signing identity (hash of the public key material). */
  readonly signer: Identity;
  /** Raw signature, hex-encoded. For hybrid tags this is the concatenation of both halves. */
  readonly bytes: string;
}

// ---------------------------------------------------------------------------
// §3.3  Encrypted channels  (Pillars 4 & 5)
// ---------------------------------------------------------------------------
//
// Session keys are derived from a hybrid KEM. The post-quantum half is mandatory, so traffic
// recorded today is not retroactively decryptable by a future quantum adversary (I-4).
//
// FIPS mapping: ml-kem-768 = FIPS 203 (Kyber-768).

export type KemTag =
  | "x25519" // classical; permitted only as the classical half of a hybrid
  | "ml-kem-768" // post-quantum KEM (baseline)
  | "x25519+ml-kem-768"; // hybrid; deployed default (matches X25519MLKEM768)

export interface ChannelOffer {
  readonly kem: KemTag;
  /** Recipient public key the initiator encapsulates against. */
  readonly recipient: Identity;
  /** KEM ciphertext, hex-encoded. */
  readonly encapsulation: string;
}

// ---------------------------------------------------------------------------
// §3.4  Stake commitments  (invariant I-7)
// ---------------------------------------------------------------------------

/** Roles that must post stake proportional to the damage they could cause. */
export type StakedRole = "operator" | "gateway" | "storage";

export interface StakeCommitment {
  readonly identity: Identity;
  readonly role: StakedRole;
  /** Settlement-chain address where collateral is locked. */
  readonly chainAddress: string;
  /** Locked amount, in the smallest unit of the settlement currency. */
  readonly amount: bigint;
  /** Enumerated violations that slash this stake. Open-ended by tag for agility. */
  readonly slashingConditions: ReadonlyArray<SlashingCondition>;
}

export type SlashingCondition =
  | "execution-deviation" // operator returned output inconsistent with spot-check
  | "receipt-forgery" // signed a receipt for work not performed
  | "replica-unavailable" // storage provider failed a proof of retrievability
  | "double-spend-receipt"; // submitted the same receipt to two bundles

// ---------------------------------------------------------------------------
// §4  Model identity & royalty manifests  (Pillar 3)
// ---------------------------------------------------------------------------
//
// A model identity is a deterministic composition expression whose result is itself
// content-addressed. LoRA adapters are commutative in the math but the protocol fixes a
// canonical order (lexicographic by adapter ContentId) so the same set yields the same
// identity and the same cache key (§4.2). See node/composition.py for the derivation.

export interface CompositionParams {
  /**
   * Per-adapter mix weight, keyed by adapter ContentId, in milli-units: 1000 == weight 1.0.
   * Integer so the model identity preimage is byte-identical across languages (floats are
   * not portably serializable). An absent adapter defaults to 1000.
   */
  readonly alphaMilli: Readonly<Record<ContentId, number>>;
}

export interface ModelIdentity {
  readonly base: ContentId;
  /** Adapters in CANONICAL order (lexicographic by ContentId). */
  readonly loras: ReadonlyArray<ContentId>;
  readonly params: CompositionParams;
  /** Cache key: H(base ‖ loras ‖ params). Recomputable by any participant. */
  readonly id: ContentId;
}

/** A single payout slice, in basis points (1 bp = 0.01%). */
export interface RoyaltySplit {
  readonly identity: Identity;
  readonly basisPoints: number; // sum across a manifest's `splits` MUST equal 10_000
}

export interface RoyaltyManifest {
  readonly author: Identity;
  /** Upstream artifacts this one derives from; their manifests also receive flow. */
  readonly parents: ReadonlyArray<ContentId>;
  readonly splits: ReadonlyArray<RoyaltySplit>;
  readonly constraints: {
    /** Floor an author may set per inference, in settlement-currency smallest units. */
    readonly minPerInference: bigint;
    /** Currency the author accepts settlement in. */
    readonly currencyClass: CurrencyClass;
  };
  /** Manifests are immutable; "editing" means publishing a new artifact (new ContentId). */
  readonly signature: ForwardSecureSignature;
}

export type CurrencyClass = "stable" | "native"; // e.g. USDC-class vs. the network token

// ---------------------------------------------------------------------------
// §6  Receipts & settlement  (invariants I-5, I-6)
// ---------------------------------------------------------------------------
//
// A receipt is a settlement instrument, not a log. It names the operator, the model, and the
// resources consumed, and is verifiable in O(log n) of the bundle it belongs to.

export type LatencyClass = "interactive" | "batch" | "bulk";

export interface ExecutionReceipt {
  readonly workloadId: ContentId;
  readonly modelIdentity: ContentId;
  readonly operatorIdentity: Identity;
  readonly bytesIn: number;
  readonly bytesOut: number;
  readonly latencyClass: LatencyClass;
  /** Unix milliseconds; checked against the operator's stake validity window. */
  readonly timestamp: number;
  readonly operatorSignature: ForwardSecureSignature;
}

export interface SettlementBundle {
  /** Protocol version; gates wire format and mandatory algorithms (§8). */
  readonly version: number;
  readonly periodStart: number;
  readonly periodEnd: number;
  readonly receipts: ReadonlyArray<ExecutionReceipt>;
  /** Signature of the aggregator that assembled the bundle. */
  readonly aggregatorSignature: ForwardSecureSignature;
}

/**
 * The four conditions under which a receipt is valid at settlement (§6). A bundle's receipts
 * are admitted iff each satisfies all four; failing receipts are dropped at validation and
 * consume no chain resources. The concrete predicate lives in node/receipts.py; this type is
 * the interface a settlement client checks against.
 */
export interface ReceiptValidator {
  signatureVerifies(r: ExecutionReceipt): boolean;
  stakeIsCurrentAt(operator: Identity, timestamp: number): boolean;
  modelResolvesToLiveManifest(modelIdentity: ContentId): boolean;
  notPreviouslyFinalized(workloadId: ContentId): boolean;
}
