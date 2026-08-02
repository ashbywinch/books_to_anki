# Testing Standards — book_language_tools

Test conventions for the language-learning tools. Supplementary to `docs/coding-standards.md` — read both.

## Organization

Test files mirror the module under test (`src/book_to_flashcards/opencode_translator.py` → `test/src/test_opencode_translator.py`); functions describe behaviour (`test_only_untranslated_cards_are_sent`); classes group scenarios per unit (`TestOpenCodeGoTranslator`, `TestContextAwareBatching`). One-off manual drivers live in `test/src/call_*.py` and never run in CI.

## Deterministic Tests

Same result every run, any order, any machine:

- **No external APIs** — the translation API is injected via `urlopen=`; tests supply a `FakeUrlopen` returning canned responses.
- **No wall-clock time** — the translator's retry/split logic is tested by feeding scripted failures, not by sleeping.
- **No execution-order dependence** — each test sets up its own cards and tears down nothing shared. `--testmon` in the default pytest config skips unrelated tests; CI runs `--no-testmon` so the full suite always runs.
- **No filesystem dependence** — `pytest` `tmp_path` or `pyfakefs` (`fs` fixture) for tests that read/write files; never repo-relative paths.

## No Monkeypatching

**Never use `monkeypatch`, `unittest.mock.patch`, or `MockTransport` in tests** (the sole exception is environment access, e.g. `monkeypatch.setenv`/`delenv` for key lookup tests — prefer `tmp_path`-based fixtures where possible). They patch global state and break on import-path changes.

Use injection instead:

| Dependency | Injection point | Test fake |
|---|---|---|
| Translation API | `OpenCodeGoTranslator(urlopen=...)` | `FakeUrlopen` with scripted responses |
| Translators | `translate_cards(cards, translator, lang)` | `RecordingTranslator`, `ReverseTextTranslator` |
| spaCy pipeline | `cards_untranslated_from_file(..., nlp=nlp)` | real pipeline on tiny dummy books |
| Files | `pyfakefs` `fs` fixture | fake FS |

If something isn't reachable through injection, refactor the code to accept a dependency — don't add another patch.

## Fakes

- **`ReverseTextTranslator`** — trivial deterministic translator (reverses text) for pipeline tests; its output is verifiable by construction.
- **`RecordingTranslator`** — records `(texts, context, lang)` per call, returns trivial translations; use it to assert batching/context behaviour without the API.
- **`FakeUrlopen`** — a callable that pops canned responses (valid chat-completion payloads, invalid JSON, HTTP errors) and records requests; assert on `request.data` to verify the payload.

A fake must fake only the dependency, never the behaviour under test. A test that fakes `translate_cards` to test `translate_cards` always passes.

## Assertions

- Assert **behaviour**, not implementation — return values and card state, not which internal method was called or in what order.
- `assert` over `self.assert*`.
- `pytest.raises` for errors; verify the message when it's part of the contract. Catch the specific exception (`OpenCodeGoError`, `ValueError`) — never bare `Exception` (a test that passes for the wrong reason is worse than a failing test).
- `in` checks for partial error-message matches, not hardcoded full strings.

## Test Smells to Avoid

| Smell | Why wrong | Fix |
|---|---|---|
| `time.sleep()` | flaky, slow | script the fake's responses instead |
| hits the real API | non-hermetic, costs money, rate-limited | `urlopen=` fake |
| asserts full JSON response string | breaks on any formatting change | assert specific fields |
| requires internet | can't run offline | inject every external call |
| fakes the behaviour under test | always passes — fake is a fantasy of the real code | real implementation for code under test; fake only its dependencies |
| asserts implementation detail | breaks on refactors that don't change behaviour | assert return values and caller-visible state |
| re-translates already-translated cards | wastes quota and time | assert the skip behaviour explicitly |
