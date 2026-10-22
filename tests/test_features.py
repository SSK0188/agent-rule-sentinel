"""Integration tests for safe recovery, adoption, diagnostics, and opt-in tools."""
import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from agent_rule_sentinel.cli import main
from agent_rule_sentinel.core import END, SOURCE, START, GuardError, apply, initialize, plan
from agent_rule_sentinel.features import (
    apply_adopt, apply_undo, diagnose, plan_adopt, plan_undo, preview_undo,
)


class FeatureTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def cli(self, *args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return main(['--root', str(self.root), *args])

    def test_gemini_is_opt_in_by_default(self):
        initialize(self.root)
        self.assertEqual(self.cli('sync', '--apply'), 0)
        self.assertTrue((self.root / 'AGENTS.md').exists())
        self.assertTrue((self.root / 'CLAUDE.md').exists())
        self.assertFalse((self.root / 'GEMINI.md').exists())
        self.assertEqual(self.cli('sync', '--target', 'gemini', '--apply'), 0)
        self.assertTrue((self.root / 'GEMINI.md').exists())
        self.assertFalse(plan(self.root, ('gemini',))[0].dirty)

    def test_all_targets_and_conflicting_options(self):
        initialize(self.root)
        self.assertEqual(self.cli('sync', '--all', '--apply'), 0)
        self.assertTrue((self.root / 'GEMINI.md').exists())
        self.assertEqual(self.cli('check', '--all'), 0)
        self.assertEqual(self.cli('sync', '--all', '--target', 'codex'), 2)

    def test_doctor_read_only_and_exit_codes(self):
        code, result = diagnose(self.root)
        self.assertEqual(code, 2)
        self.assertEqual(result['source'], 'missing')
        self.assertFalse((self.root / SOURCE).exists())
        initialize(self.root)
        code, result = diagnose(self.root)
        self.assertEqual(code, 1)
        self.assertEqual(result['targets'], {'codex': 'drift', 'claude': 'drift'})
        self.assertFalse((self.root / 'AGENTS.md').exists())
        self.assertEqual(self.cli('sync', '--apply'), 0)
        self.assertEqual(self.cli('doctor'), 0)
        (self.root / 'AGENTS.md').write_text(END + '\n')
        code, result = diagnose(self.root)
        self.assertEqual(code, 2)
        self.assertEqual(result['targets']['codex'], 'error')

    def test_doctor_json(self):
        initialize(self.root)
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            status = main(['--root', str(self.root), 'doctor', '--json'])
        self.assertEqual(status, 1)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed['source'], 'ok')
        self.assertEqual(parsed['targets']['codex'], 'drift')

    def test_adopt_requires_explicit_apply_and_leaves_target_unmodified(self):
        original = '# Original instructions\r\nNever skip tests\r\n'
        (self.root / 'AGENTS.md').write_bytes(original.encode('utf-8'))
        self.assertEqual(self.cli('adopt', '--target', 'codex'), 0)
        self.assertFalse((self.root / SOURCE).exists())
        self.assertEqual(self.cli('adopt', '--target', 'codex', '--apply'), 0)
        self.assertEqual((self.root / SOURCE).read_bytes(), original.encode('utf-8'))
        self.assertEqual((self.root / 'AGENTS.md').read_bytes(), original.encode('utf-8'))

    def test_adopt_does_not_overwrite_existing_source(self):
        initialize(self.root)
        (self.root / 'AGENTS.md').write_text('Use tests\n')
        self.assertEqual(self.cli('adopt', '--target', 'codex', '--apply'), 2)
        self.assertIn('Shared project guidance', (self.root / SOURCE).read_text())

    def test_adopt_rejects_embedded_markers_and_possible_secrets(self):
        (self.root / 'AGENTS.md').write_text(START + '\nsecret\n' + END + '\n')
        self.assertEqual(self.cli('adopt', '--target', 'codex', '--apply'), 2)
        self.assertFalse((self.root / SOURCE).exists())
        (self.root / 'AGENTS.md').write_text('api_key: superSecretCredential\n')
        self.assertEqual(self.cli('adopt', '--target', 'codex', '--apply'), 2)
        self.assertFalse((self.root / SOURCE).exists())

    def test_adopt_refuses_symlink(self):
        elsewhere = self.root / 'elsewhere.md'
        elsewhere.write_text('Outside content')
        (self.root / 'AGENTS.md').symlink_to(elsewhere)
        self.assertEqual(self.cli('adopt', '--target', 'codex', '--apply'), 2)
        self.assertFalse((self.root / SOURCE).exists())

    def test_adopt_refuses_change_after_preview(self):
        existing = self.root / 'AGENTS.md'
        existing.write_text('first\n')
        _, initial = plan_adopt(self.root, 'codex')
        existing.write_text('second\n')
        with self.assertRaises(GuardError):
            apply_adopt(self.root, 'codex', initial)
        self.assertFalse((self.root / SOURCE).exists())

    def test_undo_existing_file_preserves_exact_crlf_content(self):
        initialize(self.root)
        initial = b'Personal\r\nDo not remove\r\n'
        target = self.root / 'AGENTS.md'
        target.write_bytes(initial)
        self.assertEqual(self.cli('sync', '--target', 'codex', '--apply'), 0)
        modified = target.read_bytes()
        recovery = plan_undo(self.root)
        self.assertEqual(len(recovery.items), 1)
        self.assertIn('[RESTORE] AGENTS.md', preview_undo(recovery))
        self.assertEqual(target.read_bytes(), modified)
        self.assertEqual(self.cli('undo', '--apply'), 0)
        self.assertEqual(target.read_bytes(), initial)

    def test_undo_removes_only_file_created_by_sync(self):
        initialize(self.root)
        self.assertFalse((self.root / 'GEMINI.md').exists())
        self.assertEqual(self.cli('sync', '--target', 'gemini', '--apply'), 0)
        self.assertTrue((self.root / 'GEMINI.md').exists())
        self.assertEqual(self.cli('undo'), 0)
        self.assertTrue((self.root / 'GEMINI.md').exists())
        self.assertEqual(self.cli('undo', '--apply'), 0)
        self.assertFalse((self.root / 'GEMINI.md').exists())

    def test_undo_refuses_to_overwrite_user_changes(self):
        initialize(self.root)
        target = self.root / 'CLAUDE.md'
        target.write_text('Original instructions\n')
        self.assertEqual(self.cli('sync', '--target', 'claude', '--apply'), 0)
        target.write_text('I changed this AFTER syncing\n')
        self.assertEqual(self.cli('undo', '--apply'), 2)
        self.assertEqual(target.read_text(), 'I changed this AFTER syncing\n')

    def test_undo_multiple_target_subset(self):
        initialize(self.root)
        a = self.root / 'AGENTS.md'
        c = self.root / 'CLAUDE.md'
        a.write_text('Codex original\n')
        c.write_text('Claude original\n')
        self.assertEqual(self.cli('sync', '--apply'), 0)
        with contextlib.redirect_stdout(io.StringIO()):
            code = main(['--root', str(self.root), 'undo', '--target', 'codex', '--apply'])
        self.assertEqual(code, 0)
        self.assertEqual(a.read_text(), 'Codex original\n')
        self.assertIn(START, c.read_text())

    def test_undo_refuses_tampered_backup_copy(self):
        initialize(self.root)
        target = self.root / 'AGENTS.md'
        target.write_text('Old\n')
        self.assertEqual(self.cli('sync', '--target', 'codex', '--apply'), 0)
        good = plan_undo(self.root)
        snapshot_dir = self.root / '.agent-rule-sentinel/backups' / good.snapshot
        (snapshot_dir / 'AGENTS.md').write_text('Tampered\n')
        self.assertEqual(self.cli('undo', '--apply'), 2)
        self.assertIn(START, target.read_text())

    def test_undo_refuses_tampered_manifest_and_path_traversal(self):
        initialize(self.root)
        self.assertEqual(self.cli('sync', '--target', 'codex', '--apply'), 0)
        good = plan_undo(self.root)
        backup_dir = self.root / '.agent-rule-sentinel/backups' / good.snapshot
        manifest = json.loads((backup_dir / 'manifest.json').read_text())
        manifest['entries'][0]['target'] = '../secret'
        (backup_dir / 'manifest.json').write_text(json.dumps(manifest))
        self.assertEqual(self.cli('undo', '--apply'), 2)
        with self.assertRaises(GuardError):
            plan_undo(self.root, snapshot='../other')

    def test_undo_legacy_snapshot_requires_manual_restoration(self):
        initialize(self.root)
        backup_root = self.root / '.agent-rule-sentinel/backups'
        backup_root.mkdir(mode=0o700)
        old = backup_root / '20260101T000000Z-aabbccdd'
        old.mkdir(mode=0o700)
        (old / 'AGENTS.md').write_text('old snapshot with no manifest')
        self.assertEqual(self.cli('undo'), 2)

    def test_manifest_hashes_match_written_files(self):
        initialize(self.root)
        target = self.root / 'AGENTS.md'
        original = 'original\n'
        target.write_text(original)
        self.assertEqual(self.cli('sync', '--target', 'codex', '--apply'), 0)
        recovery = plan_undo(self.root)
        manifest_path = (self.root / '.agent-rule-sentinel/backups' /
                         recovery.snapshot / 'manifest.json')
        manifest = json.loads(manifest_path.read_text())
        entry = manifest['entries'][0]
        self.assertEqual(entry['before_sha256'],
                         hashlib.sha256(original.encode()).hexdigest())
        self.assertEqual(entry['after_sha256'],
                         hashlib.sha256(target.read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()
