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
