# Writing Documentation Guide

For anyone writing/updating project documentation.

## Context Efficiency

Every doc contains only what's relevant to its single topic and audience. Before writing, answer:

- Who is this for? (dev running the pipeline, agent implementing a feature, contributor adding a translation backend)
- What single question does it answer?
- What does this audience NOT need?

Content for a different audience/topic goes in its own doc — cross-reference by **linking**, never by copying.

Humans AND AI agents must both navigate from `readme.md` and `CONTRIBUTING.md` to find what they need.

### Signs of violation

- Two distinct audiences in one doc
- Two unrelated topics
- Temptation to copy-paste content from another doc
- Reader must skip large sections
- A concept explained twice (within a doc or across docs)

## SOLID/DRY for docs

| Principle | Rule |
|---|---|
| **Single source of truth** | Each fact lives in exactly one place; other docs link, never repeat |
| **One topic per file** | Subtopic for a different audience → separate file + link |
| **Avoid redundancy** | Exists elsewhere? Link. Doesn't exist? Most logical home, link from others |
| **Delete, don't archive** | Obsolete = wrong = remove. No "legacy" renames, no deprecation notices |
| **Docs match code** | Rename a function/module/CLI flag → update docs in the same commit |
| **API keys never in docs** | Keys live in the environment or opencode's auth file — never document values |

## Checklist

- [ ] Single, clearly stated audience
- [ ] Single, clearly stated topic
- [ ] No content belonging to a different doc
- [ ] No duplicated content from other docs (link instead)
- [ ] Every section relevant to the stated audience
- [ ] Title + first paragraph make purpose clear
- [ ] Links to related docs where readers might need them

## Density & Concision

Docs are read inside a limited AI context window. Every sentence costs context. Write for density: the smallest set of words that preserves every fact and decision.

| Technique | Rule | ✗ Low-density | ✓ High-density |
|---|---|---|---|
| **Rules as explicit negatives** | State constraints as prohibitions, not preferences — "Never X" reads faster, followed more reliably | "Avoid swallowing errors silently when catching exceptions" | "**Never swallow errors.** Every `except` must log, re-raise, or handle observably" |
| **Commands over prose** | Executable commands beat descriptive sentences | "To translate a book, run the translate command with a language option" | "`book-to-flashcard from-text book.txt pipeline ru_core_news_sm translate --lang English to-jsonl out.jsonl`" |
| **Tables over prose** | Rule-per-row beats paragraph-per-rule; use when facts have consistent fields | prose bullets | state/meaning, layer/rule/files, fake/default tables |
| **Canonical ✗/✓ pairs** | One right/wrong code pair teaches more than enumerating edge cases | list every failure mode | `# ✗ string parsing` / `# ✓ structured` pair |
| **One-line contracts** | A contract that fits one line is easier to hold in context | three sentences of explanation | "`translate_cards(cards, lang, context)` MUST return one translation per card, in order" |
| **Decision-relevant context only** | Keep only background that changes a decision; cut filler and restated motivation | "The pipeline was originally built for DeepL and…" | (omitted) |
| **Link, don't paste** | A fact lives in one place; other docs link | copy the CLI reference inline | "see `readme.md`" |
| **Task-card structure** | For how-to sections: goal (one verb), scope (exact paths), constraints (must/never), acceptance (verifiable command) | narrative walkthrough | Goal / Scope / Constraints / Acceptance headings |

### Size ceilings

Always-loaded files (`readme.md`, `CONTRIBUTING.md`, this doc, skill bodies) target **~150–200 lines / <32 KiB** — loaded in full every session, so bloat is paid every session. Referenced docs (pulled in only when relevant, e.g. `docs/card-pipeline.md`) can be longer, but densify prose first; density matters less for them than for always-loaded files.

### Density checklist

- [ ] Every sentence carries a fact, a decision, or a constraint
- [ ] Rules are explicit negatives ("Never X"), not vague preferences
- [ ] Commands replace descriptions where executable
- [ ] Tables replace paragraphs where fields are consistent
- [ ] Code shows a canonical ✗/✓ pair, not exhaustive cases
- [ ] No filler, no restated motivation
- [ ] Always-loaded files within the ~150–200 line ceiling

## How to update

1. Identify audience + topic.
2. Find the existing doc for that audience/topic.
3. No doc exists → create one with a clear single purpose.
4. Add content in the right place.
5. Update cross-references (`readme.md`, `CONTRIBUTING.md`, reference tables).
6. Check nothing duplicated that belongs elsewhere.
7. Verify humans and agents find it starting from `readme.md`/`CONTRIBUTING.md`.
