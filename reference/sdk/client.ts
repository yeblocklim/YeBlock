// SPDX-License-Identifier: Apache-2.0
//
// Status: first-phase reference excerpt (pre-alpha). Interfaces and protocol logic only,
// not the production implementation, and subject to change as the spec matures.
// Scope and rationale: reference/README.md.
//
// YeBlock LIM - Reference SDK shape (TypeScript)
//
// "Boring at the edges" (ARCHITECTURE.md Design Goals): application developers should reach the
// protocol through the YeBlock LIM API (Mesh SDK) without having to learn protocol internals.
// All five pillars are inherited by default - content-addressed weights, LoRA composition,
// end-to-end encryption, post-quantum channel security, and on-chain settlement happen below
// this surface.
//
// This is the interface contract of `@yeblock/sdk`, not its implementation. The transport,
// key management, and receipt verification are provided by the concrete package; here we fix
// the shape application code is written against.

import type {
  ContentId,
  Identity,
  KemTag,
  LatencyClass,
  ExecutionReceipt,
  IdeaCapsule,
  IdeaLicense,
  EscrowPhase,
  JouleCredit,
  PaymentStream,
  StreamUnit,
  AgentWalletPolicy,
} from "../types/protocol";

/** Identifier of a base model on the network (resolves to a content hash). */
export type ModelRef = string; // e.g. "lim-8b"

/** Identifier of a LoRA adapter on the network. */
export type LoraRef = string; // e.g. "legal-contract-v1"

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface PrivacyOptions {
  /**
   * End-to-end encryption is non-optional (invariant I-4): the gateway and operator only ever
   * carry ciphertext. This selects the channel *tier*, not whether encryption happens.
   *  - "e2ee"        : default. Operator runs inference but never sees plaintext keys.
   *  - "confidential": Phase B. Execution is pinned to TEE-attested operators (medical / legal
   *                    / financial workloads). Adds latency; restricts the eligible operator set.
   */
  tier?: "e2ee" | "confidential";
  /** Hybrid KEM to negotiate. Defaults to the deployed hybrid (x25519+ml-kem-768). */
  kem?: KemTag;
}

export interface CompletionRequest {
  /** Base model. */
  model: ModelRef;
  /** LoRA stack; applied in the protocol's canonical order regardless of array order. */
  loras?: LoraRef[];
  /** Per-adapter mix weights in milli-units (1000 == 1.0), keyed by LoraRef. Absent ⇒ 1000. */
  alphaMilli?: Record<LoraRef, number>;
  messages: ChatMessage[];
  temperature?: number;
  /** Scheduling hint; influences routing and price, not correctness. */
  latencyClass?: LatencyClass;
  privacy?: PrivacyOptions;
}

export interface Usage {
  promptTokens: number;
  completionTokens: number;
  /** Settled cost for this call, in the chosen currency's smallest unit. */
  cost: bigint;
  currency: "USDC" | "native";
}

export interface CompletionResponse {
  /** The content-addressed model identity actually served (base + canonical LoRA stack). */
  servedModelIdentity: ContentId;
  /** Identity of the operator that executed the workload. */
  operator: Identity;
  message: ChatMessage;
  usage: Usage;
  /**
   * The signed execution receipt for this call. A client can verify, offline and on a phone,
   * that the work it paid for was the work it received (I-5). See node/receipts.py.
   */
  receipt: ExecutionReceipt;
}

/** A streamed chunk; the final chunk carries the receipt and usage. */
export type CompletionChunk =
  | { delta: string; done: false }
  | { done: true; response: CompletionResponse };

export interface ChatCompletions {
  create(req: CompletionRequest): Promise<CompletionResponse>;
  stream(req: CompletionRequest): AsyncIterable<CompletionChunk>;
}

export interface YeBlockClientOptions {
  /** API credential for a gateway. Gateways are interchangeable; none is privileged. */
  apiKey: string;
  /** Optional explicit gateway endpoint. Defaults to the reference YeBlock gateway. */
  gateway?: string;
  /**
   * Client-side keypair used to terminate end-to-end encryption. If omitted, the SDK generates
   * an ephemeral one per session. The gateway never receives the private half.
   */
  identityKey?: { publicKey: string; privateKey: string };
}

// ---------------------------------------------------------------------------
// Liquid Economy surfaces (design-stage; lim-protocol §11)
// ---------------------------------------------------------------------------

/** YeBlock LIME - publish, fund, and track encrypted ideas. The SDK encrypts the payload client-side
 *  before upload; the gateway and the protocol only ever see the hash and the teaser. */
export interface Ideas {
  /** Encrypt + upload the payload, register the capsule, return the on-chain record. The
   *  registration timestamp is the author's Proof of Priority. */
  publish(req: {
    payload: Uint8Array;
    teaser: string;
    license: IdeaLicense;
    ask: bigint;
    royaltyBps?: number;
    parents?: ContentId[];
  }): Promise<IdeaCapsule>;
  /** Escrow funds against a capsule (decryption grant is the author's act, not the SDK's). */
  fund(capsuleId: ContentId): Promise<{ phase: EscrowPhase }>;
  /** Track an execution: machine steps, posted human tasks, receipts, settlement. */
  status(capsuleId: ContentId): Promise<{ phase: EscrowPhase; receipts: ExecutionReceipt[] }>;
}

/** YeBlock LIP - agent wallet and streaming payments. Policy is enforced by the rail at validation
 *  time; the SDK cannot spend outside the owner-set policy even if asked to. */
export interface Payments {
  policy(): Promise<AgentWalletPolicy>;
  /** Open a streaming payment (pay-per-token / per-second / per-joule). */
  openStream(req: {
    payee: Identity;
    ratePerUnit: bigint;
    unit: StreamUnit;
  }): Promise<PaymentStream>;
  /** Close a stream; the final checkpoint and the close are one settlement act. */
  closeStream(streamId: ContentId): Promise<{ totalSettled: bigint }>;
}

/** YeBlock LEM - energy credit market access (Path C). Operators buy credits to offset power costs;
 *  ESG-constrained buyers retire green-attested credits. */
export interface Energy {
  /** Quote available credits for a window, optionally green-certified only. */
  quote(req: { joules: bigint; greenOnly?: boolean }): Promise<{ credits: JouleCredit[]; cost: bigint }>;
  /** Retire a held credit (0 = power-cost offset, 1 = ESG compliance). */
  retire(creditId: ContentId, reason: 0 | 1): Promise<void>;
}

/**
 * Entry point. YeBlock's own Mesh SDK surface; every request is content-addressed, LoRA-composed, end-to-end encrypted,
 * post-quantum-protected, and settled on-chain underneath. The Liquid Economy surfaces
 * (`ideas`, `payments`, `energy`) are design-stage and ship behind capability flags.
 *
 * @example
 *   const client = new YeBlock({ apiKey: process.env.YEBLOCK_API_KEY! });
 *   const res = await client.chat.create({
 *     model: "lim-8b",
 *     loras: ["legal-contract-v1"],
 *     messages: [{ role: "user", content: "Review this lease agreement..." }],
 *     privacy: { tier: "confidential" },
 *   });
 *   console.log(res.message.content);
 *   console.log(`cost: ${res.usage.cost} ${res.usage.currency}`);
 */
export declare class YeBlock {
  constructor(options: YeBlockClientOptions);
  readonly chat: ChatCompletions;
  /** YeBlock LIME (design-stage). */
  readonly ideas: Ideas;
  /** YeBlock LIP (design-stage). */
  readonly payments: Payments;
  /** YeBlock LEM (design-stage). */
  readonly energy: Energy;
}
