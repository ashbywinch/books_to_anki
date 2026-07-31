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
not add or drop content. If a fragment is a verse line, translate it as verse. \
The fragments come from "{title}" by {author} and are in reading order; they \
may begin or end mid-sentence, so use the provided CONTEXT to resolve \
pronouns, references and phrasing correctly. Translate every fragment, even \
if the CONTEXT or the fragment itself is fragmentary. Respond with ONLY a \
JSON array of objects, one per fragment, in the same order, like this: \
[{{"index":1,"translation":"..."}}]"""

_USER_PROMPT = """\
CONTEXT (the text immediately before the fragments to translate):
{context}

FRAGMENTS:
{fragments}

Translate ALL {count} fragments above into {lang} and respond with ONLY the \
JSON array of {{ "index": N, "translation": "..." }} objects, exactly one \
object per fragment (exactly {count} objects, in order). Never omit a \
fragment; if one is impossible to translate, use an empty string for it."""


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
            if len(texts) == 1 or depth >= 3:
                raise
            mid = len(texts) // 2
            first = self._translate_batch_with_retries(
                texts[:mid], lang, context, title, author, depth + 1
            )
            second = self._translate_batch_with_retries(
                texts[mid:], lang, context, title, author, depth + 1
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
        for index, translation in parsed:
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


def parse_translation_response(response: str, expected: int) -> list[tuple[int, str]]:
    """Parse the model's numbered translation list.

    Returns a list of (index, translation) pairs, 1-based. Raises ValueError (or
    TypeError for structurally malformed entries) if the response is not a JSON
    array of {index, translation} objects covering every index 1..expected
    exactly once.
    """
    text = response.strip()
    # The model often wraps the JSON in markdown fences or adds prose.
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end <= start:
        raise ValueError(f"No JSON array in response: {response[:200]!r}")
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as e:
        raise ValueError(f"Response is not valid JSON: {text[start:end+1][:200]!r}") from e

    if not isinstance(data, list):
        raise TypeError(f"Expected a JSON array, got {type(data).__name__}")
    by_index: dict[int, str] = {}
    for item in data:
        if not isinstance(item, dict):
            raise TypeError(f"Expected objects in array, got {type(item).__name__}")
        index = item.get("index")
        translation = item.get("translation")
        if not isinstance(index, int) or not isinstance(translation, str):
            raise TypeError(f"Malformed entry: {item!r}")
        by_index[index] = translation
    if set(by_index) != set(range(1, expected + 1)):
        raise ValueError(
            f"Expected indices 1..{expected}, got {sorted(by_index)}"
        )
    return sorted(by_index.items())
