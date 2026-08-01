"""Translation through the OpenCode Go API (deepseek models).

This is a thin OpenAI-compatible client that talks directly to the OpenCode Go
endpoint (https://opencode.ai/zen/go/v1) with the key opencode stores in its
auth file, so no ``opencode`` CLI process or server is needed. It uses only the
standard library.

Cards are translated in numbered batches inside a single request, with the
preceding text of the book included as context, which keeps round trips low
while letting the model resolve pronouns and references correctly.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Callable

from .Card import Card
from .translate_cards import Translator

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://opencode.ai/zen/go/v1"
DEFAULT_MODEL = "deepseek-v4-flash"

# Providers whose api keys opencode may have stored in its auth.json.
AUTH_JSON_PROVIDER_HINTS = ("opencode-go", "opencode")

_SYSTEM_PROMPT = """\
You are a professional literary translator. Translate the source fragments \
into {lang}. Be faithful to the source: keep names, tone and register, and do \
not add or drop content. If a fragment is verse, translate it as verse, line \
by line, keeping every line. \
The fragments come from "{title}" by {author} and are in reading order; they \
may begin or end mid-sentence, so use the provided CONTEXT to resolve \
pronouns, references and phrasing correctly. Translate every fragment, even \
if the CONTEXT or the fragment itself is fragmentary. \
Translate EACH fragment IN FULL: every line and every sentence of a fragment \
must be translated, in order. NEVER summarize, condense, or translate only \
the first sentence or first line of a fragment: a partial translation is an \
error, not an acceptable answer. At the same time keep the translation \
faithful but not padded: do not add explanatory or filler words - it should \
be close to the source in length. \
For EVERY fragment, also include a "source" field containing its opening \
words, copied VERBATIM from the FRAGMENTS list (about the first 24 \
characters of the fragment, ignoring leading whitespace). Copy those \
characters EXACTLY - do not normalize, correct, or modernize the opening \
words, even if they look archaic, misspelled, or foreign. This lets us check \
that each translation is paired with the right fragment. \
Respond with ONLY a JSON array of objects, one per fragment, in the same \
order, like this: [{{"index":1,"source":"...","translation":"..."}}]"""

_USER_PROMPT = """\
CONTEXT (the text immediately before the fragments to translate):
{context}

FRAGMENTS:
{fragments}

