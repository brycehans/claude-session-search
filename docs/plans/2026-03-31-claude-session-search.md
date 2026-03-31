# claude-session-search Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Python CLI tool that full-text searches Claude Code session transcripts for a given project, with timestamp/branch filtering and JSON output for piping to Claude.

**Architecture:** Single-file Python script using only stdlib. Resolves a real filesystem path to the matching `~/.claude/projects/` directory, loads `sessions-index.json` for metadata filtering, then streams through JSONL transcript files searching message content. Outputs colored terminal results or structured JSON.

**Tech Stack:** Python 3.10+ stdlib only (argparse, json, re, pathlib, datetime)

---

### Task 1: Project scaffolding

**Files:**
- Create: `claude-session-search.py`
- Create: `tests/test_search.py`

**Step 1: Create the entry point with argument parsing**

```python
#!/usr/bin/env python3
"""Search Claude Code session transcripts."""

import argparse
import sys


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="claude-session-search",
        description="Search Claude Code session transcripts",
    )
    parser.add_argument("query", help="Search term (regex supported)")
    parser.add_argument(
        "--project",
        required=True,
        help="Working directory path (e.g. /Users/bryce/Dev/my-project)",
    )
    parser.add_argument("--after", help="Only sessions after this timestamp")
    parser.add_argument("--before", help="Only sessions before this timestamp")
    parser.add_argument("--branch", help="Filter to sessions on this git branch")
    parser.add_argument(
        "--deep",
        action="store_true",
        help="Also search tool calls and results",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output as JSON for piping to Claude",
    )
    parser.add_argument(
        "--context",
        type=int,
        default=1,
        help="Lines of context around matches (default: 1)",
    )
    parser.add_argument(
        "--case-sensitive",
        action="store_true",
        help="Case-sensitive search (default: insensitive)",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**Step 2: Write the basic test**

```python
"""Tests for claude-session-search."""

import subprocess
import sys


