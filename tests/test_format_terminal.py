"""Tests for terminal output formatting."""

from claude_session_search import format_terminal_output


def test_format_single_session():
    session_results = [
        {
            "sessionId": "abc12345-full-uuid",
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
    assert "abc12345" in output
    assert "main" in output
    assert "Auth discussion" in output
    assert "[user]" in output
    assert "how does auth work?" in output


def test_format_empty_results():
    output = format_terminal_output([], use_color=False)
    assert "No matches found" in output
