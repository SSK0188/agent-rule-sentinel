# Agent Rule Sentinel

**A local-first, review-before-write synchronizer for Codex and Claude Code project instructions.**

[中文说明](docs/README.zh-CN.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Roadmap](ROADMAP.md)

Keep a canonical set of project instructions in `.agent-rule-sentinel/source.md`, then produce consistent managed blocks in `AGENTS.md` (Codex) and `CLAUDE.md` (Claude Code). **You always preview changes first.** No provider account, API key or network connection is required.

## Why?

Developers working across multiple coding agents often duplicate project rules. Edits drift, and an automated overwrite could erase personal or agent-specific instructions. Agent Rule Sentinel updates only a clearly marked section, leaving surrounding content untouched.

## Features

- Zero runtime dependencies (Python 3.10+), offline by design.
- `plan` previews unified diffs, with no writes.
- `sync --apply` only changes explicitly selected target files.
- Existing custom text outside managed markers is preserved.
- Existing targets are privately backed up before replacement; newly created targets are not backed up.
- `check` detects drift for CI, returning status 1 when a target needs synchronization.
- Refuses symlink targets, malformed markers, oversized files and several recognizable credential patterns.
- No background watcher or automatic commits, push, network calls, or AI model execution.

**Security scope:** The credential detector is heuristic, not an exhaustive secret scanner. Review the source and diffs before committing generated files. Backups may contain sensitive content and are ignored by Git.

## Quickstart

```bash
# From the repository root, Python >=3.10:
python -m pip install -e .

# From the ROOT of YOUR OWN project (not this repository):
agent-rule-sentinel init
# Edit .agent-rule-sentinel/source.md with real project instructions.
agent-rule-sentinel plan
agent-rule-sentinel sync --apply
agent-rule-sentinel check
```

Example output from `plan`:

```diff
[CHANGED] AGENTS.md
--- AGENTS.md (current)
+++ AGENTS.md (proposed)
+<!-- agent-rule-sentinel:BEGIN; managed block; edits will be replaced -->
+... your project rules ...
+<!-- agent-rule-sentinel:END -->
```

**Select a single target:**

```bash
agent-rule-sentinel plan --target codex
agent-rule-sentinel sync --target claude --apply
agent-rule-sentinel --root /path/to/project check
```

### What happens to my existing files?

If `AGENTS.md` or `CLAUDE.md` does not exist, the tool creates it **only with `sync --apply`**. If it exists without the tool's markers, the tool **appends** a marked block, preserving earlier content. Subsequent synchronizations replace only the marked block. If markers are malformed or duplicated, the tool stops rather than guessing.

Private backups are stored in `.agent-rule-sentinel/backups/<UTC timestamp>-<random>/` within your project. To restore an existing file, inspect the backup and manually copy it back. The tool does not auto-delete backups. The backup folder is created with owner-only permissions; the directory is excluded via this repository's `.gitignore`, and you should add the same entry to the `.gitignore` in projects using this tool.

```gitignore
.agent-rule-sentinel/backups/
```

### Automating drift detection

After generated files have been committed to your repository, use:

```bash
agent-rule-sentinel check
```

The command returns 0 when synchronized, 1 for drift, 2 for invalid or unsafe input. This makes it easy to wire into an existing CI job.

## Supported targets

| Tool | File | Behavior |
| --- | --- | --- |
| OpenAI Codex | `AGENTS.md` | Synced managed block |
| Claude Code | `CLAUDE.md` | Synced managed block |

The project does not claim to synchronize user-level settings, provider memories, skills, personal conversations, token budgets, or cloud accounts. It does not translate between agent-specific syntax; write common, portable Markdown rules in the canonical source.

## Development

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m compileall -q src
```

Public API stability is not guaranteed before v1.0. Please use Issues to propose changes and submit focused, tested PRs.

## Privacy and limits

This tool reads/writes local Markdown files in the designated project, and no telemetry is included. It cannot guarantee that agent products interpret every instruction identically. Symlink paths are refused. Do not point it at a production workspace without reviewing its planned changes. The project is not affiliated with OpenAI or Anthropic.

## License

MIT. See [LICENSE](LICENSE).