def test_help_flag():
    result = subprocess.run(
        [sys.executable, "claude-session-search.py", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Search Claude Code session transcripts" in result.stdout


def test_missing_query_exits_nonzero():
    result = subprocess.run(
        [sys.executable, "claude-session-search.py", "--project", "/tmp"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
```

**Step 3: Run tests to verify they pass**

Run: `cd /Users/bryce/Dev/claude-session-search && python3 -m pytest tests/test_search.py -v`
Expected: 2 PASS

**Step 4: Commit**

```bash
git init
git add claude-session-search.py tests/test_search.py docs/
git commit -m "feat: project scaffolding with arg parsing"
```

---

### Task 2: Project path resolution

**Files:**
- Modify: `claude-session-search.py`
- Create: `tests/test_resolve_project.py`

**Step 1: Write the failing test**

```python
"""Tests for project path resolution."""

import json
import os
import tempfile

from claude_session_search import resolve_project_dir


def test_resolve_project_dir_exact_match(tmp_path):
    """Given a real path like /Users/bryce/Dev/foo, find the matching project dir."""
    claude_dir = tmp_path / ".claude" / "projects"
    project_dir = claude_dir / "-Users-bryce-Dev-foo"
    project_dir.mkdir(parents=True)
    # Write a sessions-index.json so it's a valid project
    (project_dir / "sessions-index.json").write_text('{"version":1,"entries":[]}')

    result = resolve_project_dir("/Users/bryce/Dev/foo", claude_dir=str(claude_dir))
    assert result == str(project_dir)


def test_resolve_project_dir_not_found(tmp_path):
    claude_dir = tmp_path / ".claude" / "projects"
    claude_dir.mkdir(parents=True)

    result = resolve_project_dir("/Users/bryce/Dev/nonexistent", claude_dir=str(claude_dir))
    assert result is None
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/bryce/Dev/claude-session-search && python3 -m pytest tests/test_resolve_project.py -v`
Expected: FAIL with ImportError

**Step 3: Implement resolve_project_dir**

Add to `claude-session-search.py`:

```python
from pathlib import Path

CLAUDE_PROJECTS_DIR = str(Path.home() / ".claude" / "projects")


def resolve_project_dir(project_path, claude_dir=CLAUDE_PROJECTS_DIR):
    """Convert a filesystem path to the matching ~/.claude/projects/ directory.

    Claude stores projects with paths like: -Users-bryce-Dev-foo
    (the real path with / replaced by -)
    """
    # Normalize: resolve symlinks, remove trailing slash
    normalized = str(Path(project_path).resolve()).rstrip("/")
    # Convert /Users/bryce/Dev/foo -> -Users-bryce-Dev-foo
    dir_name = normalized.replace("/", "-")

    candidate = Path(claude_dir) / dir_name
    if candidate.is_dir():
        return str(candidate)
    return None
```

Update the import at top of file so functions are importable:
- Rename file considerations: keep as `claude-session-search.py` for CLI, but also make importable by adding `claude_session_search.py` as a symlink, OR restructure slightly.

Actually, simpler: rename to `claude_session_search.py` and add a shell wrapper. But even simpler: just keep `claude-session-search.py` and in tests do:

```python
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("claude_session_search", "claude-session-search.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
resolve_project_dir = mod.resolve_project_dir
```

Better approach: name the file `claude_session_search.py` for importability, and create a tiny `claude-session-search` shell script or symlink for CLI use.

**Revised structure:**
- Rename `claude-session-search.py` → `claude_session_search.py`
- Tests import directly: `from claude_session_search import resolve_project_dir`

**Step 4: Run tests to verify they pass**

Run: `cd /Users/bryce/Dev/claude-session-search && python3 -m pytest tests/test_resolve_project.py -v`
Expected: 2 PASS

**Step 5: Commit**

```bash
git add claude_session_search.py tests/test_resolve_project.py
git commit -m "feat: resolve filesystem path to claude project dir"
```

---

### Task 3: Session index loading and filtering

**Files:**
- Modify: `claude_session_search.py`
- Create: `tests/test_session_index.py`

**Step 1: Write the failing tests**

```python
"""Tests for session index loading and filtering."""

import json
from datetime import datetime, timezone

from claude_session_search import load_sessions, filter_sessions


def make_index(tmp_path, entries):
    project_dir = tmp_path / "project"
    project_dir.mkdir(parents=True)
    index = {"version": 1, "entries": entries}
    (project_dir / "sessions-index.json").write_text(json.dumps(index))
    return str(project_dir)


def make_entry(**overrides):
    base = {
        "sessionId": "abc123",
        "fullPath": "/fake/abc123.jsonl",
        "firstPrompt": "hello",
        "summary": "Test session",
        "messageCount": 5,
        "created": "2026-03-15T10:00:00.000Z",
        "modified": "2026-03-15T11:00:00.000Z",
        "gitBranch": "main",
        "projectPath": "/Users/bryce/Dev/foo",
    }
    base.update(overrides)
    return base


def test_load_sessions(tmp_path):
    entries = [make_entry(sessionId="s1"), make_entry(sessionId="s2")]
    project_dir = make_index(tmp_path, entries)
    sessions = load_sessions(project_dir)
    assert len(sessions) == 2
    assert sessions[0]["sessionId"] == "s1"


def test_filter_by_after():
    entries = [
        make_entry(sessionId="old", created="2026-03-01T10:00:00.000Z"),
        make_entry(sessionId="new", created="2026-03-20T10:00:00.000Z"),
    ]
    result = filter_sessions(entries, after="2026-03-15")
    assert len(result) == 1
    assert result[0]["sessionId"] == "new"


def test_filter_by_before():
    entries = [
        make_entry(sessionId="old", created="2026-03-01T10:00:00.000Z"),
        make_entry(sessionId="new", created="2026-03-20T10:00:00.000Z"),
    ]
    result = filter_sessions(entries, before="2026-03-10")
    assert len(result) == 1
    assert result[0]["sessionId"] == "old"


def test_filter_by_branch():
    entries = [
        make_entry(sessionId="s1", gitBranch="main"),
        make_entry(sessionId="s2", gitBranch="develop"),
    ]
    result = filter_sessions(entries, branch="develop")
    assert len(result) == 1
    assert result[0]["sessionId"] == "s2"


def test_filter_combined():
    entries = [
        make_entry(sessionId="s1", gitBranch="develop", created="2026-03-01T10:00:00.000Z"),
        make_entry(sessionId="s2", gitBranch="develop", created="2026-03-20T10:00:00.000Z"),
        make_entry(sessionId="s3", gitBranch="main", created="2026-03-20T10:00:00.000Z"),
    ]
    result = filter_sessions(entries, after="2026-03-10", branch="develop")
    assert len(result) == 1
    assert result[0]["sessionId"] == "s2"
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/bryce/Dev/claude-session-search && python3 -m pytest tests/test_session_index.py -v`
Expected: FAIL with ImportError

**Step 3: Implement load_sessions and filter_sessions**

```python
import json
from datetime import datetime, timezone


def parse_timestamp(ts_string):
    """Parse a flexible timestamp string into a datetime object.

    Supports: ISO format, 'YYYY-MM-DD HH:MM', 'YYYY-MM-DD'
    """
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(ts_string, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"Could not parse timestamp: {ts_string}")


def load_sessions(project_dir):
    """Load session entries from a project's sessions-index.json."""
    index_path = Path(project_dir) / "sessions-index.json"
    with open(index_path) as f:
        data = json.load(f)
    return data.get("entries", [])


def filter_sessions(entries, after=None, before=None, branch=None):
    """Filter session entries by timestamp and branch."""
    result = entries

    if after:
        after_dt = parse_timestamp(after)
        result = [e for e in result if parse_timestamp(e["created"]) > after_dt]

    if before:
        before_dt = parse_timestamp(before)
        result = [e for e in result if parse_timestamp(e["created"]) < before_dt]

    if branch:
        result = [e for e in result if e.get("gitBranch") == branch]

    return result
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/bryce/Dev/claude-session-search && python3 -m pytest tests/test_session_index.py -v`
Expected: 5 PASS

**Step 5: Commit**

```bash
git add claude_session_search.py tests/test_session_index.py
git commit -m "feat: load and filter sessions by timestamp and branch"
```

---

### Task 4: JSONL message extraction

**Files:**
- Modify: `claude_session_search.py`
- Create: `tests/test_extract_messages.py`

**Step 1: Write the failing tests**

```python
"""Tests for extracting searchable text from JSONL transcripts."""

import json

from claude_session_search import extract_messages


def write_jsonl(path, records):
    with open(path, "w") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")


def test_extract_user_message(tmp_path):
    jsonl_path = tmp_path / "session.jsonl"
    write_jsonl(jsonl_path, [
        {
            "type": "user",
            "message": {"role": "user", "content": "how does auth work?"},
            "timestamp": "2026-03-15T10:00:00.000Z",
        }
    ])
    messages = list(extract_messages(str(jsonl_path), deep=False))
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["text"] == "how does auth work?"


def test_extract_assistant_text_block(tmp_path):
    jsonl_path = tmp_path / "session.jsonl"
    write_jsonl(jsonl_path, [
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "The auth middleware validates tokens."},
                ],
            },
            "timestamp": "2026-03-15T10:01:00.000Z",
        }
    ])
    messages = list(extract_messages(str(jsonl_path), deep=False))
    assert len(messages) == 1
    assert "auth middleware" in messages[0]["text"]


def test_skip_thinking_blocks(tmp_path):
    jsonl_path = tmp_path / "session.jsonl"
    write_jsonl(jsonl_path, [
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "thinking", "thinking": "secret thoughts"},
                    {"type": "text", "text": "Here is the answer."},
                ],
            },
            "timestamp": "2026-03-15T10:01:00.000Z",
        }
    ])
    messages = list(extract_messages(str(jsonl_path), deep=False))
    assert len(messages) == 1
    assert "secret thoughts" not in messages[0]["text"]
    assert "Here is the answer." in messages[0]["text"]


