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
