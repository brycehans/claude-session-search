"""Integration tests with real-ish JSONL data."""

import json
from claude_session_search import main


def create_test_project(tmp_path):
    """Create a minimal fake Claude project structure."""
    # Use a project path inside tmp_path so it resolves consistently
    fake_project = tmp_path / "fake-project"
    fake_project.mkdir(parents=True)
    # resolve() to match what resolve_project_dir does
    normalized = str(fake_project.resolve()).replace("/", "-")
    project_dir = tmp_path / ".claude" / "projects" / normalized
    project_dir.mkdir(parents=True)

    project_path = str(fake_project.resolve())

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
                "projectPath": project_path,
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
                "projectPath": project_path,
            },
        ],
    }
    (project_dir / "sessions-index.json").write_text(json.dumps(index))
    claude_dir = str(tmp_path / ".claude" / "projects")
    return project_path, claude_dir


def test_search_finds_auth(tmp_path, capsys):
    project_path, claude_dir = create_test_project(tmp_path)
    exit_code = main([
        "auth",
        "--project", project_path,
    ], claude_dir=claude_dir)
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "auth" in captured.out.lower()


def test_search_json_output(tmp_path, capsys):
    project_path, claude_dir = create_test_project(tmp_path)
    exit_code = main([
        "auth",
        "--project", project_path,
        "--json",
    ], claude_dir=claude_dir)
    assert exit_code == 0
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert len(parsed) == 1  # Only session 1 has "auth"


def test_search_no_matches(tmp_path, capsys):
    project_path, claude_dir = create_test_project(tmp_path)
    exit_code = main([
        "zzzznotfound",
        "--project", project_path,
    ], claude_dir=claude_dir)
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "No matches" in captured.out


def test_filter_by_branch(tmp_path, capsys):
    project_path, claude_dir = create_test_project(tmp_path)
    exit_code = main([
        "database",
        "--project", project_path,
        "--branch", "develop",
    ], claude_dir=claude_dir)
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "database" in captured.out.lower()


def test_filter_by_date(tmp_path, capsys):
    project_path, claude_dir = create_test_project(tmp_path)
    exit_code = main([
        "auth",
        "--project", project_path,
        "--after", "2026-03-16",
    ], claude_dir=claude_dir)
    assert exit_code == 1  # Auth session is before the cutoff
