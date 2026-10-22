# Repository contributor guidance

This is the repository's own maintainer file. Do not use this directory as the demo target when testing `agent-rule-sentinel`.

- Target Python 3.10+ and prefer standard-library solutions.
- Keep default behavior non-mutating; require `--apply` for file writes.
- Preserve all user content outside managed markers.
- Add regression tests for changed behavior; document security limitations precisely.
- Run `python -m unittest discover -s tests -v` before opening a PR.
- Never add fabricated adoption statistics or claim affiliation with model providers.
