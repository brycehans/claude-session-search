"""Tests for claude-session-search."""

import subprocess
import sys


def test_help_flag():
    result = subprocess.run(
        [sys.executable, "claude_session_search.py", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Search Claude Code session transcripts" in result.stdout


def test_missing_query_exits_nonzero():
    result = subprocess.run(
        [sys.executable, "claude_session_search.py", "--project", "/tmp"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