def test_deep_mode_includes_tool_use(tmp_path):
    jsonl_path = tmp_path / "session.jsonl"
    write_jsonl(jsonl_path, [
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Let me check."},
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "input": {"command": "grep -r 'auth' src/"},
                    },
                ],
            },
            "timestamp": "2026-03-15T10:01:00.000Z",
        }
    ])
    shallow = list(extract_messages(str(jsonl_path), deep=False))
    assert len(shallow) == 1
    assert "grep" not in shallow[0]["text"]

    deep = list(extract_messages(str(jsonl_path), deep=True))
    assert len(deep) == 1
    assert "grep" in deep[0]["text"]


def test_skip_progress_and_snapshot_types(tmp_path):
    jsonl_path = tmp_path / "session.jsonl"
    write_jsonl(jsonl_path, [
        {"type": "progress", "data": {"type": "hook_progress"}},
        {"type": "file-history-snapshot", "snapshot": {}},
        {
            "type": "user",
            "message": {"role": "user", "content": "hello"},
            "timestamp": "2026-03-15T10:00:00.000Z",
        },
    ])
    messages = list(extract_messages(str(jsonl_path), deep=False))
    assert len(messages) == 1
    assert messages[0]["text"] == "hello"
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/bryce/Dev/claude-session-search && python3 -m pytest tests/test_extract_messages.py -v`
Expected: FAIL with ImportError

**Step 3: Implement extract_messages**

```python
def extract_messages(jsonl_path, deep=False):
    """Extract searchable messages from a JSONL transcript file.

    Yields dicts with: role, text, timestamp
    """
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = record.get("type")
            if msg_type not in ("user", "assistant"):
                continue

            message = record.get("message", {})
            content = message.get("content", "")
            timestamp = record.get("timestamp", "")

            text_parts = []

            if isinstance(content, str):
                text_parts.append(content)
            elif isinstance(content, list):
                for block in content:
                    block_type = block.get("type", "")
                    if block_type == "text":
                        text_parts.append(block.get("text", ""))
                    elif block_type == "tool_use" and deep:
                        tool_name = block.get("name", "")
                        tool_input = json.dumps(block.get("input", {}))
                        text_parts.append(f"[tool:{tool_name}] {tool_input}")
                    elif block_type == "tool_result" and deep:
                        result_content = block.get("content", "")
                        if isinstance(result_content, str):
                            text_parts.append(f"[result] {result_content}")
                        elif isinstance(result_content, list):
                            for rc in result_content:
                                if rc.get("type") == "text":
                                    text_parts.append(f"[result] {rc.get('text', '')}")

            text = "\n".join(text_parts).strip()
            if text:
                yield {
                    "role": message.get("role", msg_type),
                    "text": text,
                    "timestamp": timestamp,
                }
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/bryce/Dev/claude-session-search && python3 -m pytest tests/test_extract_messages.py -v`
Expected: 5 PASS

**Step 5: Commit**

```bash
git add claude_session_search.py tests/test_extract_messages.py
git commit -m "feat: extract searchable text from JSONL transcripts"
```

---

### Task 5: Search engine (regex matching with context)

**Files:**
- Modify: `claude_session_search.py`
- Create: `tests/test_search_engine.py`

**Step 1: Write the failing tests**

```python
"""Tests for the search/matching logic."""

