import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_rule_sentinel.core import (
    SOURCE, TARGETS, START, END, GuardError, apply, initialize,
    plan, preview, render, validate_source,
)
from agent_rule_sentinel.cli import main


class ProjectTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        initialize(self.root)

    def test_initializes_source_and_refuses_overwrite(self):
        self.assertTrue((self.root / SOURCE).exists())
        with self.assertRaises(GuardError):
            initialize(self.root)

    def test_init_does_not_create_target(self):
        for relative in TARGETS.values():
            self.assertFalse((self.root / relative).exists())

    def test_plan_does_not_write(self):
        changes = plan(self.root, ('codex', 'claude'))
        self.assertEqual(len(changes), 2)
        self.assertTrue(all(change.dirty for change in changes))
        self.assertFalse((self.root / 'AGENTS.md').exists())

    def test_preview_contains_diff(self):
        text = preview(plan(self.root, ('codex',)))
        self.assertIn('+++ AGENTS.md', text)
        self.assertIn('BEGIN', text)

    def test_apply_is_idempotent(self):
        changes = plan(self.root, ('codex', 'claude'))
        apply(self.root, changes)
        clean = plan(self.root, ('codex', 'claude'))
        self.assertFalse(any(c.dirty for c in clean))
        self.assertIsNone(apply(self.root, clean))

    def test_appends_preserving_existing_text(self):
        target = self.root / 'AGENTS.md'
        target.write_text('# My personal notes\n\nKeep me.\n', encoding='utf-8')
        apply(self.root, plan(self.root, ('codex',)))
        result = target.read_text()
        self.assertTrue(result.startswith('# My personal notes\n\nKeep me.\n'))
        self.assertIn(START, result)
        self.assertIn(END, result)

    def test_updates_managed_area_and_keeps_user_content(self):
        target = self.root / 'CLAUDE.md'
        target.write_text('before\n'+START+'\nold\n'+END+'\nafter\n')
        apply(self.root, plan(self.root, ('claude',)))
        text = target.read_text()
        self.assertTrue(text.startswith('before\n'))
        self.assertTrue(text.endswith('\nafter\n'))
        self.assertNotIn('\nold\n', text)

    def test_detects_corrupt_markers(self):
        for content in [START, END, END+'\n'+START, START+'\n'+START+'\n'+END]:
            with self.subTest(content=content):
                with self.assertRaises(GuardError):
                    render(content, 'Hello')

    def test_detects_secret_patterns(self):
        for secret in [
            'password=longPasswordHere',
            '-----BEGIN OPENSSH PRIVATE KEY-----',
            'api_key: superSecretCredential',
            'sk-'+'A'*25,
            'ghp_'+'A'*30,
        ]:
            with self.subTest(secret=secret):
                with self.assertRaises(GuardError):
                    validate_source(secret)

    def test_no_fake_claim_of_complete_secret_scanning(self):
        validate_source('Avoid committing private configuration files.')

    def test_source_markers_rejected(self):
        with self.assertRaises(GuardError):
            validate_source('instruction\n'+START)

    def test_source_symlink_rejected(self):
        other = self.root / 'other.txt'
        other.write_text('hello')
        (self.root / SOURCE).unlink()
        (self.root / SOURCE).symlink_to(other)
        with self.assertRaises(GuardError):
            plan(self.root, ('codex',))

    def test_target_symlink_rejected(self):
        (self.root / 'AGENTS.md').symlink_to(self.root / SOURCE)
        with self.assertRaises(GuardError):
            plan(self.root, ('codex',))

    def test_preserves_existing_mode(self):
        target = self.root / 'AGENTS.md'
        target.write_text('existing\n')
        target.chmod(0o600)
        apply(self.root, plan(self.root, ('codex',)))
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)

    def test_private_backup_contains_previous_content(self):
        target = self.root / 'AGENTS.md'
        target.write_text('previous\n')
        result = apply(self.root, plan(self.root, ('codex',)))
        saved = Path(result) / 'AGENTS.md'
        self.assertEqual(saved.read_text(), 'previous\n')
        self.assertEqual(saved.stat().st_mode & 0o777, 0o600)
        self.assertEqual(Path(result).parent.stat().st_mode & 0o777, 0o700)

    def test_change_between_plan_and_apply_rejected(self):
        changes = plan(self.root, ('codex',))
        (self.root / 'AGENTS.md').write_text('unexpected edit')
        with self.assertRaises(GuardError):
            apply(self.root, changes)
        self.assertEqual((self.root / 'AGENTS.md').read_text(), 'unexpected edit')

    def test_check_detects_drift(self):
        self.assertEqual(main(['--root', str(self.root), 'check']), 1)
        apply(self.root, plan(self.root, ('codex', 'claude')))
        self.assertEqual(main(['--root', str(self.root), 'check']), 0)

    def test_sync_requires_apply_flag(self):
        self.assertEqual(main(['--root', str(self.root), 'sync']), 0)
        self.assertFalse((self.root / 'AGENTS.md').exists())
        self.assertEqual(main(['--root', str(self.root), 'sync', '--apply']), 0)
        self.assertTrue((self.root / 'AGENTS.md').exists())

    def test_missing_source_is_error(self):
        (self.root / SOURCE).unlink()
        self.assertEqual(main(['--root', str(self.root), 'plan']), 2)

    def test_does_not_write_to_outside_project(self):
        outsider = self.root.parent / 'untrusted.md'
        self.assertEqual(render(None, 'test').count(START), 1)
        with self.assertRaises(GuardError):
            from agent_rule_sentinel.core import _checked_path
            _checked_path(self.root, Path('../untrusted.md'))

    def test_unknown_target_rejected(self):
        with self.assertRaises(GuardError):
            plan(self.root, ('unknown',))


if __name__ == '__main__':
    unittest.main()
