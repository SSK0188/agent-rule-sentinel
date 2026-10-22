#!/bin/sh
# Non-destructive smoke test in a brand-new temporary directory.
set -eu
workspace=$(mktemp -d)
trap 'rm -rf "$workspace"' EXIT HUP INT TERM
agent-rule-sentinel --root "$workspace" init
agent-rule-sentinel --root "$workspace" plan >/dev/null
agent-rule-sentinel --root "$workspace" sync --apply >/dev/null
agent-rule-sentinel --root "$workspace" check >/dev/null
printf 'smoke test passed: local workspace initialized, applied and checked\n'
