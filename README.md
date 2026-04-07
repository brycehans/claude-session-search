# claude-session-search

Search through your Claude Code session transcripts from the command line.

## Quick start

```bash
# Search all projects
claude-session-search "auth middleware"

# Search a specific project
claude-session-search "auth middleware" --project ~/Dev/my-project
```

## Installation

```bash
# Clone the repo
git clone <repo-url> ~/Dev/claude-session-search

# Symlink to PATH
ln -s ~/Dev/claude-session-search/claude_session_search.py /usr/local/bin/claude-session-search
```

## How it works

Claude Code stores session transcripts as JSONL files under `~/.claude/projects/`. Each project directory contains one `.jsonl` file per session, plus a `sessions-index.json` with metadata (summaries, dates, branches).

`claude-session-search` discovers all JSONL files in the matching project directory (or all project directories when `--project` is omitted), extracts the human and assistant message text, and runs your query against it. Sessions with metadata in the index get enriched with summaries, branch names, and timestamps.

## Usage

```
claude-session-search <query> [options]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `query` | Search term. Supports regex (e.g. `"auth_v\d+"`) |

### Options

| Option | Description |
|--------|-------------|
| `--project PATH` | Path to the project working directory. Omit to search all projects. |
| `--after TIMESTAMP` | Only include sessions created after this time |
| `--before TIMESTAMP` | Only include sessions created before this time |
| `--branch NAME` | Only include sessions on this git branch |
| `--deep` | Also search tool calls and their results |
| `--json` | Output as JSON (for piping to other tools) |
| `--context N` | Number of surrounding messages to show (default: 1) |
| `--case-sensitive` | Match case exactly (default: case-insensitive) |

### Timestamp formats

The `--after` and `--before` flags accept several formats:

```
2026-03-30T17:30:00.000Z       # Full ISO with milliseconds
2026-03-30T17:30:00+00:00      # ISO with UTC offset
2026-03-30T17:30:00             # ISO without timezone
2026-03-30 17:30               # Date and time
2026-03-30                     # Date only (midnight UTC)
```

## Examples

### Search all projects

```bash
claude-session-search "database migration"
```

### Search a specific project

```bash
claude-session-search "database migration" --project ~/Dev/my-app
```

### Search within a date range

```bash
claude-session-search "deploy" --project ~/Dev/my-app \
  --after "2026-03-01" --before "2026-03-15"
```

### Search a specific branch

```bash
claude-session-search "refactor" --project ~/Dev/my-app --branch develop
```

### Search tool calls too

By default, only the text of human and assistant messages is searched. Use `--deep` to also search through tool calls (Bash commands, file reads, grep results, etc.):

```bash
claude-session-search "package.json" --project ~/Dev/my-app --deep
```

### Pipe JSON to Claude for analysis

```bash
claude-session-search "auth" --project ~/Dev/my-app --json \
  | claude "summarize what decisions were made about auth"
```

### Get more context around matches

```bash
claude-session-search "bug" --project ~/Dev/my-app --context 3
```

### Use regex

```bash
claude-session-search "TODO|FIXME|HACK" --project ~/Dev/my-app
```

## Terminal output

Results are grouped by session, with a header showing the session ID, timestamp, branch, and summary (when available). When searching globally (no `--project`), the project name is also shown. Matching messages are highlighted, with context messages shown in dim text:

```
── session 09cb08ea (2026-03-30 05:56, project: Dev-my-app, branch: feature/hidden-form-fields) ──
   PR review for hidden form fields
  [user]  can you review the auth middleware changes in this PR?
  [assistant]  Looking at the auth middleware, the main change is...
  [user]  please add a comment on the PR noting those things
```

## JSON output

With `--json`, output is a JSON array of session objects:

```json
[
  {
    "sessionId": "09cb08ea-85c7-4bbb-8b15-a79227e3e83a",
    "created": "2026-03-30T05:51:34.000Z",
    "project": "Dev-my-app",
    "branch": "feature/hidden-form-fields",
    "summary": "PR review for hidden form fields",
    "matches": [
      {
        "role": "user",
        "text": "can you review the auth middleware changes?",
        "timestamp": "2026-03-30T05:52:00.000Z",
        "context_before": [...],
        "context_after": [...]
      }
    ]
  }
]
```

The `project` field is included only when searching globally (no `--project` flag).

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Matches found |
| 1 | No matches found, or no sessions match filters |

## How sessions are discovered

The tool scans for `.jsonl` files on disk in the project directory rather than relying solely on `sessions-index.json`. This is because the index can become stale -- it may reference deleted sessions or miss sessions that exist on disk. When a file has a matching entry in the index, it inherits the metadata (summary, branch, timestamps). Otherwise, a minimal entry is constructed from the file's modification time.

## Claude Code skill

A Claude Code skill is included at `skills/searching-session-transcripts/SKILL.md`. This lets Claude automatically use the tool when you ask about past conversations.

To install:

```bash
cp -r skills/searching-session-transcripts ~/.claude/skills/
```

Once installed, Claude will pick it up when you ask things like "when did we discuss auth?" or "find the session where we decided on the database schema".

## Requirements

Python 3.10+ (no external dependencies).
