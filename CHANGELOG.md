# Changelog

## Unreleased

- Preserve existing CRLF line endings when syncing to Windows-style rule files (merged in PR #2 after v0.1.0).
- Create a scoped Git ignore guard before storing sensitive backup snapshots; fail safely on conflicting or symlinked ignore files (Issue #3).
- Verify `git add .` does not stage backup snapshots, and add a macOS CI job with smoke tests.

## 0.1.0 - 2026-10-22

Initial source release: local-first project instruction synchronization, explicit preview/apply, managed blocks, basic credential-pattern rejection, private backups, drift checks, documentation, and unit tests.

GitHub v0.1.0 release: https://github.com/SSK0188/agent-rule-sentinel/releases/tag/v0.1.0 . No package registry publication is claimed.