from claude_session_search import search_messages


def test_basic_search():
    messages = [
        {"role": "user", "text": "how does auth work?", "timestamp": "2026-03-15T10:00:00.000Z"},
        {"role": "assistant", "text": "The auth middleware validates tokens.", "timestamp": "2026-03-15T10:01:00.000Z"},
        {"role": "user", "text": "what about the database?", "timestamp": "2026-03-15T10:02:00.000Z"},
    ]
    matches = search_messages(messages, "auth", case_sensitive=False, context=0)
    assert len(matches) == 2
    assert matches[0]["role"] == "user"
    assert matches[1]["role"] == "assistant"


def test_case_insensitive_default():
    messages = [
        {"role": "user", "text": "Auth middleware", "timestamp": "t1"},
    ]
    matches = search_messages(messages, "auth", case_sensitive=False, context=0)
    assert len(matches) == 1


def test_case_sensitive():
    messages = [
        {"role": "user", "text": "Auth middleware", "timestamp": "t1"},
    ]
    matches = search_messages(messages, "auth", case_sensitive=True, context=0)
    assert len(matches) == 0


def test_regex_search():
    messages = [
        {"role": "user", "text": "check auth_v2 and auth_v3", "timestamp": "t1"},
    ]
    matches = search_messages(messages, r"auth_v\d+", case_sensitive=False, context=0)
    assert len(matches) == 1


def test_context_lines():
    messages = [
        {"role": "user", "text": "first message", "timestamp": "t1"},
        {"role": "assistant", "text": "auth is here", "timestamp": "t2"},
        {"role": "user", "text": "third message", "timestamp": "t3"},
    ]
    matches = search_messages(messages, "auth", case_sensitive=False, context=1)
    assert len(matches) == 1
    assert len(matches[0]["context_before"]) == 1
    assert len(matches[0]["context_after"]) == 1
    assert matches[0]["context_before"][0]["text"] == "first message"
    assert matches[0]["context_after"][0]["text"] == "third message"
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/bryce/Dev/claude-session-search && python3 -m pytest tests/test_search_engine.py -v`
Expected: FAIL with ImportError

**Step 3: Implement search_messages**

```python
import re


