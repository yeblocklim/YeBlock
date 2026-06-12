// SPDX-License-Identifier: Apache-2.0
//
// Status: first-phase reference excerpt (pre-alpha). Interfaces and protocol logic only,
// not the production implementation, and subject to change as the spec matures.
// Scope and rationale: reference/README.md.
pragma solidity ^0.8.24;

/// @title IEnergyCredit - YeBlock LEM energy attestation, JouleCredit minting, and hosting splits
/// @notice Liquid Economy §11.2 (docs/lim-protocol.md). YeBlock LEM converts energy advantage into
///         network advantage IN PLACE: the protocol never moves, schedules, or settles
///         physical electricity. This interface covers the two on-chain surfaces:
///         (1) Path C - metered, TEE-attested contributions mint JouleCredits (fungible
///             within their green class; retired against power costs or ESG compliance);
///         (2) Path B - two-seat hosting splits (hardware seat / energy seat), enforced
///             inside the operator payout at settlement so neither party custodies the
///             other's share.
/// @dev    Metering detail stays encrypted; only window aggregates are public. Attestations
///         are PQ-signed for decade-scale audit validity. Over-reporting is the slashing
///         condition "energy-over-report" (IStakeVault), verified by redundant-meter
///         cross-checks - the same economics as compute verification.
interface IEnergyCredit {
    struct Attestation {
        bytes32 meterIdentity; // TEE-resident metering key (staked role: energy-meter)
        uint64 windowStart;
        uint64 windowEnd;
        uint64 joules;
        bool greenCertified;
        bytes teeQuote; // attestation that metering ran in-enclave (vendor-tagged)
    }

    struct HostingSplit {
        bytes32 hardwareSeat;
        bytes32 energySeat;
        uint16 hardwareBps; // hardware share; energy seat receives 10_000 - hardwareBps
    }

    event AttestationAccepted(bytes32 indexed attestationId, bytes32 indexed meterIdentity, uint64 joules);
    event CreditMinted(bytes32 indexed creditId, bytes32 indexed attestationId, bool greenCertified);
    event CreditRetired(bytes32 indexed creditId, bytes32 indexed retiredBy, uint8 reason);
    event HostingSplitRegistered(bytes32 indexed nodeIdentity, bytes32 hardwareSeat, bytes32 energySeat);

    /// @notice Submit a metered attestation. Reverts if the meter's stake is not current, the
    ///         TEE quote fails verification, or the window overlaps a previously accepted one
    ///         (no double-minting a time window).
    /// @param signature Forward-secure (PQ) signature by the meter identity.
    function submitAttestation(
        bytes32 attestationId,
        Attestation calldata attestation,
        bytes calldata signature
    ) external;

    /// @notice Mint a JouleCredit from a validated attestation, 1:1 with attested joules.
    ///         Credits are fungible within their `greenCertified` class.
    function mint(bytes32 attestationId) external returns (bytes32 creditId);

    /// @notice Retire a credit. Retirement is terminal: reasons are 0 = power-cost offset
    ///         (operators), 1 = ESG compliance (green credits only).
    function retire(bytes32 creditId, uint8 reason) external;

    /// @notice Register a two-seat revenue split for a node ("has power, no hardware" hosting).
    ///         The split is enforced by ISettlement inside the operator payout; updating the
    ///         ratio requires signatures from BOTH seats.
    function registerHostingSplit(
        bytes32 nodeIdentity,
        HostingSplit calldata split,
        bytes calldata hardwareSignature,
        bytes calldata energySignature
    ) external;

    function creditOf(bytes32 creditId)
        external
        view
        returns (uint64 joules, bool greenCertified, bytes32 retiredBy);

    function hostingSplitOf(bytes32 nodeIdentity) external view returns (HostingSplit memory);

    /// @notice Total attested joules for a meter within a window - the cross-check surface
    ///         redundant meters audit against (slashing on divergence).
    function attestedJoules(bytes32 meterIdentity, uint64 windowStart, uint64 windowEnd)
        external
        view
        returns (uint64);
}
