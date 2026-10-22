# Maintainer guide

This is a practical maintenance plan, not evidence that any external users or co-maintainers exist.

## Project responsibilities

- Triage Issues against duplicates and reproducible minimal examples.
- Prefer non-destructive behavior; review file-write changes very carefully.
- Check test coverage for symlink, malformed markers, backup, drift, and concurrency cases.
- Run local tests and GitHub Actions on each PR; CI is a baseline, not proof of complete security.
- Prepare changelog entries and release notes from actual commits.
- Respond respectfully and disclose unverified limitations.
- Never claim Star counts, downloads, adoption, funding eligibility, or organization endorsements without verifiable sources.

## Release checklist

1. Collect issues fixed, PRs merged, test results and documentation changes.
2. Run `python -m unittest discover -s tests -v` and `./scripts/smoke_test.sh`.
3. Verify README commands on a clean local folder and review every changed file.
4. Update `CHANGELOG.md` and the version in `pyproject.toml` and `src/agent_rule_sentinel/cli.py` together.
5. Publish a GitHub release from the exact tested commit, disclose known limitations and supported Python versions.
6. Monitor new issues and respond to regressions; publish security fixes responsibly.

## Evidence of active maintenance

After public publication, maintain a truthful log of releases, useful community Issues, reviewed PRs, tests, user reports and any package download metrics. Do not open sham PRs or generate artificial engagement.

## Security model

The CLI edits project-local files, and explicit `--apply` is the write boundary. It does not use shell evaluation, API credentials, network connections or model providers. Backups are intentionally local and private, but can contain sensitive original text. Malicious local processes with filesystem write access may race these checks; the tool is not designed as a hostile multi-user service.
