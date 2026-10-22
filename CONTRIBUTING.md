# Contributing

Thank you for helping improve Agent Rule Sentinel. All contributions must be genuine and independently reviewable.

1. Search open Issues and PRs for duplication. For feature requests or file format changes, open an Issue first.
2. Fork the repository, create a focused branch, and write a regression test for behavior changes.
3. Run `python -m unittest discover -s tests -v` and `python -m compileall -q src`.
4. Keep each PR focused. Explain user impact, before/after behavior, tests, security implications and known limits.
5. Never commit actual credentials, private data, copies of a user's `AGENTS.md`, or backup files.
6. AI-assisted code is welcome if you understand and verify every line, including failure behavior and security edge cases.

Maintainers will review contributions as available. There is no guaranteed response time or automatic path to write access. Reports of security vulnerabilities belong in private channels; see [SECURITY.md](SECURITY.md).
