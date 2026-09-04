#!/usr/bin/env python3
"""Count how many times a word (default: "fuck") appears in the user's Junie session history.

Junie stores each session under ~/.junie/sessions/<sessionId>/ as an
events.jsonl stream. This script reads every session's events.jsonl, extracts
the user prompts (UserPromptEvent records), and counts case-insensitive
occurrences of the word.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from shared import Counter, render_report


def default_junie_dir() -> Path:
    """Directory where the Junie CLI stores its data."""
    return Path.home() / ".junie"


def iter_user_prompts(sessions_dir: Path):
    """Yield (session_id, prompt_text) for every user prompt across all sessions."""
    for events_file in sorted(sessions_dir.glob("session-*/events.jsonl")):
        session_id = events_file.parent.name
        try:
            with events_file.open() as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if event.get("kind") != "UserPromptEvent":
                        continue
                    prompt = event.get("prompt")
                    if not isinstance(prompt, str) or not prompt:
                        prompt = event.get("presentablePrompt")
                    if isinstance(prompt, str) and prompt:
                        yield session_id, prompt
        except OSError:
            continue


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Count how many times a word appears in the user's Junie session history."
    )
    parser.add_argument(
        "--junie-dir",
        type=Path,
        default=default_junie_dir(),
        help="directory containing the Junie data (default: %(default)s)",
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
        help="also print per-session counts",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    sessions_dir = args.junie_dir / "sessions"
    counter = Counter(args.word)
    total_messages = 0

    for session_id, prompt in iter_user_prompts(sessions_dir):
        total_messages += 1
        counter.add(session_id, prompt)

    render_report(
        source_lines=[
            ("Junie data dir", str(args.junie_dir)),
            ("Sessions dir", str(sessions_dir)),
        ],
        total_messages=total_messages,
        counter=counter,
        bucket_label="session",
        breakdown=args.breakdown,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
