#!/usr/bin/env python3
"""Search Claude Code session transcripts."""

import argparse
import json
import re
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
    # Normalize +00:00 offset to Z for simpler format matching
    ts_string = ts_string.replace("+00:00", "Z")
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
    """Load session entries by discovering JSONL files and enriching with index metadata."""
    project_path = Path(project_dir)

    # Load index for metadata (may not cover all files)
    index_by_id = {}
    index_path = project_path / "sessions-index.json"
    if index_path.exists():
        with open(index_path) as f:
            data = json.load(f)
        for entry in data.get("entries", []):
            index_by_id[entry["sessionId"]] = entry

    # Discover all JSONL files on disk
    entries = []
    for jsonl_file in sorted(project_path.glob("*.jsonl")):
        session_id = jsonl_file.stem
        if session_id in index_by_id:
            entries.append(index_by_id[session_id])
        else:
            # Build minimal entry from file metadata
            stat = jsonl_file.stat()
            created = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
            entries.append({
                "sessionId": session_id,
                "fullPath": str(jsonl_file),
                "firstPrompt": "",
                "summary": "",
                "messageCount": 0,
                "created": created,
                "modified": created,
                "gitBranch": "",
                "projectPath": "",
            })

    return entries


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


def extract_messages(jsonl_path, deep=False):
    """Extract searchable messages from a JSONL transcript file."""
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = record.get("type")
            if msg_type not in ("user", "assistant"):
                continue

            message = record.get("message", {})
            content = message.get("content", "")
            timestamp = record.get("timestamp", "")

            text_parts = []

            if isinstance(content, str):
                text_parts.append(content)
            elif isinstance(content, list):
                for block in content:
                    block_type = block.get("type", "")
                    if block_type == "text":
                        text_parts.append(block.get("text", ""))
                    elif block_type == "tool_use" and deep:
                        tool_name = block.get("name", "")
                        tool_input = json.dumps(block.get("input", {}))
                        text_parts.append(f"[tool:{tool_name}] {tool_input}")
                    elif block_type == "tool_result" and deep:
                        result_content = block.get("content", "")
                        if isinstance(result_content, str):
                            text_parts.append(f"[result] {result_content}")
                        elif isinstance(result_content, list):
                            for rc in result_content:
                                if rc.get("type") == "text":
                                    text_parts.append(f"[result] {rc.get('text', '')}")

            text = "\n".join(text_parts).strip()
            if text:
                yield {
                    "role": message.get("role", msg_type),
                    "text": text,
                    "timestamp": timestamp,
                }


def search_messages(messages, query, case_sensitive=False, context=0):
    """Search messages for a query pattern, returning matches with context."""
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        pattern = re.compile(query, flags)
    except re.error:
        pattern = re.compile(re.escape(query), flags)

    results = []
    for i, msg in enumerate(messages):
        if pattern.search(msg["text"]):
            match = {
                "role": msg["role"],
                "text": msg["text"],
                "timestamp": msg["timestamp"],
                "context_before": messages[max(0, i - context):i] if context > 0 else [],
                "context_after": messages[i + 1:i + 1 + context] if context > 0 else [],
            }
            results.append(match)

    return results


