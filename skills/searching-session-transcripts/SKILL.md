---
name: searching-session-transcripts
description: Use when the user wants to find, recall, or search past Claude Code conversations - typically by topic, keyword, error message, or decision made in a previous session. Also use when asked "when did we discuss X" or "what did we decide about Y"
---

# Searching Session Transcripts

Find past Claude Code conversations using `claude-session-search`.

## Usage

```bash
claude-session-search "<query>" --project <path> [options]
```

The user typically provides three things:
1. **A keyword or topic** they remember discussing
2. **A rough date range** for when it happened
3. **Which project directory** the work was in

## Workflow

1. Ask for any missing pieces (keyword, project path, date range)
2. Run the search
3. If too many results, narrow with `--after`/`--before` or `--branch`
4. If too few, try broader terms, regex alternatives (`"auth|login|session"`), or `--deep`

## Quick Reference

| Flag | Purpose | Example |
|------|---------|---------|
| `--project PATH` | Project working directory (required) | `--project /Users/bryce/Dev/my-app` |
| `--after TS` | Sessions after this time | `--after "2026-03-01"` |
| `--before TS` | Sessions before this time | `--before "2026-03-15"` |
| `--branch NAME` | Filter by git branch | `--branch develop` |
| `--deep` | Include tool calls and results | |
| `--json` | JSON output for analysis | |
| `--context N` | Surrounding messages (default: 1) | `--context 3` |
| `--case-sensitive` | Exact case matching | |

Timestamps accept: `2026-03-30`, `2026-03-30 17:30`, `2026-03-30T17:30:00`.

## Piping to Claude for Analysis

```bash
claude-session-search "auth" --project /path --json | claude "summarize what we decided"
```

## Common Patterns

- **Broad then narrow:** Start with a single keyword, add date/branch filters if noisy
- **Regex alternation:** `"TODO|FIXME|HACK"` or `"auth_v\d+"` for related terms
- **Deep search:** Use `--deep` when the answer is in a file that was read or a command that was run, not in the conversation text itself