def search_messages(messages, query, case_sensitive=False, context=0):
    """Search messages for a query pattern, returning matches with context."""
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        pattern = re.compile(query, flags)
    except re.error:
        # Fall back to literal search if regex is invalid
        pattern = re.compile(re.escape(query), flags)

    results = []
    for i, msg in enumerate(messages):
        if pattern.search(msg["text"]):
            match = {
                "role": msg["role"],
                "text": msg["text"],
                "timestamp": msg["timestamp"],
                "context_before": messages[max(0, i - context):i] if context > 0 else [],
                "context_after": messages[i + 1:i + 1 + context] if context > 0 else [],
            }
            results.append(match)

    return results
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/bryce/Dev/claude-session-search && python3 -m pytest tests/test_search_engine.py -v`
Expected: 5 PASS

**Step 5: Commit**

```bash
git add claude_session_search.py tests/test_search_engine.py
git commit -m "feat: regex search with context lines"
```

---

### Task 6: Terminal output formatter

**Files:**
- Modify: `claude_session_search.py`
- Create: `tests/test_format_terminal.py`

**Step 1: Write the failing test**

```python
"""Tests for terminal output formatting."""

from claude_session_search import format_terminal_output


def test_format_single_session():
    session_results = [
        {
            "sessionId": "abc123",
            "created": "2026-03-15T10:00:00.000Z",
            "branch": "main",
            "summary": "Auth discussion",
            "matches": [
                {
                    "role": "user",
                    "text": "how does auth work?",
                    "timestamp": "2026-03-15T10:00:00.000Z",
                    "context_before": [],
                    "context_after": [],
                },
            ],
        }
    ]
    output = format_terminal_output(session_results, use_color=False)
    assert "abc123" in output
    assert "main" in output
    assert "Auth discussion" in output
    assert "[user]" in output
    assert "how does auth work?" in output


def test_format_empty_results():
    output = format_terminal_output([], use_color=False)
    assert "No matches found" in output
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/bryce/Dev/claude-session-search && python3 -m pytest tests/test_format_terminal.py -v`
Expected: FAIL with ImportError

**Step 3: Implement format_terminal_output**

```python
def format_terminal_output(session_results, use_color=True):
    """Format search results for terminal display."""
    if not session_results:
        return "No matches found."

    lines = []
    for session in session_results:
        sid = session["sessionId"][:8]
        created = session["created"][:19].replace("T", " ")
        branch = session.get("branch", "?")
        summary = session.get("summary", "")

        if use_color:
            header = f"\033[1;36m── session {sid} ({created}, branch: {branch}) ──\033[0m"
            if summary:
                header += f"\n\033[2m   {summary}\033[0m"
        else:
            header = f"── session {sid} ({created}, branch: {branch}) ──"
            if summary:
                header += f"\n   {summary}"

        lines.append(header)

        for match in session["matches"]:
            for ctx in match.get("context_before", []):
                role_tag = f"[{ctx['role']}]"
                lines.append(f"  \033[2m{role_tag}  {ctx['text'][:200]}\033[0m" if use_color
                             else f"  {role_tag}  {ctx['text'][:200]}")

            role_tag = f"[{match['role']}]"
            if use_color:
                lines.append(f"  \033[1;33m{role_tag}\033[0m  {match['text'][:200]}")
            else:
                lines.append(f"  {role_tag}  {match['text'][:200]}")

            for ctx in match.get("context_after", []):
                role_tag = f"[{ctx['role']}]"
                lines.append(f"  \033[2m{role_tag}  {ctx['text'][:200]}\033[0m" if use_color
                             else f"  {role_tag}  {ctx['text'][:200]}")

        lines.append("")

    return "\n".join(lines)
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/bryce/Dev/claude-session-search && python3 -m pytest tests/test_format_terminal.py -v`
Expected: 2 PASS

**Step 5: Commit**

```bash
git add claude_session_search.py tests/test_format_terminal.py
git commit -m "feat: terminal output formatter with color support"
```

---

### Task 7: JSON output formatter

**Files:**
- Modify: `claude_session_search.py`
- Create: `tests/test_format_json.py`

**Step 1: Write the failing test**

```python
"""Tests for JSON output formatting."""

