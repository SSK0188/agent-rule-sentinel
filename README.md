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
- Read-only `doctor`, safe import (`adopt`), conflict-aware restore (`undo`) in the development branch.
- Opt-in Gemini CLI (`GEMINI.md`) project instruction support.
- Refuses symlink targets, malformed markers, oversized files and several recognizable credential patterns.
- No background watcher or automatic commits, push, network calls, or AI model execution.

**Version note:** The commands below marked 0.2.0.dev0 exist on the unreleased `main` development branch, **not** in the published `v0.1.0` tag.

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


### New development commands (unreleased 0.2.0.dev0)

**Adopt existing rules before running init.** If a project has an unmanaged AGENTS.md but no shared source, you can import it without modifying AGENTS.md:

~~~bash
agent-rule-sentinel adopt --target codex          # preview (size and SHA-256)
agent-rule-sentinel adopt --target codex --apply  # create canonical source
~~~

Adoption refuses existing canonical source files, managed markers, symlinks and recognizable secret patterns. It **does not** translate tool-specific syntax or merge conflicting rules. Review the imported content before syncing to other assistants.

**Diagnose project health without changing files:**

~~~bash
agent-rule-sentinel doctor
agent-rule-sentinel doctor --json
~~~

Exit code: 0 = targets synchronized; 1 = drift; 2 = invalid input or missing source. Diagnose only the default Codex/Claude targets unless you select others.

**Preview and restore a newer backup snapshot:**

~~~bash
agent-rule-sentinel undo                  # show restore plan, do not write
agent-rule-sentinel undo --apply          # restore only unchanged destinations
agent-rule-sentinel undo --target codex --apply
agent-rule-sentinel undo --snapshot SNAPSHOT_NAME
~~~

Backups created by this development version include an integrity-checked manifest recording previous and generated file hashes. Undo refuses to overwrite files modified after sync, and can remove newly created target files if they are still unchanged. **Old backups without manifests must be restored manually.** Previews can display sensitive content; do not share private diff output.

**Opt in to Gemini CLI project rules:**

~~~bash
agent-rule-sentinel plan --target gemini
agent-rule-sentinel sync --target gemini --apply
agent-rule-sentinel check --all
~~~

For compatibility, default sync still covers only Codex and Claude. Gemini CLI normally uses `GEMINI.md` at the project level, but users can configure other context filenames; imports and provider-specific directives are not converted.

**Integrate drift detection with GitHub Actions.** Copy [the example workflow](examples/github-actions-agent-rules.yml) into your own project's `.github/workflows/` folder and commit the canonical source and selected managed files first. The sample currently installs from the development branch; **pin a tested release or commit** before production use.

**Installation / packaging:** CI validates wheel and source-distribution builds, but **there is no PyPI release**. For now, clone the GitHub repo and install from its source checkout via `python -m pip install -e .`.


### What happens to my existing files?

If `AGENTS.md` or `CLAUDE.md` does not exist, the tool creates it **only with `sync --apply`**. If it exists without the tool's markers, the tool **appends** a marked block, preserving earlier content. Subsequent synchronizations replace only the marked block. If markers are malformed or duplicated, the tool stops rather than guessing.

Private backups are stored in `.agent-rule-sentinel/backups/<UTC timestamp>-<random>/` within your project. To restore an existing file, inspect the backup and manually copy it back. The tool does not auto-delete backups. The backup directory uses owner-only permissions. Starting with the next update, the tool creates a scoped `.agent-rule-sentinel/backups/.gitignore` **before** saving snapshots so an ordinary `git add .` will not stage them even if your project lacks a root ignore rule. The harmless backup `.gitignore` file itself can be staged. If a different backup ignore file already exists, the tool refuses to overwrite it; inspect that file before retrying. Previously tracked files, forced additions (`git add -f`), and secrets in existing Git history are **not** protected by ignore rules. You can also add the directory to your project's top-level `.gitignore` as defense in depth.

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
| Gemini CLI (optional; development) | `GEMINI.md` | Synced managed block with `--target gemini` or `--all` |

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
