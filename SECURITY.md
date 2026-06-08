# Security Policy

> **Reporting a vulnerability:** Email **`ye@yeblock.com`**. Do not open a public issue.
>
> We will acknowledge receipt within 72 hours and provide a remediation timeline within 7 days.

---

## Scope

This security policy covers:

- The contents of **this repository** (documentation, specifications, protocol design).
- The **YeBlock reference web application** at [yeblock.com](https://yeblock.com) and its associated APIs.
- Any **YeBlock-operated infrastructure** (gateways, settlement aggregators, reference services).

This policy **does not** cover:

- Third-party services we depend on (Cloudflare, Reown, etc.) — please report those directly to the respective vendor.
- Issues in user-operated nodes, gateways, or applications built on top of YeBlock LIM. Those are the responsibility of their operators.
- Theoretical weaknesses in standardized cryptographic primitives we use (e.g. ML-KEM, Dilithium). Coordinate with the standards bodies (NIST, IETF) instead.

If you are unsure whether something is in scope, **err on the side of reporting it**. We will route it appropriately.

## How to Report

### What to include

A useful report typically contains:

1. **A clear description** of the vulnerability and what it allows an attacker to do.
2. **Reproduction steps** — exact URLs, payloads, configuration, or browser/device state. Reproducible reports are fixed faster.
3. **Impact assessment** — which systems are affected, how severe the worst-case outcome is, and any conditions or prerequisites required.
4. **Suggested mitigation**, if any. (Optional — we will design our own, but suggestions are appreciated.)
5. **Your preferred contact** for follow-up correspondence.

### Where to send it

| Channel | When to use |
|---|---|
| **Email — `ye@yeblock.com`** | All vulnerability reports. The default channel. |
| **PGP-encrypted email** | If you require encrypted transport, request our current public key in your initial unencrypted email; we will respond with the key fingerprint. |
| **GitHub Security Advisory** | If the vulnerability is in this repository specifically and you prefer GitHub's coordinated disclosure flow, use [private vulnerability reporting](https://github.com/yeblocklim/YeBlock/security/advisories/new). |

**Do not** report security issues through:

- Public GitHub Issues
- Public GitHub Discussions
- Social media (Twitter/X, Telegram, Discord)
- Customer support channels

These are public surfaces. Disclosure on them puts users at risk.

## Our Response Process

We aim to respond to all reports on a fixed timeline. The clock starts when your initial email reaches `ye@yeblock.com`.

| Stage | Timeline | What happens |
|---|---|---|
| **Acknowledgment** | Within **72 hours** | We confirm receipt and assign a tracking reference. If you have not heard back, please assume the email did not arrive and resend. |
| **Initial assessment** | Within **7 days** | We confirm whether the report is in scope, classify severity, and provide an initial remediation timeline. |
| **Remediation** | Severity-dependent (see below) | We fix the vulnerability, deploy the fix, and verify with the reporter where appropriate. |
| **Public disclosure** | After remediation, with reporter's consent | We publish a security advisory with credit to the reporter (unless anonymity is requested). |

### Severity guidance

| Severity | Examples | Target remediation |
|---|---|---|
| **Critical** | Remote code execution, unauthenticated user account takeover, settlement-layer fund theft, private key exposure | **≤ 7 days** |
| **High** | Authenticated privilege escalation, sensitive data leak (private user data, internal infrastructure config), authentication bypass for non-critical actions | **≤ 30 days** |
| **Medium** | XSS / CSRF in non-critical surfaces, denial of service against a single user account, information disclosure of non-sensitive metadata | **≤ 60 days** |
| **Low** | Best-practice violations without direct impact, hardening recommendations, theoretical issues without practical attack | **≤ 90 days** or next major release |

These are targets. Complex issues may take longer; we will keep you informed if a timeline slips.

## Coordinated Disclosure

We follow a **coordinated disclosure** model:

1. The reporter privately discloses the issue to us.
2. We investigate, remediate, and deploy a fix.
3. After the fix is deployed and (where relevant) users have had time to update, the issue is published as a security advisory.
4. The reporter is credited unless they request anonymity.

If you intend to publish your findings independently (e.g. as a research paper, conference talk, or blog post), please:

- Notify us in your initial report so we can coordinate timelines.
- Allow us a reasonable window to remediate before public disclosure (the default is **90 days from the initial report**, extendable by mutual agreement for complex issues).
- Avoid disclosing reproduction details that would enable active exploitation against current users until a fix is deployed.

We will work with you in good faith on timing. We will not retaliate against good-faith research, and we will not pursue legal action against researchers who follow this policy.

## Bug Bounty

YeBlock does not currently operate a paid bug bounty program. We are working through pre-alpha; a formal bounty program will be announced when the network reaches mainnet readiness.

In the interim, we recognize researchers in the following ways:

- **Public credit** in security advisories (with consent).
- **Hall of fame** listing on this repository (planned).
- **Discretionary rewards** for high-impact reports — case-by-case, evaluated against the severity, novelty, and quality of the report. Contact `ye@yeblock.com` to discuss.

## Safe Harbor

Research conducted under this policy is considered:

- **Authorized** by YeBlock for testing scope as defined above.
- **Exempt** from any restrictions in our Terms of Service that would otherwise prohibit such testing, to the extent applicable.
- **In good faith** when conducted in compliance with this policy.

You are expected to:

- Not access, modify, or destroy data belonging to others.
- Not perform attacks that degrade service for legitimate users (DoS, spam, social engineering of YeBlock staff or users).
- Not exfiltrate more data than necessary to demonstrate the issue.
- Stop and report immediately if you encounter user data, payment information, or anything that suggests you have access beyond the intended scope of your test.

If you act in good faith and within these boundaries, we will not pursue legal action.

---

## Questions

Anything in this policy unclear? Email `ye@yeblock.com` and ask. Clarifying the policy is itself a contribution to security.

*Last updated: 2026-05*
