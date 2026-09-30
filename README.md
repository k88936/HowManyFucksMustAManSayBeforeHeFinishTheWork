# How Many "Fucks" Must A Man Say Before He Finish The Work?

```shell
uv run fuck_junie.py 
uv run fuck_codex.py 
```

```txt
Codex data dir : /root/.codex
Thread history : /root/.codex/thread_history_1.sqlite
User messages  : 783
Messages with "fuck": 177
Total "fuck" said: 357
```
```text
Junie data dir : /root/.junie
Sessions dir : /root/.junie/sessions
User messages  : 748
Messages with "fuck": 86
Total "fuck" said: 116
```

## Top N by frequency

Rank conversations by "fuck frequency" — `fuck count / user input length` (characters) — and print the top `N`:

```shell
uv run fuck_junie.py --top 5
uv run fuck_codex.py --top 5
```

```txt
Top 5 threads by "fuck" frequency (count / user input length):
      rate  count    chars  thread
   0.04762      2       42  01a08a10-c7a4-7e33-a8a5-fb8bfd093c9c
   0.04762      2       42  01a08a18-8b5e-7b03-99c6-0666ae265407
   0.04000      2       50  01a089fc-47a3-7ac3-9972-0b56bcbb24ef
   0.02920     12      411  01a07062-6c8f-7b01-a09e-8632b83db951
   0.02829     32     1131  01a0703c-d661-71c1-b33d-a7824c1594ab
```

## Render conversations to Markdown

Write the top `N` whole conversations (every user and assistant turn, in order)
to one `.md` file each. `N` comes from `--top` and defaults to `10`:

```shell
uv run fuck_junie.py --top 5 --md-dir ./out/junie
uv run fuck_codex.py --top 5 --md-dir ./out/codex
```

## Tests

```shell
uv run python -m unittest
```