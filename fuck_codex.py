#!/usr/bin/env python3
"""Count how many times a word (default: "fuck") appears in the user's Codex thread history.

The script reads the Codex CLI thread-history database (~/.codex/thread_history_*.sqlite),
extracts the text of the user's own messages, and counts case-insensitive occurrences.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from shared import Counter, render_report


def default_codex_dir() -> Path:
    """Directory where the Codex CLI stores its data."""
    return Path.home() / ".codex"


def find_thread_history_db(codex_dir: Path) -> Path:
    """Return the newest thread-history SQLite database under the given directory."""
    candidates = sorted(codex_dir.glob("thread_history_*.sqlite"))
    if not candidates:
        raise FileNotFoundError(
            f"no thread-history database found under {codex_dir} "
            "(looked for thread_history_*.sqlite)"
        )
    return candidates[-1]


def extract_user_text(item_json: str) -> str:
    """Extract the plain text a user typed from a thread_items.item_json blob."""
    try:
        data = json.loads(item_json)
    except (json.JSONDecodeError, TypeError):
        return ""

    content = data.get("content")
    if not isinstance(content, list):
        text = data.get("text")
        return text if isinstance(text, str) else ""

    parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        text = block.get("text")
        if isinstance(text, str) and text:
            parts.append(text)
    return "\n".join(parts)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Count how many times a word appears in the user's Codex thread history."
    )
    parser.add_argument(
        "--codex-dir",
        type=Path,
        default=default_codex_dir(),
        help="directory containing the Codex data (default: %(default)s)",
    )
    parser.add_argument(
        "--word",
        default="fuck",
        help=(
            "word to count, matched case-insensitively; the default also matches "
            "common variations and censored spellings (default: %(default)s)"
        ),
    )
    parser.add_argument(
        "--breakdown",
        action="store_true",
        help="also print per-thread counts",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    db_path = find_thread_history_db(args.codex_dir)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            "SELECT thread_id, item_json FROM thread_items WHERE item_type = 'userMessage'"
        ).fetchall()
    finally:
        conn.close()

    counter = Counter(args.word)
    for thread_id, item_json in rows:
        counter.add(thread_id, extract_user_text(item_json))

    render_report(
        source_lines=[
            ("Codex data dir", str(args.codex_dir)),
            ("Thread history", str(db_path)),
        ],
        total_messages=len(rows),
        counter=counter,
        bucket_label="thread",
        breakdown=args.breakdown,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
