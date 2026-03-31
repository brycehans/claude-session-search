"""Tests for the search/matching logic."""

from claude_session_search import search_messages


def test_basic_search():
    messages = [
        {"role": "user", "text": "how does auth work?", "timestamp": "t0"},
        {"role": "assistant", "text": "The auth middleware validates tokens.", "timestamp": "t1"},
        {"role": "user", "text": "what about the database?", "timestamp": "t2"},
    ]
    matches = search_messages(messages, "auth", case_sensitive=False, context=0)
    assert len(matches) == 2
    assert matches[0]["role"] == "user"
    assert matches[1]["role"] == "assistant"


def test_case_insensitive_default():
    messages = [{"role": "user", "text": "Auth middleware", "timestamp": "t1"}]
    matches = search_messages(messages, "auth", case_sensitive=False, context=0)
    assert len(matches) == 1


def test_case_sensitive():
    messages = [{"role": "user", "text": "Auth middleware", "timestamp": "t1"}]
    matches = search_messages(messages, "auth", case_sensitive=True, context=0)
    assert len(matches) == 0


def test_regex_search():
    messages = [{"role": "user", "text": "check auth_v2 and auth_v3", "timestamp": "t1"}]
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
