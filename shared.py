"""Shared counting and rendering logic for the "fuck" counters.

Both the Codex scanner (``codex.py``) and the Junie scanner (``junie.py``)
import this module so the counting rules and the terminal report stay identical.
"""

from __future__ import annotations

import re
from collections import defaultdict


DEFAULT_WORD = "fuck"

# Alternate, censored, and slang spellings of the default word that do not
# contain the literal substring "fuck". The base substring already matches
# every derived form (fucking, fucked, fucker, fucks, motherfucker, ...).
_VARIANTS: dict[str, tuple[str, ...]] = {
    "fuck": (
        "fuk",
        "fck",
        "phuck",
        "f*ck",
        "f**k",
        "f***",
    ),
}


def _variant_pattern(word: str) -> str:
    """Return a regex alternation covering `word` and its known variations."""
    variants: set[str] = {word}
    variants.update(_VARIANTS.get(word.lower(), ()))
    return "|".join(re.escape(v) for v in sorted(variants, key=len, reverse=True))


def count_occurrences(text: str, word: str) -> int:
    """Count non-overlapping, case-insensitive occurrences of `word` in `text`.

    The match is a plain substring search, so a single pass covers every
    casing (``fuck``, ``FUCK``, ``Fuck``, ``fUcK``, ...) as well as every
    derived form (``fucking``, ``fucked``, ``fucks``, ``fucker``, ...).
    The default word (``fuck``) also matches common alternate and censored
    spellings (``fuk``, ``fck``, ``phuck``, ``f*ck``, ``f**k``, ``f***``, ...).
    """
    if not word:
        return 0
    return len(re.findall(_variant_pattern(word), text, flags=re.IGNORECASE))


class Counter:
    """Accumulates per-message word counts and per-bucket totals."""

    def __init__(self, word: str) -> None:
        self.word = word
        self.total = 0
        self.messages_with_word = 0
        self.per_bucket: dict[str, int] = defaultdict(int)

    def add(self, bucket_id: str, text: str) -> None:
        """Add one message, bucketed by its identifier (thread or session)."""
        occurrences = count_occurrences(text, self.word)
        if occurrences:
            self.messages_with_word += 1
            self.total += occurrences
            self.per_bucket[bucket_id] += occurrences


def render_report(
    source_lines: list[tuple[str, str]],
    total_messages: int,
    counter: Counter,
    bucket_label: str,
    breakdown: bool,
) -> None:
    """Print the terminal report for one scanner run."""
    for label, value in source_lines:
        print(f"{label} : {value}")

    print(f"User messages  : {total_messages}")
    print(f'Messages with "{counter.word}": {counter.messages_with_word}')
    print(f'Total "{counter.word}" said: {counter.total}')

    if breakdown and counter.per_bucket:
        print(f"\nPer-{bucket_label} breakdown:")
        for bucket_id, count in sorted(
            counter.per_bucket.items(), key=lambda kv: (-kv[1], kv[0])
        ):
            print(f"  {count:4d}  {bucket_id}")
