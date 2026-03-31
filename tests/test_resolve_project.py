"""Tests for project path resolution."""

import json
from claude_session_search import resolve_project_dir


def test_resolve_project_dir_exact_match(tmp_path):
    claude_dir = tmp_path / ".claude" / "projects"
    project_dir = claude_dir / "-Users-bryce-Dev-foo"
    project_dir.mkdir(parents=True)
    (project_dir / "sessions-index.json").write_text('{"version":1,"entries":[]}')

    result = resolve_project_dir("/Users/bryce/Dev/foo", claude_dir=str(claude_dir))
    assert result == str(project_dir)


def test_resolve_project_dir_not_found(tmp_path):
    claude_dir = tmp_path / ".claude" / "projects"
    claude_dir.mkdir(parents=True)

    result = resolve_project_dir("/Users/bryce/Dev/nonexistent", claude_dir=str(claude_dir))
    assert result is None
