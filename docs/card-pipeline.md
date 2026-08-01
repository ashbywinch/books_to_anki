# Card Pipeline Reference

**For:** developers adding or changing the book → cards → translations → deck pipeline.

The pipeline: `.txt` files → spaCy splitting → `Card`s → translation (OpenCode Go API) → JSONL/Anki. API surface lives in the code — `src/book_to_flashcards/*.py`. This doc records the **rules and conventions** that aren't discoverable from the code.

## The Card Contract

`Card(title, author, start, end, text, translation="")` — see `src/book_to_flashcards/Card.py`.

- `start`/`end` are **absolute character offsets** into the source `.txt`.
- Cards tile their book in order: `card[n].end == card[n+1].start`. A gap or overlap is a bug. `cards_skip_first_line_if_author` re-offsets deliberately (adjusts `start` by the removed author line).
- `translation == ""` means "not translated". **A non-empty translation is never sent to the API again.** Never clear it to force a retry.
- JSONL is the persistence format; fields map 1:1 (see `src/book_to_flashcards/cards_jsonl.py`). Files are written per book as `<author>/<title>.jsonl`, atomically (write `.tmp`, then `os.replace`).

## Text Splitting

`src/split_sentences/split_sentences.py` — spaCy-based chunking:

- `nlp.pipe(file)` processes the file **one line per Doc**; `split_text` consolidates across lines into `CrossDocSpan`s with global offsets.
- `maxfieldlen` (CLI `--maxfieldlen`, default 70) caps chunk length; chunks aim for grammatical coherence (dependency-tree consolidation), not uniform length.
- **Verse behaves differently from prose**: poems without sentence punctuation split into fewer, longer chunks than prose at the same `maxfieldlen`. Not a bug.
- The `ru_core_news_sm` pipeline is the default for the Russian books; `make_nlp` excludes `lemmatizer`/`ner`/`attribute_ruler` and adds the `tidy_punctuation` component. Load the pipeline once and pass `nlp=` when processing many books — never per file.

## Translation Contract

`Translator.translate_cards(cards, lang, context="") -> list[str]` — one translation per card, in order, with the preceding book text as `context`.

### Batching and context (`src/book_to_flashcards/translate_cards.py`)

- Cards are grouped by book (title+author); **batches never mix books**.
- Each batch is translated with the text of the previous `context_cards` (default 10) cards of the same book prepended as context — resolves mid-sentence starts, pronouns, register.
- Only cards with empty `translation` are sent; already-translated cards pass through untouched (this is what makes re-runs safe and cheap).
- Batch size is the translator's `batch_size` (OpenCode Go default 60 — the API reliably truncates larger outputs).

### OpenCode Go translator (`src/book_to_flashcards/opencode_translator.py`)

- Direct OpenAI-compatible calls to `https://opencode.ai/zen/go/v1`; key via `find_api_key()` (env `OPENCODE_API_KEY`, else opencode's `auth.json`).
- **`thinking: {"type": "disabled"}` is sent by default** — deepseek-v4-flash otherwise burns the whole output budget on reasoning and returns empty content for large batches. If a model rejects the param (HTTP 400/422), the client retries once without it.
- **Response contract**: the model must return a JSON array `[{"index": N, "translation": "..."}]` covering exactly indices `1..len(cards)`. Fences/prose around the JSON are tolerated; missing, duplicate, or extra indices are a failure.
- **Failure recovery**: log every failure (book, batch size, error) → retry the whole batch once → split in half, recurse (bounded depth 6) → a single card gets one more attempt → raise. A batch that raises leaves no partially-written cards (cards are only emitted after their batch's translations return).
- **Never translate per card in a loop.** If the API is flaky, the recovery splits; per-card calls are the last resort inside recovery only.

### Persistence during long runs

When translating many books in one process: **persist each completed batch immediately** (append + flush to the book's JSONL). A crash at any point must leave a valid partial file whose cards are all translated — the next run loads it and translates only what's missing. Never buffer an entire book in memory before writing.

## Anki Output (`src/book_to_flashcards/cards_to_anki.py`)

- The Anki note model is "Book Snippet": `index_in_file`, `file`, `prev`, `current`, `next`, `translation`. `prev`/`next` give the surrounding context on the card.
- `cards_to_anki` writes intermediate results to the `.apkg` if the translation API fails mid-deck (`OpenCodeGoError`), so a long deck build isn't lost.

## CLI Pipeline

`book-to-flashcard` is a chained Click pipeline; each command wraps a processor generator. The canonical translation flow:

```
book-to-flashcard from-folder data/books pipeline ru_core_news_sm \
  translate --lang English to-jsonl data/translations
```

- `translate` options: `--lang` (free-text target, default `English`), `--model` (default `deepseek-v4-flash`).
- `dummy-translate` reverses text — for pipeline testing without API cost.
- Re-running translation on an already-translated JSONL is a no-op (card-level skip).