Translate ALL {count} fragments above into {lang} and respond with ONLY the \
JSON array of {{ "index": N, "source": "...", "translation": "..." }} \
objects, exactly one object per fragment (exactly {count} objects, in \
order). The "source" field must be the VERBATIM opening of the corresponding \
fragment (about the first 24 characters, ignoring leading whitespace) - not \
a translation of it. Never omit a fragment; if one is impossible to \
translate, use an empty string for it. \
\
Before you finish, CHECK YOUR WORK: for each of the {count} objects, verify \
that its "translation" covers the ENTIRE fragment - every line and every \
sentence, in order - and that its "source" field matches the fragment with \
the same number. A translation that covers only the first line or first \
sentence, that condenses or summarizes the fragment, or that is paired with \
the wrong fragment, is WRONG. If any object is wrong, rewrite it correctly \
before responding. Only after every fragment has a complete, correctly \
paired translation may you respond."""


class OpenCodeGoError(RuntimeError):
    """Raised when the OpenCode Go API cannot be used."""


class OpenCodeGoTranslator(Translator):
    """Translates cards via the OpenCode Go chat completions API."""

    # Batch size is capped well below the API's comfortable output size: the
    # model reliably stops early (dropping the last few fragments) on larger
    # batches, and the retry/split recovery then wastes calls.
    batch_size = 60

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str | None = None,
        max_tokens: int = 12000,
        timeout: float = 600.0,
        max_retries: int = 2,
        urlopen: Callable[..., Any] | None = None,
        disable_thinking: bool = True,
        batch_size: int | None = None,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key if api_key is not None else find_api_key()
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.max_retries = max_retries
        self.disable_thinking = disable_thinking
        if batch_size is not None:
            self.batch_size = batch_size
        # injectable for tests
        self._urlopen = urlopen or urllib.request.urlopen

    # -- API plumbing -----------------------------------------------------

    def _chat(self, system: str, user: str) -> str:
        """One chat completion call; returns the assistant text."""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": self.max_tokens,
        }
        if self.disable_thinking:
            # deepseek-v4-flash otherwise spends its whole output budget on
            # reasoning and returns empty translations for large batches
            payload["thinking"] = {"type": "disabled"}
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                # Cloudflare in front of the API rejects the urllib default UA
                "User-Agent": "opencode/1.14.20",
            },
            method="POST",
        )
        delay = 2.0
        for attempt in range(self.max_retries + 1):
            try:
                with self._urlopen(request, timeout=self.timeout) as response:
                    data = json.loads(response.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503, 529) and attempt < self.max_retries:
                    time.sleep(delay)
                    delay *= 2
                    continue
                if (
                    e.code in (400, 422)
                    and self.disable_thinking
                    and payload.get("thinking")
                ):
                    # model doesn't understand the thinking param - retry without it
                    logger.warning(
                        "model %s rejected the thinking param (HTTP %d); retrying without it",
                        self.model, e.code,
                    )
                    payload.pop("thinking")
                    request.data = json.dumps(payload).encode("utf-8")
                    continue
                raise OpenCodeGoError(
                    f"OpenCode Go API error {e.code}: {e.read().decode('utf-8', 'replace')[:200]}"
                ) from e
        else:  # pragma: no cover - only reachable if retries exhaust without break
            raise OpenCodeGoError("OpenCode Go API request failed after retries")
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise OpenCodeGoError(f"Unexpected API response: {json.dumps(data)[:300]}") from e
        if not content or not content.strip():
            # e.g. the model spent its whole budget on reasoning, or the
            # service returned an empty completion - treat as retryable
            raise OpenCodeGoError(
                f"Empty response from API (finish_reason={data.get('choices', [{}])[0].get('finish_reason')})"
            )
        return content
    # -- translation ------------------------------------------------------

    def translate_cards(
        self, cards: Sequence[Card], lang: str, context: str = ""
    ) -> list[str]:
        """Translate a same-book batch of cards with preceding-text context."""
        return self._translate_batch_with_retries(
            [card.text for card in cards], lang, context, title=cards[0].title, author=cards[0].author
        )

    def _translate_batch_with_retries(
        self, texts: Sequence[str], lang: str, context: str, title: str, author: str, depth: int = 0
    ) -> list[str]:
        """Translate a batch, retrying once whole, then splitting on failure.

        Every failure is logged with the book and batch size. Splitting is
        bounded (depth < 3) so a persistently broken batch costs at most a
        handful of extra calls; a single card gets one more attempt before the
        error is raised to the caller.
        """
        try:
            return self._translate_batch(texts, lang, context, title, author)
        except (OpenCodeGoError, TypeError, ValueError) as e:
            logger.warning(
                "Translation failed for %s (%d cards, depth %d): %s",
                title, len(texts), depth, e,
            )
        # one retry of the whole batch - transient API hiccups often clear here
        try:
            return self._translate_batch(texts, lang, context, title, author)
        except (OpenCodeGoError, TypeError, ValueError) as e:
            logger.warning(
                "Retry failed for %s (%d cards, depth %d): %s",
                title, len(texts), depth, e,
            )
            # Split until single cards: dense prose batches have been observed
            # to truncate the model's output even at 7 cards, and a single
            # card's translation always fits the output budget. Depth 6 lets
            # a 60-card batch degrade all the way down to one card per call
            # instead of failing the whole book. Each half keeps the context
            # of the text that precedes it: the second half gets the first
            # half's text appended to the incoming context, so split cards
            # never lose the immediately preceding text for pronouns and
            # references.
            if len(texts) == 1 or depth >= 6:
                raise
            mid = len(texts) // 2
            first = self._translate_batch_with_retries(
                texts[:mid], lang, context, title, author, depth + 1
            )
            second = self._translate_batch_with_retries(
                texts[mid:],
                lang,
                context + "".join(texts[:mid]),
                title,
                author,
                depth + 1,
            )
            return first + second

    def _translate_batch(
        self, texts: Sequence[str], lang: str, context: str, title: str, author: str
    ) -> list[str]:
        fragments = "\n".join(f"[{i}] {text}" for i, text in enumerate(texts, start=1))
        system = _SYSTEM_PROMPT.format(lang=lang, title=title, author=author)
        user = _USER_PROMPT.format(
            context=context, fragments=fragments, lang=lang, count=len(texts)
        )

        response = self._chat(system, user)
        parsed = parse_translation_response(response, len(texts))
        translations = [""] * len(texts)
        for (index, (source, translation)), text in zip(parsed, texts):
            if not _source_matches(source, text):
                # the model paired a translation with the wrong fragment
                raise ValueError(
                    f"Misaligned response for fragment {index}: "
                    f"source {source[:20]!r} does not match {text[:20]!r}"
                )
            translations[index - 1] = translation
        return translations


def find_api_key() -> str:
    """Return the OpenCode Go API key from the environment or opencode's auth file."""
    env_key = os.environ.get("OPENCODE_API_KEY")
    if env_key:
        return env_key

    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", "")) / "opencode"
    else:
        data_home = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local/share")
        base = Path(data_home) / "opencode"
    auth_path = base / "auth.json"
    if auth_path.exists():
        try:
            auth = json.loads(auth_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            auth = {}
        for hint in AUTH_JSON_PROVIDER_HINTS:
            entry = auth.get(hint)
            if isinstance(entry, dict) and entry.get("type") == "api" and entry.get("key"):
                return entry["key"]
    raise OpenCodeGoError(
        "No API key found. Set the OPENCODE_API_KEY environment variable, or "
        "log in with `opencode` (its auth file is read automatically)."
    )


def parse_translation_response(response: str, expected: int) -> list[tuple[int, tuple[str, str]]]:
    """Parse the model's numbered translation list.

    Returns a list of (index, (source, translation)) pairs, 1-based. Raises
    ValueError (or TypeError for structurally malformed entries) if the
    response is not a JSON array of {index, source, translation} objects
    covering every index 1..expected exactly once. The "source" field is the
    model's verbatim echo of the fragment opening, used to verify alignment.
    """
    text = response.strip()
    # The model often wraps the JSON in markdown fences or adds prose.
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end <= start:
        # the model sometimes emits the objects bare, without the array
        # wrapper: "{...}\n{...}" - wrap the brace span and retry
        first_brace, last_brace = text.find("{"), text.rfind("}")
        if first_brace != -1 and last_brace > first_brace:
            # separate the bare objects (which may be newline-joined) with
            # commas before wrapping in an array
            text = "[" + re.sub(r"}\s*{", "},{", text[first_brace : last_brace + 1]) + "]"
            start, end = 0, len(text) - 1
        else:
            raise ValueError(f"No JSON array in response: {response[:200]!r}")
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as e:
        raise ValueError(f"Response is not valid JSON: {text[start:end+1][:200]!r}") from e

    if not isinstance(data, list):
        raise TypeError(f"Expected a JSON array, got {type(data).__name__}")
    by_index: dict[int, tuple[str, str]] = {}
    for item in data:
        if not isinstance(item, dict):
            raise TypeError(f"Expected objects in array, got {type(item).__name__}")
        index = item.get("index")
        translation = item.get("translation")
        source = item.get("source", "")
        if not isinstance(index, int) or not isinstance(translation, str):
            raise TypeError(f"Malformed entry: {item!r}")
        by_index[index] = (source, translation)
    if set(by_index) != set(range(1, expected + 1)):
        raise ValueError(
            f"Expected indices 1..{expected}, got {sorted(by_index)}"
        )
    return sorted(by_index.items())


def _normalize(text: str) -> str:
    """Lowercase and collapse whitespace, for fuzzy prefix comparison."""
    return "".join(text.split()).lower()


def _edits_leq(a: str, b: str, max_edits: int) -> bool:
    """Is the Levenshtein distance between ``a`` and ``b`` at most ``max_edits``?

    Early-exits once the running row's minimum exceeds the bound, so a truly
    different string (e.g. a shifted card's source) fails fast instead of
    computing a full table.
    """
    if abs(len(a) - len(b)) > max_edits:
        return False
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        row_min = i
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            v = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            cur.append(v)
            row_min = min(row_min, v)
        if row_min > max_edits:
            return False
        prev = cur
    return prev[-1] <= max_edits


def _source_matches(source: str, text: str) -> bool:
    """Does the model's echoed source match the opening of the expected card?

    The model is asked to copy the first ~24 characters of each fragment
    verbatim; we accept a fuzzy match because it may trim leading
    punctuation/whitespace, echo the prompt's "[N] " numbering, or
    transcribe a character slightly differently (e.g. "сестрою" vs
    "сестрой" - observed in production, where an exact-prefix check caused
    a retry loop). Both strings are normalized and leading non-alphanumeric
    characters are skipped.

    A longer echoed source is far more distinctive, so a long echo is
    matched against the card's opening with at most 2 character edits; a
    short echo falls back to a 12-character prefix or 1-edit match. A truly
    shifted card differs by far more than a couple of edits, so this stays a
    real alignment check.
    """
    s = _normalize(source)
    t = _normalize(text)
    s = s.lstrip("0123456789—–-«»\"'().,:;!?…[]")
    t = t.lstrip("0123456789—–-«»\"'().,:;!?…[]")
    if not s:
        return False
    if len(s) >= 24:
        return _edits_leq(s, t[: len(s)], 2)
    return t.startswith(s[:12]) or _edits_leq(s[:12], t[:12], 1)
