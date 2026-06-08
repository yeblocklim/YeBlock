// SPDX-License-Identifier: Apache-2.0
//
// Status: first-phase reference excerpt (pre-alpha). Interfaces and protocol logic only,
// not the production implementation, and subject to change as the spec matures.
// Scope and rationale: reference/README.md.
pragma solidity ^0.8.24;

/// @title IStakeVault - Stake commitments and slashing
/// @notice Pillars 1 (Compute) and 2 (Storage). Implements invariant I-7 ("Stake is the Unit
///         of Trust"): every party whose misbehavior could damage another posts collateral
///         proportional to the damage it could cause. The protocol extends no trust on social,
///         contractual, or reputational grounds - only on slashable stake.
/// @dev    This is an interface, not a deployment. Concrete contracts open together with their
///         first third-party audit (see ../../README.md#repository-map).
interface IStakeVault {
    enum Role {
        Operator,
        Gateway,
        Storage
    }

    /// @dev Mirrors SlashingCondition in reference/types/protocol.ts.
    enum SlashingCondition {
        ExecutionDeviation,
        ReceiptForgery,
        ReplicaUnavailable,
        DoubleSpendReceipt
    }

    struct Commitment {
        bytes32 identity; // content-addressed identity the stake secures
        Role role;
        uint256 amount; // locked collateral, in settlement-currency smallest units
        uint64 lockedFrom; // validity window start (unix seconds)
        uint64 lockedUntil; // 0 ⇒ open-ended until withdrawal request
    }

    event Staked(bytes32 indexed identity, Role indexed role, uint256 amount);
    event WithdrawalRequested(bytes32 indexed identity, uint64 effectiveAt);
    event Withdrawn(bytes32 indexed identity, uint256 amount);
    event Slashed(
        bytes32 indexed identity,
        SlashingCondition indexed reason,
        uint256 amount,
        address beneficiary
    );

    /// @notice Lock collateral for `identity` in `role`. Sets the upper bound on the cost of
    ///         its misbehavior.
    function stake(bytes32 identity, Role role, uint256 amount) external;

    /// @notice Begin the unbonding timer. Stake remains slashable during the cooldown so that
    ///         in-flight receipts stay backed.
    function requestWithdrawal(bytes32 identity) external;

    /// @notice Complete withdrawal after the cooldown, if no challenge is pending.
    function withdraw(bytes32 identity) external;

    /// @notice Slash a committed identity. Callable only by the authorized settlement /
    ///         challenge module. Slashed funds flow to the harmed party and/or protocol treasury.
    function slash(
        bytes32 identity,
        SlashingCondition reason,
        uint256 amount,
        address beneficiary
    ) external;

    /// @notice The validity check used by settlement: was `identity` continuously staked at
    ///         `timestamp`? This is the on-chain counterpart of StakeOracle in node/receipts.py.
    function stakeIsCurrentAt(bytes32 identity, uint64 timestamp) external view returns (bool);

    function commitmentOf(bytes32 identity) external view returns (Commitment memory);
}