import json

from claude_session_search import format_json_output


def test_json_output_structure():
    session_results = [
        {
            "sessionId": "abc123",
            "created": "2026-03-15T10:00:00.000Z",
            "branch": "main",
            "summary": "Auth discussion",
            "matches": [
                {
                    "role": "user",
                    "text": "how does auth work?",
                    "timestamp": "2026-03-15T10:00:00.000Z",
                    "context_before": [],
                    "context_after": [],
                },
            ],
        }
    ]
    output = format_json_output(session_results)
    parsed = json.loads(output)
    assert len(parsed) == 1
    assert parsed[0]["sessionId"] == "abc123"
    assert len(parsed[0]["matches"]) == 1


def test_json_output_is_valid_json():
    output = format_json_output([])
    parsed = json.loads(output)
    assert parsed == []
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/bryce/Dev/claude-session-search && python3 -m pytest tests/test_format_json.py -v`
Expected: FAIL

**Step 3: Implement format_json_output**

```python
def format_json_output(session_results):
    """Format search results as JSON for piping to Claude."""
    return json.dumps(session_results, indent=2)
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/bryce/Dev/claude-session-search && python3 -m pytest tests/test_format_json.py -v`
Expected: 2 PASS

**Step 5: Commit**

```bash
git add claude_session_search.py tests/test_format_json.py
git commit -m "feat: JSON output formatter"
```

---

### Task 8: Wire everything together in main()

**Files:**
- Modify: `claude_session_search.py`
- Create: `tests/test_integration.py`

**Step 1: Write the integration test**

```python
"""Integration tests with real-ish JSONL data."""

import json
import os

from claude_session_search import main


def create_test_project(tmp_path):
    """Create a minimal fake Claude project structure."""
    project_dir = tmp_path / ".claude" / "projects" / "-tmp-fake-project"
    project_dir.mkdir(parents=True)

    # Session 1
    s1_id = "aaaaaaaa-1111-1111-1111-111111111111"
    s1_path = project_dir / f"{s1_id}.jsonl"
    with open(s1_path, "w") as f:
        f.write(json.dumps({
            "type": "user",
            "message": {"role": "user", "content": "how does auth middleware work?"},
            "timestamp": "2026-03-15T10:00:00.000Z",
        }) + "\n")
        f.write(json.dumps({
            "type": "assistant",
            "message": {"role": "assistant", "content": [
                {"type": "text", "text": "The auth middleware validates JWT tokens on each request."},
            ]},
            "timestamp": "2026-03-15T10:01:00.000Z",
        }) + "\n")

    # Session 2
    s2_id = "bbbbbbbb-2222-2222-2222-222222222222"
    s2_path = project_dir / f"{s2_id}.jsonl"
    with open(s2_path, "w") as f:
        f.write(json.dumps({
            "type": "user",
            "message": {"role": "user", "content": "fix the database migration"},
            "timestamp": "2026-03-20T14:00:00.000Z",
        }) + "\n")

    # Index
    index = {
        "version": 1,
        "entries": [
            {
                "sessionId": s1_id,
                "fullPath": str(s1_path),
                "firstPrompt": "how does auth middleware work?",
                "summary": "Auth middleware discussion",
                "messageCount": 2,
                "created": "2026-03-15T10:00:00.000Z",
                "modified": "2026-03-15T10:01:00.000Z",
                "gitBranch": "main",
                "projectPath": "/tmp/fake-project",
            },
            {
                "sessionId": s2_id,
                "fullPath": str(s2_path),
                "firstPrompt": "fix the database migration",
                "summary": "Database migration fix",
                "messageCount": 1,
                "created": "2026-03-20T14:00:00.000Z",
                "modified": "2026-03-20T14:00:00.000Z",
                "gitBranch": "develop",
                "projectPath": "/tmp/fake-project",
            },
        ],
    }
    (project_dir / "sessions-index.json").write_text(json.dumps(index))
    return str(project_dir), str(tmp_path / ".claude" / "projects")


def test_search_finds_auth(tmp_path, capsys):
    project_dir, claude_dir = create_test_project(tmp_path)
    exit_code = main([
        "auth",
        "--project", "/tmp/fake-project",
    ], claude_dir=claude_dir)
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "auth" in captured.out.lower()


