# Changelog

## Unreleased

### Development features (0.2.0.dev0)

- Add manifest-backed conflict-aware undo of newer backup snapshots.
- Add safe import of existing unmanaged rules (`adopt`).
- Add read-only diagnostics with machine-readable JSON (`doctor`).
- Add opt-in Gemini CLI project `GEMINI.md` support without changing existing default targets.
- Add a reusable GitHub Actions drift-check example and test wheel/sdist builds.
- Add regression tests for recovery, file integrity, adoption and diagnostics.
- These changes are not part of the published v0.1.0 release; PyPI publication has not occurred.


- Preserve existing CRLF line endings when syncing to Windows-style rule files (merged in PR #2 after v0.1.0).
- Create a scoped Git ignore guard before storing sensitive backup snapshots; fail safely on conflicting or symlinked ignore files (Issue #3).
- Verify `git add .` does not stage backup snapshots, and add a macOS CI job with smoke tests.

## 0.1.0 - 2026-10-22

Initial source release: local-first project instruction synchronization, explicit preview/apply, managed blocks, basic credential-pattern rejection, private backups, drift checks, documentation, and unit tests.

GitHub v0.1.0 release: https://github.com/SSK0188/agent-rule-sentinel/releases/tag/v0.1.0 . No package registry publication is claimed.
