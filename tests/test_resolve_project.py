"""Tests for project path resolution."""

import json
from pathlib import Path
from claude_session_search import resolve_project_dir


def test_resolve_project_dir_exact_match(tmp_path):
    claude_dir = tmp_path / ".claude" / "projects"
    # Use tmp_path as the fake project so resolve() won't mangle it
    fake_project = tmp_path / "myproject"
    fake_project.mkdir()
    dir_name = str(fake_project.resolve()).replace("/", "-")
    project_dir = claude_dir / dir_name
    project_dir.mkdir(parents=True)
    (project_dir / "sessions-index.json").write_text('{"version":1,"entries":[]}')

    result = resolve_project_dir(str(fake_project), claude_dir=str(claude_dir))
    assert result == str(project_dir)


def test_resolve_project_dir_not_found(tmp_path):
    claude_dir = tmp_path / ".claude" / "projects"
    claude_dir.mkdir(parents=True)

    result = resolve_project_dir(str(tmp_path / "nonexistent"), claude_dir=str(claude_dir))
    assert result is None