def test_search_json_output(tmp_path, capsys):
    project_dir, claude_dir = create_test_project(tmp_path)
    exit_code = main([
        "auth",
        "--project", "/tmp/fake-project",
        "--json",
    ], claude_dir=claude_dir)
    assert exit_code == 0
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert len(parsed) == 1  # Only session 1 has "auth"


def test_search_no_matches(tmp_path, capsys):
    project_dir, claude_dir = create_test_project(tmp_path)
    exit_code = main([
        "zzzznotfound",
        "--project", "/tmp/fake-project",
    ], claude_dir=claude_dir)
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "No matches" in captured.out


def test_filter_by_branch(tmp_path, capsys):
    project_dir, claude_dir = create_test_project(tmp_path)
    exit_code = main([
        "database",
        "--project", "/tmp/fake-project",
        "--branch", "develop",
    ], claude_dir=claude_dir)
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "database" in captured.out.lower()


def test_filter_by_date(tmp_path, capsys):
    project_dir, claude_dir = create_test_project(tmp_path)
    exit_code = main([
        "auth",
        "--project", "/tmp/fake-project",
        "--after", "2026-03-16",
    ], claude_dir=claude_dir)
    assert exit_code == 1  # Auth session is before the cutoff
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/bryce/Dev/claude-session-search && python3 -m pytest tests/test_integration.py -v`
Expected: FAIL

**Step 3: Wire up main()**

```python
def main(argv=None, claude_dir=CLAUDE_PROJECTS_DIR):
    args = parse_args(argv)

    # Resolve project
    project_dir = resolve_project_dir(args.project, claude_dir=claude_dir)
    if not project_dir:
        print(f"Error: No Claude project found for path: {args.project}", file=sys.stderr)
        return 1

    # Load and filter sessions
    entries = load_sessions(project_dir)
    entries = filter_sessions(
        entries,
        after=args.after,
        before=args.before,
        branch=args.branch,
    )

    if not entries:
        print("No sessions match the given filters.")
        return 1

    # Search each session
    use_color = not args.json_output and sys.stdout.isatty()
    session_results = []

    for entry in entries:
        jsonl_path = Path(project_dir) / f"{entry['sessionId']}.jsonl"
        if not jsonl_path.exists():
            continue

        messages = list(extract_messages(str(jsonl_path), deep=args.deep))
        matches = search_messages(
            messages,
            args.query,
            case_sensitive=args.case_sensitive,
            context=args.context,
        )

        if matches:
            session_results.append({
                "sessionId": entry["sessionId"],
                "created": entry.get("created", ""),
                "branch": entry.get("gitBranch", ""),
                "summary": entry.get("summary", ""),
                "matches": matches,
            })

    # Output
    if args.json_output:
        print(format_json_output(session_results))
    else:
        print(format_terminal_output(session_results, use_color=use_color))

    return 0 if session_results else 1
```

**Step 4: Run all tests**

Run: `cd /Users/bryce/Dev/claude-session-search && python3 -m pytest tests/ -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add claude_session_search.py tests/test_integration.py
git commit -m "feat: wire up main with end-to-end search pipeline"
```

---

### Task 9: Make it executable and add CLI entry point

**Files:**
- Modify: `claude_session_search.py` (ensure shebang)
- Optional: create shell alias instructions

**Step 1: Make file executable**

```bash
chmod +x claude_session_search.py
```

**Step 2: Test running it directly**

Run: `cd /Users/bryce/Dev/claude-session-search && ./claude_session_search.py --help`
Expected: Help output shown

**Step 3: Test against real data**

Run: `cd /Users/bryce/Dev/claude-session-search && ./claude_session_search.py "auth" --project /Users/bryce/Dev/front-end-two-col-template-rebooted`
Expected: Real search results from actual transcripts

**Step 4: Commit**

```bash
git add claude_session_search.py
git commit -m "chore: make script executable"
```

---

## Summary

| Task | What | Tests |
|------|------|-------|
| 1 | Scaffolding + argparse | 2 |
| 2 | Project path resolution | 2 |
| 3 | Session index loading + filtering | 5 |
| 4 | JSONL message extraction | 5 |
| 5 | Search engine (regex + context) | 5 |
| 6 | Terminal output formatter | 2 |
| 7 | JSON output formatter | 2 |
| 8 | Integration wiring | 5 |
| 9 | Make executable + real test | 0 (manual) |

**Total: 9 tasks, 28 automated tests**
