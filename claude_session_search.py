#!/usr/bin/env python3
"""Search Claude Code session transcripts."""

import argparse
import sys
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