def format_terminal_output(session_results, use_color=True):
    """Format search results for terminal display."""
    if not session_results:
        return "No matches found."

    lines = []
    for session in session_results:
        sid = session["sessionId"][:8]
        created = session["created"][:19].replace("T", " ")
        branch = session.get("branch", "?")
        summary = session.get("summary", "")
        project = session.get("project", "")

        meta_parts = [created]
        if project:
            meta_parts.append(f"project: {project}")
        if branch:
            meta_parts.append(f"branch: {branch}")
        meta = ", ".join(meta_parts)

        if use_color:
            header = f"\033[1;36m── session {sid} ({meta}) ──\033[0m"
            if summary:
                header += f"\n\033[2m   {summary}\033[0m"
        else:
            header = f"── session {sid} ({meta}) ──"
            if summary:
                header += f"\n   {summary}"

        lines.append(header)

        for match in session["matches"]:
            for ctx in match.get("context_before", []):
                role_tag = f"[{ctx['role']}]"
                if use_color:
                    lines.append(f"  \033[2m{role_tag}  {ctx['text'][:200]}\033[0m")
                else:
                    lines.append(f"  {role_tag}  {ctx['text'][:200]}")

            role_tag = f"[{match['role']}]"
            if use_color:
                lines.append(f"  \033[1;33m{role_tag}\033[0m  {match['text'][:200]}")
            else:
                lines.append(f"  {role_tag}  {match['text'][:200]}")

            for ctx in match.get("context_after", []):
                role_tag = f"[{ctx['role']}]"
                if use_color:
                    lines.append(f"  \033[2m{role_tag}  {ctx['text'][:200]}\033[0m")
                else:
                    lines.append(f"  {role_tag}  {ctx['text'][:200]}")

        lines.append("")

    return "\n".join(lines)


def format_json_output(session_results):
    """Format search results as JSON for piping to Claude."""
    return json.dumps(session_results, indent=2)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="claude-session-search",
        description="Search Claude Code session transcripts",
    )
    parser.add_argument("query", help="Search term (regex supported)")
    parser.add_argument(
        "--project",
        help="Working directory path (e.g. /Users/bryce/Dev/my-project). Omit to search all projects.",
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


def main(argv=None, claude_dir=CLAUDE_PROJECTS_DIR):
    args = parse_args(argv)

    # Resolve project directories
    if args.project:
        project_dir = resolve_project_dir(args.project, claude_dir=claude_dir)
        if not project_dir:
            print(f"Error: No Claude project found for path: {args.project}", file=sys.stderr)
            return 1
        project_dirs = [project_dir]
    else:
        claude_path = Path(claude_dir)
        if not claude_path.is_dir():
            print(f"Error: Claude projects directory not found: {claude_dir}", file=sys.stderr)
            return 1
        project_dirs = sorted(
            str(d) for d in claude_path.iterdir() if d.is_dir()
        )

    # Load and filter sessions across all project dirs
    all_entries = []  # list of (project_dir, entry) tuples
    for pdir in project_dirs:
        entries = load_sessions(pdir)
        entries = filter_sessions(
            entries,
            after=args.after,
            before=args.before,
            branch=args.branch,
        )
        for entry in entries:
            all_entries.append((pdir, entry))

    if not all_entries:
        print("No sessions match the given filters.")
        return 1

    # Search each session
    use_color = not args.json_output and sys.stdout.isatty()
    session_results = []

    for pdir, entry in all_entries:
        jsonl_path = Path(pdir) / f"{entry['sessionId']}.jsonl"
        if not jsonl_path.exists():
            continue

        messages = list(extract_messages(str(jsonl_path), deep=args.deep))
        matches = search_messages(
            messages,
            args.query,
            case_sensitive=args.case_sensitive,
            context=args.context,
        )

        if matches:
            result = {
                "sessionId": entry["sessionId"],
                "created": entry.get("created", ""),
                "branch": entry.get("gitBranch", ""),
                "summary": entry.get("summary", ""),
                "matches": matches,
            }
            if not args.project:
                # Strip home dir prefix for readability
                dir_name = Path(pdir).name
                home_prefix = str(Path.home()).replace("/", "-")
                if dir_name.startswith(home_prefix):
                    result["project"] = dir_name[len(home_prefix):].lstrip("-") or "~"
                else:
                    result["project"] = dir_name
            session_results.append(result)

    # Output
    if args.json_output:
        print(format_json_output(session_results))
    else:
        print(format_terminal_output(session_results, use_color=use_color))

    if not session_results and not args.deep:
        print("Tip: try --deep to also search tool calls and results.", file=sys.stderr)

    return 0 if session_results else 1


if __name__ == "__main__":
    sys.exit(main())
