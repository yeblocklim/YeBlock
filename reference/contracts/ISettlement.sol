// SPDX-License-Identifier: Apache-2.0
//
// Status: first-phase reference excerpt (pre-alpha). Interfaces and protocol logic only,
// not the production implementation, and subject to change as the spec matures.
// Scope and rationale: reference/README.md.
pragma solidity ^0.8.24;

/// @title ISettlement - Atomic settlement of execution-receipt bundles
/// @notice The convergence point of all five pillars. Transcribed from docs/lim-protocol.md §6
///         and invariant I-6 ("Royalties Settle Atomically with Compute"). Receipts are batched
///         into a bundle and paid out in a single transaction: the compute operator's payout,
///         the storage providers' fees, and every LoRA author's royalty are dispatched together.
///         There is no staging period in which any party holds funds owed to another.
/// @dev    Settlement is batched (not per-request) to keep the on-chain footprint sub-linear in
///         inference volume - the same choreography as an optimistic rollup; only the attested
///         object differs. Heavy post-quantum signature verification runs in an algorithm-agile
///         verifier module (a precompile or pluggable contract), selected by the signature's tag.
interface ISettlement {
    enum LatencyClass {
        Interactive,
        Batch,
        Bulk
    }

    /// @dev Mirrors ExecutionReceipt in reference/types/protocol.ts and node/receipts.py.
    struct ExecutionReceipt {
        bytes32 workloadId;
        bytes32 modelIdentity;
        bytes32 operatorIdentity;
        uint64 bytesIn;
        uint64 bytesOut;
        LatencyClass latencyClass;
        uint64 timestamp;
        bytes operatorSignature; // self-describing; algorithm tag travels in the encoding
    }

    struct SettlementBundle {
        uint8 version;
        uint64 periodStart;
        uint64 periodEnd;
        ExecutionReceipt[] receipts;
        bytes aggregatorSignature;
    }

    /// @notice Network-level reward split, in basis points (the returned tuple always sums to
    ///         10_000). The concrete weights are set by governance and are not fixed by this
    ///         interface. The per-artifact author split is separate and lives in IRoyaltyRegistry.
    /// @dev    The split covers compute, loraAuthors, liquidityProviders, storage, verification,
    ///         protocol, and referral. Live values are governance-configured; see tokenomics.
    function networkSplitBps()
        external
        view
        returns (
            uint16 compute,
            uint16 loraAuthors,
            uint16 liquidityProviders,
            uint16 storageProviders,
            uint16 verification,
            uint16 protocol,
            uint16 referral
        );

    event BundleSettled(bytes32 indexed bundleId, uint64 periodEnd, uint256 receiptsAdmitted);
    event ReceiptRejected(bytes32 indexed workloadId, string reason);
    event ChallengeOpened(bytes32 indexed bundleId, address indexed challenger);

    /// @notice Submit a bundle for settlement. The contract verifies the aggregator signature,
    ///         then for each receipt enforces the four §6 validity conditions:
    ///           1. operator signature verifies against its tag,
    ///           2. operator stake was current at the receipt timestamp (IStakeVault),
    ///           3. the model identity resolves to a live manifest (IRoyaltyRegistry),
    ///           4. the workload was not previously finalized (dedup).
    ///         Failing receipts are dropped (ReceiptRejected) and consume no further resources;
    ///         admitted receipts are paid atomically per `networkSplitBps` and the artifact
    ///         manifests. Returns the count admitted.
    function submitBundle(SettlementBundle calldata bundle) external returns (uint256 admitted);

    /// @notice Open the dispute window for a settled bundle; challengers post counter-evidence.
    function challenge(bytes32 bundleId, bytes calldata evidence) external;

    /// @notice Whether a workload has already been paid in a finalized bundle (dedup view).
    function isFinalized(bytes32 workloadId) external view returns (bool);
}
