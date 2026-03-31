#!/usr/bin/env python3
"""Search Claude Code session transcripts."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


CLAUDE_PROJECTS_DIR = str(Path.home() / ".claude" / "projects")


def resolve_project_dir(project_path, claude_dir=CLAUDE_PROJECTS_DIR):
    """Convert a filesystem path to the matching ~/.claude/projects/ directory."""
    normalized = str(Path(project_path).resolve()).rstrip("/")
    dir_name = normalized.replace("/", "-")
    candidate = Path(claude_dir) / dir_name
    if candidate.is_dir():
        return str(candidate)
    return None


def parse_timestamp(ts_string):
    """Parse a flexible timestamp string into a datetime object."""
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
