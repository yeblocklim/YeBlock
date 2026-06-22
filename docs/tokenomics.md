# Tokenomics

> **Status: design-stage.** Every figure on this page is a **design target**, not a realized
> commitment. Final parameters — supply release schedule, allocation splits, fee/burn rates, and
> the network reward split — are subject to **DAO governance** once it is live. YBT is **not yet
> issued**. Nothing here is investment advice or a promise of return.
>
> This page is the concrete source for the values that the protocol interfaces reference abstractly
> (e.g. `ISettlement.networkSplitBps()` is documented as *"governance-configured; see tokenomics"*).

YBT is the YeBlock network token, used for staking, settlement, and governance. Consistent with
[*What YeBlock LIM Is Not* → "a token-first design"](../README.md#what-yeblock-lim-is-not), the
protocol does not depend on any particular token market price and works with any liquid settlement
currency; the parameters below describe how the network token is allocated and how value flows, not
a price model.

---

## 1. Supply

**Total supply: 121,000,000 YBT (fixed, non-inflationary).**

More than half of the supply is directed to miners, nodes, and other network contributors, to
reward real compute, storage, and referral contribution.

---

## 2. Allocation

| Allocation | YBT | Share |
|---|---:|---:|
| Distributed Referral Mining | 30,000,000 | 24.8% |
| VC (Venture Capital) | 14,520,000 | 12.0% |
| YeBlock Foundation | 15,730,000 | 13.0% |
| TGE (Token Generation Event) | 21,000,000 | 17.4% |
| Node | 14,000,000 | 11.6% |
| Staking | 12,000,000 | 9.9% |
| Contribution Mining | 9,000,000 | 7.4% |
| Ecosystem Partnerships / Grants / Growth | 4,750,000 | 3.9% |
| **Total** | **121,000,000** | **100%** |

---

## 3. Vesting & Anti-Exit

| Bucket | Share | Vesting |
|---|---:|---|
| YeBlock Foundation (team) | 13% | 3-year vesting + 1-year cliff |
| VC | 12% | 3-year vesting + 1-year cliff |

**Anti-exit design.** After team YBT unlocks, it is intended to be **re-staked**, with the team
sustained by staking rewards rather than by selling. If unlocked YBT is not re-staked, DAO
governance may vote to send part of the Foundation's YBT to a burn address (ratio set by vote). If
team YBT must be sold to fund operations, the **sell ratio and timing are decided by DAO vote**. The
treasury is multisig-managed and publicly audited.

---

## 4. Deflation

Up to **40% of net protocol ecosystem revenue** is allocated to **open-market buyback of YBT,
followed by permanent burn**, continuously reinforcing a deflationary mechanism. The exact rate is a
governance parameter, not a protocol constant.

---

## 5. Network Reward Split

When an inference settles, the network-level reward is split across seven roles. These are the live
values behind `ISettlement.networkSplitBps()` (the returned tuple always sums to 10,000 basis
points). The concrete weights are governance-configured; the per-artifact author royalty is separate
and lives in `IRoyaltyRegistry`.

| Role | Share |
|---|---:|
| Compute | 30% |
| LoRA authors | 15% |
| Liquidity providers | 15% |
| Storage | 13% |
| Verification | 2% |
| Protocol | 15% |
| Referral | 10% |
| **Total** | **100%** |

---

## 6. Disclaimer

All allocations, ratios, and schedules above are **target designs**; final parameters are determined
by **DAO governance**. YBT is currently unissued. This document describes mechanism and economic
design only and is **not** investment advice or a guarantee of any return.
