// SPDX-License-Identifier: Apache-2.0
//
// Status: first-phase reference excerpt (pre-alpha). Interfaces and protocol logic only,
// not the production implementation, and subject to change as the spec matures.
// Scope and rationale: reference/README.md.
pragma solidity ^0.8.24;

/// @title IIdeaRegistry - YeBlock LIME idea registration, escrow, and human-task lifecycle
/// @notice Liquid Economy §11.1 (docs/lim-protocol.md). An IdeaCapsule is an encrypted,
///         content-addressed idea with a public teaser. Registration is append-only and
///         PQ-signed; the block timestamp establishes Proof of Priority ("this idea existed,
///         authored by this identity, at this time"). Execution settles through the standard
///         receipt bundle (ISettlement); revenue replays the royalty waterfall with two added
///         seat classes: idea author and human executor(s).
/// @dev    The contract never sees idea plaintext (client-side encryption, Pillar 4). It
///         stores hashes, terms, and escrow state - nothing else. Capsules are immutable;
///         "editing" an idea means registering a derivative with `parents` set (lineage).
interface IIdeaRegistry {
    enum License {
        Buyout, // one-time transfer of execution rights
        LicensedExecution // author keeps ownership; perpetual royaltyBps applies
    }

    enum EscrowPhase {
        None,
        Funded,
        Executing,
        Settled,
        Refunded
    }

    struct Capsule {
        bytes32 author; // content-addressed identity
        string teaser; // the ONLY plaintext surface of the idea
        License license;
        uint256 ask; // asking price, settlement-currency smallest units
        uint16 royaltyBps; // author share in LicensedExecution mode
        bytes32[] parents; // idea lineage; revenue flows upstream (waterfall)
        bool exists;
    }

    struct HumanTask {
        bytes32 capsuleId;
        bytes32 stepId; // pipeline step outside model competence
        uint256 price;
        uint256 requiredStake; // slashed on "human-task-nondelivery" (IStakeVault)
        bytes32 executor; // zero until accepted
        bool delivered;
    }

    event CapsuleRegistered(bytes32 indexed capsuleId, bytes32 indexed author, uint64 priorityTimestamp);
    event CapsuleFunded(bytes32 indexed capsuleId, bytes32 indexed funder, uint256 amount);
    event HumanTaskPosted(bytes32 indexed capsuleId, bytes32 indexed stepId, uint256 price);
    event HumanTaskAccepted(bytes32 indexed stepId, bytes32 indexed executor);
    event CapsuleSettled(bytes32 indexed capsuleId);

    /// @notice Register an IdeaCapsule. Reverts if `capsuleId` exists (append-only) or if a
    ///         listed parent does not exist (lineage must be anchored).
    /// @param capsuleId Content hash of the ENCRYPTED idea payload.
    /// @param signature Forward-secure (PQ) signature by `capsule.author`; the algorithm tag
    ///        travels with the signature. Block timestamp becomes the Proof of Priority.
    function registerCapsule(
        bytes32 capsuleId,
        Capsule calldata capsule,
        bytes calldata signature
    ) external;

    /// @notice Lock escrow against a capsule. Decryption grant is an author-side act off-chain;
    ///         escrow releases only against validated execution receipts (machine and human).
    function fund(bytes32 capsuleId) external payable;

    /// @notice Post a pipeline step for human execution (Reverse Hiring). Callable only while
    ///         the capsule is in Executing phase.
    function postHumanTask(HumanTask calldata task) external;

    /// @notice Accept a human task by posting the required stake. The executor enters the same
    ///         receipt / QA / slashing regime as any operator.
    function acceptHumanTask(bytes32 stepId, bytes32 executor) external;

    /// @notice Settle the capsule against a finalized receipt bundle. Disburses escrow through
    ///         ISettlement with idea-author and human-executor seats included; transitions the
    ///         escrow phase to Settled. Reverts if any pipeline receipt failed validation.
    function settle(bytes32 capsuleId, bytes32 bundleId) external;

    function capsuleOf(bytes32 capsuleId) external view returns (Capsule memory);

    function escrowPhase(bytes32 capsuleId) external view returns (EscrowPhase);

    /// @notice Proof of Priority lookup: registration timestamp for an existing capsule.
    function priorityTimestamp(bytes32 capsuleId) external view returns (uint64);

    /// @notice Walk the idea lineage upward (for waterfall resolution). Bounded depth; the
    ///         off-chain mirror is reference/protocol/idea_market.py.
    function lineageOf(bytes32 capsuleId) external view returns (bytes32[] memory ancestors);
}
