# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run a single test file
python3 -m pytest tests/test_search_engine.py -v

# Run a single test
python3 -m pytest tests/test_integration.py::test_search_finds_auth -v

# Run the tool against real data (all projects)
./claude_session_search.py "query"

# Run against a specific project
./claude_session_search.py "query" --project /path/to/project
```

## Architecture

Single-file CLI tool (`claude_session_search.py`) with no external dependencies — Python 3.10+ stdlib only.

**Data pipeline:** `resolve_project_dir` → `load_sessions` → `filter_sessions` → `extract_messages` → `search_messages` → `format_*_output`

- **resolve_project_dir**: Converts a real filesystem path (e.g. `/home/user/Dev/foo`) to the matching `~/.claude/projects/-home-user-Dev-foo` directory by replacing `/` with `-`
- **load_sessions**: Discovers `.jsonl` files on disk (not just from `sessions-index.json`, which can be stale) and enriches with index metadata where available
- **extract_messages**: Parses JSONL transcript lines, yielding `{role, text, timestamp}` dicts. Skips thinking blocks. In `--deep` mode, includes tool_use/tool_result content
- **search_messages**: Regex search with context window (N messages before/after)
- **format_terminal_output** / **format_json_output**: Two output modes — colored terminal or JSON for piping

All functions accept dependency-injected paths (e.g. `claude_dir` parameter) to enable testing with `tmp_path` fixtures without touching real `~/.claude/` data.
