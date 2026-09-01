"""
Local, dependency-free stub for an LLM summarizer.

In production this would call an LLM to generate a summary.
"""

from __future__ import annotations

import re
from typing import Iterable

MAX_PER_MESSAGE = 80
MAX_TOTAL = 600

#: A sentence ends at .!? followed by whitespace or end-of-string.
_SENTENCE_END = re.compile(r"[.!?](\s|$)")


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "\u2026"


def summarize(messages: Iterable[str]) -> str:
    """Reduce a conversation to the first sentence of each message."""
    first_sentences: list[str] = []
    for raw in messages:
        trimmed = raw.strip()
        if not trimmed:
            first_sentences.append("")
            continue
        match = _SENTENCE_END.search(trimmed)
        sentence = trimmed if match is None else trimmed[: match.start() + 1]
        first_sentences.append(_truncate(sentence, MAX_PER_MESSAGE))

    joined = " ".join(s for s in first_sentences if s)
    return _truncate(joined, MAX_TOTAL)
