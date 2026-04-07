"""Tests for session index loading and filtering."""

import json
from claude_session_search import load_sessions, filter_sessions


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
        "projectPath": "/home/user/projects/foo",
    }
    base.update(overrides)
    return base


def test_load_sessions(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    entries = [make_entry(sessionId="s1"), make_entry(sessionId="s2")]
    (project_dir / "sessions-index.json").write_text(json.dumps({"version": 1, "entries": entries}))
    # Create matching JSONL files on disk
    (project_dir / "s1.jsonl").write_text("")
    (project_dir / "s2.jsonl").write_text("")
    sessions = load_sessions(str(project_dir))
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
