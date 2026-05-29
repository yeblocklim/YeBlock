# Contributing to YeBlock

Thank you for considering a contribution to YeBlock. This is the public documentation hub for the LIM protocol — every fix to a typo, every clarification of an ambiguous passage, and every well-argued protocol proposal makes the project measurably better.

This guide explains how to contribute productively. Read it once before opening a substantive PR; small fixes (typos, broken links, dead references) can skip most of it.

## Table of Contents

- [Ground Rules](#ground-rules)
- [Where to Start](#where-to-start)
- [Types of Contributions](#types-of-contributions)
- [Workflow](#workflow)
- [Documentation Style Guide](#documentation-style-guide)
- [Commit & PR Conventions](#commit--pr-conventions)
- [Code of Conduct](#code-of-conduct)
- [Licensing](#licensing)

---

## Ground Rules

YeBlock is a **protocol project**, not a startup blog. We hold documentation to the same standard as code: precise, durable, reviewable. The expectations below apply to every contribution, large or small.

1. **Discuss before you build.** Substantive changes (new sections, protocol proposals, restructuring) start as a [Discussion](https://github.com/yeblocklim/YeBlock/discussions) — not as a PR. This prevents wasted work on changes the maintainers will reject for reasons that could have been raised earlier.

2. **One change per PR.** PRs that mix typo fixes, structural refactors, and conceptual edits are hard to review and harder to revert if one piece breaks. Keep PRs focused.

3. **Small is good.** A 3-line typo PR is welcome. So is a 300-line documentation expansion. Both should be self-contained.

4. **English only.** All content in this repository is in English. Localized translations may live in sibling repositories, but the source-of-truth is English.

5. **Cite your sources.** Claims about prior art (e.g., "Bittensor does X", "Filecoin uses Y") must reference verifiable documentation. Vague hand-waves get rejected.

6. **No marketing fluff.** This is a protocol document, not a press release. "Revolutionary" / "groundbreaking" / "next-generation" are red flags; precise technical claims are not.

## Where to Start

If you want to contribute but are not sure where:

- **Documentation issues** labeled [`documentation`](https://github.com/yeblocklim/YeBlock/issues?q=is%3Aissue+is%3Aopen+label%3Adocumentation) and [`good first issue`](https://github.com/yeblocklim/YeBlock/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) are accessible entry points.
- **Open questions** in [`docs/lim-protocol.md` §10](./docs/lim-protocol.md#10-open-questions) list explicitly unresolved design questions. Substantive analysis on any of them is welcome — open a Discussion.
- **The lexicon** in [`docs/concepts.md`](./docs/concepts.md) is where new LIM-specific terms get defined. If you find a term used in the docs but missing from the lexicon, that's a contribution opportunity.

## Types of Contributions

| Type | Best Channel | Example |
|---|---|---|
| Typo, broken link, formatting glitch | **Direct PR** (no Discussion needed) | Fix `recieve` → `receive` |
| Clarification of an existing passage | **Direct PR**; Issue if the passage is ambiguous and you're not sure of the fix | Reword a confusing sentence |
| Adding a missing lexicon entry | **Direct PR** | Define `Cognitive Load` in `concepts.md` |
| Adding a new diagram | **Discussion first**, then PR | Add a sequence diagram for settlement disputes |
| New section in an existing document | **Discussion first**, then PR | Add a "Glossary by Pillar" appendix |
| Protocol design proposal | [**Protocol Proposal Issue**](https://github.com/yeblocklim/YeBlock/issues/new?template=protocol_proposal.yml) | Propose a new royalty-manifest field |
| Restructuring a document | **Discussion first** (high bar) | Split `lim-protocol.md` into multiple files |
| New top-level document | **Discussion first** (very high bar) | Add `GOVERNANCE.md` |

## Workflow

A typical contribution flows through these stages. Skip the ones that don't apply.

### 1. Discussion (for non-trivial changes)

Open a Discussion under the appropriate category. Describe:

- **What** you intend to change (concrete enough that a reader can disagree).
- **Why** it improves the documentation or protocol.
- **Alternatives** you considered.

Wait for at least one maintainer response before starting work. If you don't hear back in a week, ping the discussion politely.

### 2. Fork & Branch

Fork the repository to your account, then clone:

```bash
git clone https://github.com/<your-username>/YeBlock.git
cd YeBlock
git remote add upstream https://github.com/yeblocklim/YeBlock.git
```

Create a topic branch off `main`:

```bash
git checkout -b docs/clarify-pillar-3
```

Branch naming: `docs/<short-topic>` for documentation changes, `proposal/<short-topic>` for protocol proposals, `fix/<short-topic>` for typos and corrections.

### 3. Edit

Make your changes. See [Documentation Style Guide](#documentation-style-guide) below.

### 4. Verify Locally

Before committing:

- **Render check** — view your edits in a Markdown previewer that supports GitHub-Flavored Markdown and Mermaid. VS Code with the [Markdown Preview Mermaid Support](https://marketplace.visualstudio.com/items?itemName=bierner.markdown-mermaid) extension works.
- **Link check** — every relative link should resolve. Every external link should be reachable.
- **Spell check** — most editors handle this. Pay particular attention to LIM-specific terms in `docs/concepts.md`.

### 5. Commit

See [Commit & PR Conventions](#commit--pr-conventions) below for message format.

### 6. Push & Open PR

```bash
git push origin docs/clarify-pillar-3
```

Open a PR against `yeblocklim/YeBlock:main`. The PR template will prompt for:

- A summary of the change.
- A link to the originating Discussion (if applicable).
- A note on what was changed and why.

### 7. Review

A maintainer will review your PR within **7 days** (often much faster). Reviews are conducted in good faith and focus on the change itself, not the contributor. Common review outcomes:

- **Approved** — merged.
- **Approved with minor edits** — maintainer may push small tweaks before merging.
- **Needs revision** — review comments will explain. Push to the same branch; the PR updates automatically.
- **Closed** — rare; explanation will accompany the close.

## Documentation Style Guide

### Voice and Tone

- **Direct, declarative, technical.** Prefer `LIM defines X as Y` over `It is the opinion of the protocol that X might be Y`.
- **Active voice.** `The operator signs the receipt`, not `The receipt is signed by the operator`.
- **No marketing language.** No "innovative", "revolutionary", "next-generation", "groundbreaking". These are red flags in a protocol document.
- **Honesty about limits.** When something is unsettled, say so explicitly. The [`Open Questions`](./docs/lim-protocol.md#10-open-questions) section exists for this.

### Markdown Conventions

- **Headings** use ATX style (`# H1`, `## H2`). Maximum depth `####`. Each document has exactly one `# H1`.
- **Tables** are preferred for comparative or structured data. Use them generously.
- **Code blocks** specify a language (`bash`, `mermaid`, `text`). Untagged blocks are reserved for ASCII art.
- **Lists** use `-` for unordered, `1.` for ordered. Sub-items are indented two spaces.
- **Emphasis**: `**bold**` for the first occurrence of a key term in a passage; `*italic*` for emphasis or the names of works.
- **Line breaks**: hard-wrap at sentence boundaries; do not hard-wrap mid-sentence. This makes diffs readable.
- **Trailing whitespace**: none. Configure your editor to strip on save.
- **Final newline**: every file ends with exactly one `\n`.

### Diagrams

- **Mermaid is preferred** for sequence diagrams, flowcharts, and architectural overviews. SVG / PNG only when Mermaid cannot express what is needed.
- **Diagram source must be in the document**, not in an external file. Mermaid blocks render directly on GitHub.
- **Color and stroke styles** for class definitions follow the palette already in `ARCHITECTURE.md` (cyan `#4dd2ff`, purple `#a78bfa`, mint `#5fe2c6`, amber `#ffc460`). Match the existing scheme.

### Lexicon Discipline

When introducing a term that has a definition in [`docs/concepts.md`](./docs/concepts.md):

- The first appearance in a passage uses the **capitalized** form (`Receipt`, `Stake Commitment`).
- Subsequent appearances may use lowercase (`receipt`, `stake`).
- New term added to the docs **must** be defined in `docs/concepts.md` in the same PR. PRs that introduce capitalized terms without lexicon entries will be asked to add them.

## Commit & PR Conventions

### Commit Message Format

```
<type>(<scope>): <short summary>

<body — what changed and why>

<footer — issue references, breaking notes>
```

**Types:**

- `docs` — documentation changes
- `fix` — typo, broken link, factual error
- `feat` — new section, new diagram, new lexicon entry
- `refactor` — restructuring without semantic change
- `chore` — repository tooling (issue templates, CI config)

**Scope:** the file or area touched (e.g. `architecture`, `concepts`, `protocol`, `readme`).

**Examples:**

```
docs(architecture): clarify settlement choreography in §5
fix(concepts): correct hash function name in Content-Addressed Identity entry
feat(protocol): add §9.5 on post-quantum migration
chore(github): update issue template for proposal format
```

### PR Title

Same format as the commit. If the PR contains multiple commits, the title summarizes the whole.

### PR Body

The PR template will ask for:

1. **Summary** — what changed, in one paragraph.
2. **Motivation** — why this matters.
3. **Discussion link** — for non-trivial changes.
4. **Verification** — what you checked locally (rendering, link integrity).

### Sign-Off

By submitting a PR, you certify the [Developer Certificate of Origin](https://developercertificate.org/) — that you have the right to contribute the work under the project's license. We do not currently require an explicit `Signed-off-by:` line, but submission constitutes agreement.

## Code of Conduct

This project follows the [Contributor Covenant 2.1](./CODE_OF_CONDUCT.md). All contributors are expected to read and uphold it. Reports of unacceptable behavior go to `ye@yeblock.com`.

## Licensing

By contributing to this repository, you agree that your contribution is licensed under the same [MIT License](./LICENSE) that covers the rest of the repository. If your contribution incorporates work from another source, you must clearly attribute it and confirm that the source's license is compatible.

---

## Questions

If you've read this guide and still aren't sure how to proceed, open a Discussion in the **General** category and ask. Asking questions is itself a contribution — it surfaces ambiguity in this guide.

Welcome to YeBlock.
