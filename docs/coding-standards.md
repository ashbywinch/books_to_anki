# Coding Standards — book_language_tools

Project-specific rules supplementing the shared coding standards. Read both. If they conflict, this file takes precedence.

## Design Principles

| Principle | Rule |
|---|---|
| **Separation of concerns** | One reason to change per module/class/function. Splitting text, translating, and writing output live in different modules with one-way dependency chains. Mixing I/O with computation = split, not shortcut. |
| **Cohesive classes** | `Card` owns its invariants: `title`/`author` identify the book, `start`/`end` are character offsets into the source file, `text` is the front, `translation` is the back. Nothing outside the card pipeline reaches into a Card's fields to compute derived values. |
| **Names communicate intent** | Domain names, not shapes: `cards_untranslated_from_file` not `make_cards_3`. Classes = domain nouns (`Card`, `Translator`); functions = verbs (`translate_cards`, `split_text`); booleans read in `if` clauses. |
| **Anti-fragile: correct by construction** | Pure functions preferred; error paths explicit; never suppress type-checker flags; happy path reads naturally. Signs of coincidental correctness: works only in your test env, ordering "happens to work", unwritten rules ("always call X before Y"). |

## The Pipeline Is the Architecture

The CLI is a chained Click pipeline of processor generators: input (`from-folder`) → `pipeline` (text → Cards) → optional `translate`/`dummy-translate` → output (`to-jsonl`/`to-anki`). Each command is a thin wrapper returning a generator that consumes and yields Cards. Conventions:

| Code | Does | Never does |
|---|---|---|
| Input commands | yield file paths | process text |
| `pipeline` | split files into untranslated Cards | translate |
| `translate` | add translations to Cards | change card text or offsets |
| Output commands | consume Cards, write files | call the translation API |

A new processing step that fits this shape belongs in the pipeline, not in a bespoke script.

## Card Model

`Card(title, author, start, end, text, translation="")` — dataclass; `translation == ""` means "not translated". The full contract (tiling, translation-skip semantics, JSONL round-trip) lives in `docs/card-pipeline.md` ("The Card Contract").

## Translators

`Translator` (in `translate_cards.py`) is the interface: `translate_cards(cards, lang, context="") -> list[str]`, one translation per card, in order. Conventions:

- **Batch, never per-card.** `batch_size` bounds how many cards go in one API call; a translator that makes one round trip per card is wrong.
- **Context is read-only input.** The `context` string is the text preceding the batch in its book — use it to resolve pronouns and references, never to echo content back.
- **`translate_text` is the legacy string-level interface** used by the dummy translator and tests; new translators implement `translate_cards`.
- **Never mutate the input cards' `text` or `start`/`end`.** Assign `card.translation` only.
- **Failures must be observable.** Log every failed batch with the book and batch size. The retry/split recovery contract lives in `docs/card-pipeline.md`.

## API Keys & Secrets

Environment or opencode's auth file only. **Never read, log, print, echo, or store keys** in context, files, code, output, cache keys, URLs, or request bodies — headers only. Redact keys from error messages before logging. The translator resolves its key via `find_api_key()` (`OPENCODE_API_KEY` env, then opencode's `auth.json`); it never accepts a key as a CLI argument or logs it.

## Error Handling

- **Never swallow errors.** Every `except` block must log, re-raise, or handle observably. Bare `except: pass` / silent `except Exception:` forbidden. Safe-to-ignore errors log at `DEBUG` with an explanation.
- **Log all translation failures** (book, batch size, exception) — a silent gap in the JSONL is a broken deck.
- **Fail fast**: don't pre-validate before trying; let code fail naturally. Missing API key → the API's 403 propagates as a normal error.

## Determinism

- **Sort file listings** before processing (`sorted(glob(...))`). `glob.glob` order is filesystem-dependent; a test or output that depends on it is a bug.
- No wall-clock dependence, no execution-order dependence in tests.
- Output JSONL key order comes from the `Card` dataclass; keep the dataclass field order stable — it is the serialization contract.

## No Backward Compatibility Shims

Delete dead code, don't deprecate it. Rename/remove + update every caller in the same commit. No aliases, no re-exports, no "will remove in a future version".

## Dependency Injection over Patching

Where a leaf depends on an external thing (the LLM API, spacy), inject it: `OpenCodeGoTranslator(urlopen=...)` for the API, `nlp=...` for the spacy pipeline. Never `monkeypatch`/`unittest.mock.patch` in tests — if something isn't reachable through injection, refactor the code to accept a dependency. See `docs/testing-standards.md`.

## Python Version

This package targets Python 3.9 (`requires-python = "==3.9.*"` — note the `.*`; `==3.9` matches only 3.9.0). No syntax newer than 3.9 without a `from __future__ import annotations` guard.
