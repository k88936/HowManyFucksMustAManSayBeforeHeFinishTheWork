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

from shared import (
    DEFAULT_TOP,
    Conversation,
    Counter,
    Message,
    export_conversations_markdown,
    positive_int,
    render_report,
)


def default_junie_dir() -> Path:
    """Directory where the Junie CLI stores its data."""
    return Path.home() / ".junie"


def iter_conversations(sessions_dir: Path):
    """Yield (session_id, Conversation) for every user/assistant turn per session."""
    for events_file in sorted(sessions_dir.glob("session-*/events.jsonl")):
        session_id = events_file.parent.name
        conversation = Conversation(session_id)
        last_assistant_text: str | None = None
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
                    kind = event.get("kind")
                    if kind == "UserPromptEvent":
                        prompt = event.get("prompt")
                        if not isinstance(prompt, str) or not prompt:
                            prompt = event.get("presentablePrompt")
                        if isinstance(prompt, str) and prompt:
                            conversation.messages.append(Message("user", prompt))
                            last_assistant_text = None
                    elif kind == "SessionA2uxEvent":
                        payload = event.get("event")
                        agent_event = (
                            payload.get("agentEvent") if isinstance(payload, dict) else None
                        )
                        if not isinstance(agent_event, dict):
                            continue
                        if agent_event.get("kind") != "ResultBlockUpdatedEvent":
                            continue
                        result = agent_event.get("result")
                        if not isinstance(result, str) or not result.strip():
                            continue
                        # The event log repeats a turn's final result, so skip the echo.
                        if result == last_assistant_text:
                            continue
                        conversation.messages.append(Message("assistant", result))
                        last_assistant_text = result
        except OSError:
            continue
        yield session_id, conversation


def iter_user_prompts(sessions_dir: Path):
    """Yield (session_id, prompt_text) for every user prompt across all sessions."""
    for session_id, conversation in iter_conversations(sessions_dir):
        for message in conversation.messages:
            if message.role == "user":
                yield session_id, message.text


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
    parser.add_argument(
        "--top",
        type=positive_int,
        metavar="N",
        help=(
            "print the N sessions with the highest frequency "
            "(count / user input length)"
        ),
    )
    parser.add_argument(
        "--md-dir",
        type=Path,
        metavar="DIR",
        help=(
            "render the top N whole conversations to markdown files in DIR "
            "(N comes from --top, default: %d)" % DEFAULT_TOP
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    sessions_dir = args.junie_dir / "sessions"
    counter = Counter(args.word)
    conversations: dict[str, Conversation] = {}
    total_messages = 0

    for session_id, conversation in iter_conversations(sessions_dir):
        conversations[session_id] = conversation
        for message in conversation.messages:
            if message.role == "user":
                total_messages += 1
                counter.add(session_id, message.text)

    render_report(
        source_lines=[
            ("Junie data dir", str(args.junie_dir)),
            ("Sessions dir", str(sessions_dir)),
        ],
        total_messages=total_messages,
        counter=counter,
        bucket_label="session",
        breakdown=args.breakdown,
        top=args.top,
    )

    if args.md_dir is not None:
        limit = args.top if args.top is not None else DEFAULT_TOP
        top_ids = [stat.bucket_id for stat in counter.top_buckets(limit)]
        written = export_conversations_markdown(
            conversations, top_ids, args.md_dir, args.word
        )
        print(f"\nRendered {len(written)} conversation(s) to {args.md_dir}:")
        for path in written:
            print(f"  {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
