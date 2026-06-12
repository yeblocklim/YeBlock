// SPDX-License-Identifier: Apache-2.0
//
// Status: first-phase reference excerpt (pre-alpha). Interfaces and protocol logic only,
// not the production implementation, and subject to change as the spec matures.
// Scope and rationale: reference/README.md.
pragma solidity ^0.8.24;

/// @title IPaymentRail - YeBlock LIP payment streams, agent wallet policy, and A2A clearing
/// @notice Liquid Economy §11.3 (docs/lim-protocol.md). YeBlock LIP generalizes batched settlement
///         (ISettlement) into a machine-shaped rail. Its distinguishing property is inherited
///         from invariant I-5, extended: a receipt is the ONLY payment pre-image. Every
///         payment finalizes atomically with the signed receipt that justifies it; there is
///         no state in which one half exists without the other.
/// @dev    Honest boundaries (stated in the spec, restated here): rail throughput figures are
///         design-capacity targets pending public testnet measurement; the rail provides no
///         fiat on/off-ramps and does not target human retail payments; fee parameters
///         (including any burn schedule) are governance decisions, not protocol constants.
interface IPaymentRail {
    enum StreamUnit {
        Tokens,
        Seconds,
        Joules
    }

    struct Stream {
        bytes32 payer;
        bytes32 payee;
        uint256 ratePerUnit; // settlement-currency smallest units
        StreamUnit unit;
        bytes32 lastCheckpointReceipt; // zero before the first checkpoint
        bool open;
    }

    /// @notice Owner-set policy for an agent-held wallet. Enforced by the rail at validation
    ///         time: a payment outside policy is invalid regardless of agent behavior.
    struct WalletPolicy {
        bytes32 owner;
        bytes32 agent;
        uint256 perCallLimit;
        uint256 dailyLimit;
        bytes32[] allowlist; // empty = any payee
        bool revoked;
    }

    event StreamOpened(bytes32 indexed streamId, bytes32 indexed payer, bytes32 indexed payee);
    event StreamCheckpointed(bytes32 indexed streamId, bytes32 indexed receipt, uint256 accrued);
    event StreamClosed(bytes32 indexed streamId, uint256 totalSettled);
    event PolicySet(bytes32 indexed agent, bytes32 indexed owner);
    event PolicyRevoked(bytes32 indexed agent);
    event Cleared(bytes32 indexed payer, bytes32 indexed payee, bytes32 indexed receipt, uint256 amount);

    /// @notice Open a payment stream. Value accrues continuously at `ratePerUnit` and
    ///         checkpoints against signed receipts; a paused stream is a settled stream.
    function openStream(bytes32 streamId, Stream calldata stream) external;

    /// @notice Checkpoint a stream against a receipt covering the units consumed since the
    ///         last checkpoint. The checkpoint obeys the four receipt-validity conditions
    ///         (lim-protocol §6) unchanged; an invalid receipt reverts the checkpoint.
    function checkpoint(bytes32 streamId, bytes32 receipt, uint256 unitsConsumed) external;

    /// @notice Close a stream. Closing is itself a settlement act - the final checkpoint and
    ///         the close are one transaction.
    function closeStream(bytes32 streamId, bytes32 finalReceipt, uint256 unitsConsumed) external;

    /// @notice Set (or replace) the policy governing an agent wallet. Only the owner may set;
    ///         revocation is always available to the owner and takes effect immediately.
    function setPolicy(WalletPolicy calldata policy, bytes calldata ownerSignature) external;

    function revokePolicy(bytes32 agent, bytes calldata ownerSignature) external;

    /// @notice A2A clearing: pay `payee` exactly `amount` anchored to `receipt`. Reverts if
    ///         the receipt is invalid, already used as a payment pre-image (no double-pay),
    ///         or the payer's wallet policy rejects the transfer.
    function clear(bytes32 payer, bytes32 payee, uint256 amount, bytes32 receipt) external;

    /// @notice Batch form of {clear} for multi-agent pipelines: all legs land atomically or
    ///         none do (a pipeline cannot half-settle).
    function clearBatch(
        bytes32[] calldata payers,
        bytes32[] calldata payees,
        uint256[] calldata amounts,
        bytes32[] calldata receipts
    ) external;

    function streamOf(bytes32 streamId) external view returns (Stream memory);

    function policyOf(bytes32 agent) external view returns (WalletPolicy memory);

    /// @notice Remaining daily allowance for an agent at `timestamp` - the view the agent
    ///         itself plans spending against.
    function dailyRemaining(bytes32 agent, uint64 timestamp) external view returns (uint256);
}
