// SPDX-License-Identifier: Apache-2.0
//
// Status: first-phase reference excerpt (pre-alpha). Interfaces and protocol logic only,
// not the production implementation, and subject to change as the spec matures.
// Scope and rationale: reference/README.md.
pragma solidity ^0.8.24;

/// @title IRoyaltyRegistry - Royalty manifests for authored artifacts
/// @notice Pillar 3 (Decentralized AI). Transcribed from docs/lim-protocol.md §4.3. Every
///         author-published artifact (base model, LoRA adapter) carries a signed, immutable
///         royalty manifest. Settlement honors manifests automatically; there is no opt-out at
///         the protocol layer (invariant I-6: royalties settle atomically with compute).
/// @dev    Manifests are content-addressed. "Editing" a manifest means publishing a new
///         artifact with a new identity; the old manifest keeps governing the old artifact.
interface IRoyaltyRegistry {
    /// @notice One payout slice. `basisPoints` across a manifest MUST sum to 10_000 (100%).
    struct Split {
        bytes32 identity; // recipient (content-addressed)
        uint16 basisPoints;
    }

    struct Manifest {
        bytes32 author;
        bytes32[] parents; // upstream artifacts this one derives from
        Split[] splits;
        uint256 minPerInference; // author-set floor, settlement-currency smallest units
        uint8 currencyClass; // 0 = stable (USDC-class), 1 = native
        bool exists;
    }

    event ManifestRegistered(bytes32 indexed artifact, bytes32 indexed author);

    /// @notice Register the manifest for `artifact`. Reverts if `artifact` already has one
    ///         (immutability) or if `splits` do not sum to 10_000 basis points.
    /// @param signature Forward-secure signature over the manifest by `author` (verified via
    ///        the algorithm-agile verifier; tag travels with the signature).
    function register(
        bytes32 artifact,
        Manifest calldata manifest,
        bytes calldata signature
    ) external;

    /// @notice True iff `artifact` resolves to a live manifest. On-chain counterpart of
    ///         ManifestResolver in node/receipts.py and a receipt-validity condition (§6).
    function isLive(bytes32 artifact) external view returns (bool);

    function manifestOf(bytes32 artifact) external view returns (Manifest memory);

    /// @notice Flatten an artifact's manifest (and its parents') into absolute payout slices for
    ///         a given gross amount. Pure helper used by ISettlement during disbursement.
    function resolveSplits(bytes32 artifact, uint256 grossAmount)
        external
        view
        returns (Split[] memory recipients, uint256[] memory amounts);
}
