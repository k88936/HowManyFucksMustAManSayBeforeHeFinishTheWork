"""Shared counting and rendering logic for the "fuck" counters.

Both the Codex scanner (``codex.py``) and the Junie scanner (``junie.py``)
import this module so the counting rules and the terminal report stay identical.
"""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_WORD = "fuck"

# How many conversations to render when --md-dir is given without an explicit --top.
DEFAULT_TOP = 10


def positive_int(value: str) -> int:
    """argparse type for an integer that must be at least 1."""
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not an integer") from None
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


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


@dataclass(frozen=True)
class BucketStat:
    """Word count, total user-input length, and derived frequency for one bucket."""

    bucket_id: str
    count: int
    length: int

    @property
    def frequency(self) -> float:
        """Occurrences per character of user input (0 when the bucket has none)."""
        return self.count / self.length if self.length else 0.0


class Counter:
    """Accumulates per-message word counts and per-bucket totals."""

    def __init__(self, word: str) -> None:
        self.word = word
        self.total = 0
        self.messages_with_word = 0
        self.per_bucket: dict[str, int] = defaultdict(int)
        self.per_bucket_length: dict[str, int] = defaultdict(int)

    def add(self, bucket_id: str, text: str) -> None:
        """Add one message, bucketed by its identifier (thread or session)."""
        self.per_bucket_length[bucket_id] += len(text)
        occurrences = count_occurrences(text, self.word)
        if occurrences:
            self.messages_with_word += 1
            self.total += occurrences
            self.per_bucket[bucket_id] += occurrences

    def top_buckets(self, limit: int) -> list[BucketStat]:
        """Return the `limit` buckets with the highest word-per-character frequency."""
        stats = [
            BucketStat(bucket_id, self.per_bucket.get(bucket_id, 0), length)
            for bucket_id, length in self.per_bucket_length.items()
        ]
        stats.sort(key=lambda stat: (-stat.frequency, -stat.count, stat.bucket_id))
        return stats[:limit]


def render_report(
    source_lines: list[tuple[str, str]],
    total_messages: int,
    counter: Counter,
    bucket_label: str,
    breakdown: bool,
    top: int | None = None,
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

    if top is not None:
        stats = counter.top_buckets(top)
        if stats:
            print(
                f'\nTop {top} {bucket_label}s by "{counter.word}" frequency '
                "(count / user input length):"
            )
            print(f"  {'rate':>8}  {'count':>5}  {'chars':>7}  {bucket_label}")
            for stat in stats:
                print(
                    f"  {stat.frequency:8.5f}  {stat.count:5d}  {stat.length:7d}  "
                    f"{stat.bucket_id}"
                )


@dataclass
class Message:
    """One conversational turn: role is either 'user' or 'assistant'."""

    role: str
    text: str


@dataclass
class Conversation:
    """An ordered list of messages belonging to one thread or session."""

    conversation_id: str
    messages: list[Message] = field(default_factory=list)


_ROLE_LABELS = {"user": "User", "assistant": "Assistant"}


def conversation_word_count(conversation: Conversation, word: str) -> int:
    """Total occurrences of `word` across the user inputs of a conversation."""
    return sum(
        count_occurrences(message.text, word)
        for message in conversation.messages
        if message.role == "user"
    )


def conversation_to_markdown(conversation: Conversation, word: str) -> str:
    """Render a whole conversation (all turns, in order) as a Markdown document."""
    user_inputs = [m for m in conversation.messages if m.role == "user"]
    lines = [
        f"# Conversation `{conversation.conversation_id}`",
        "",
        f"- User inputs: {len(user_inputs)}",
        f"- User input length: {sum(len(m.text) for m in user_inputs)}",
        f'- "{word}" said: {conversation_word_count(conversation, word)}',
        "",
    ]
    for index, message in enumerate(conversation.messages, start=1):
        label = _ROLE_LABELS.get(message.role, message.role.title())
        lines.extend([f"## {label} ({index})", "", message.text.strip(), ""])
    return "\n".join(lines)


def _safe_filename(name: str) -> str:
    """Turn a conversation id into a filesystem-safe Markdown file stem."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")
    return cleaned or "conversation"


def export_conversations_markdown(
    conversations: dict[str, Conversation],
    conversation_ids: list[str],
    out_dir: Path,
    word: str,
) -> list[Path]:
    """Write each selected conversation to its own `.md` file under `out_dir`."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for conversation_id in conversation_ids:
        conversation = conversations[conversation_id]
        path = out_dir / f"{_safe_filename(conversation_id)}.md"
        path.write_text(conversation_to_markdown(conversation, word), encoding="utf-8")
        written.append(path)
    return written
