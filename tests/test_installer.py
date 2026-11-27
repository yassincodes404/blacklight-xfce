"""Exercise profile changes in disposable homes; never touch the live desktop."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
spec = importlib.util.spec_from_file_location('galinia_install', ROOT / 'tools/install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / 'user'
        self.stage = self.root / 'stage'
        self.history = self.root / 'history'
        for path in [self.home, self.stage, self.history]:
            path.mkdir()

    def put(self, base, relative, text, mode=0o644):
        path = base / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        path.chmod(mode)
        return path

    def test_install_repeat_and_restore_preserve_file_mode_symlink_and_unrelated_data(self):
        self.put(self.home, '.config/theme', 'original', 0o600)
        self.put(self.home, 'notes.txt', 'personal')
        (self.home / 'alias').symlink_to('notes.txt')
        self.put(self.stage, '.config/theme', 'galinia')
        self.put(self.stage, '.local/bin/tool', '#!/bin/sh\nexit 0\n', 0o755)
        self.put(self.stage, 'alias', 'replaced link')
        backup = installer.install_transaction(self.stage, self.home, self.history)
        self.assertEqual((self.home / '.config/theme').read_text(), 'galinia')
        self.assertEqual((self.home / '.local/bin/tool').stat().st_mode & 0o777, 0o755)
        self.assertIsNone(installer.install_transaction(self.stage, self.home, self.history))
        installer.restore_transaction(backup, self.home)
        self.assertEqual((self.home / '.config/theme').read_text(), 'original')
        self.assertEqual((self.home / '.config/theme').stat().st_mode & 0o777, 0o600)
        self.assertEqual(os.readlink(self.home / 'alias'), 'notes.txt')
        self.assertEqual((self.home / 'notes.txt').read_text(), 'personal')
        self.assertFalse((self.home / '.local/bin/tool').exists())
        installer.restore_transaction(backup, self.home)

    def test_failure_during_write_restores_all_changes(self):
        self.put(self.home, 'a', 'old')
        self.put(self.stage, 'a', 'new')
        self.put(self.stage, 'b', 'new file')
        real_copy = installer.copy_atomic
        def fail_second(source, dest):
            if source == self.stage / 'b':
                raise OSError('simulated disk error')
            real_copy(source, dest)
        with patch.object(installer, 'copy_atomic', side_effect=fail_second):
            with self.assertRaisesRegex(OSError, 'simulated disk error'):
                installer.install_transaction(self.stage, self.home, self.history)
        self.assertEqual((self.home / 'a').read_text(), 'old')
        self.assertFalse((self.home / 'b').exists())
        journal = next(self.history.glob('*/journal.json'))
        self.assertEqual(json.loads(journal.read_text())['status'], 'restored')

    def test_restore_conflict_is_detected_before_any_file_is_restored(self):
        for name in ['a', 'b']:
            self.put(self.home, name, 'old')
            self.put(self.stage, name, 'new')
        backup = installer.install_transaction(self.stage, self.home, self.history)
        (self.home / 'b').write_text('my later edit')
        with self.assertRaisesRegex(ValueError, 'Restore conflict'):
            installer.restore_transaction(backup, self.home)
        self.assertEqual((self.home / 'a').read_text(), 'new')
        self.assertEqual((self.home / 'b').read_text(), 'my later edit')

    def test_corrupt_backup_does_not_replace_installed_files(self):
        self.put(self.home, 'a', 'old')
        self.put(self.stage, 'a', 'new')
        backup = installer.install_transaction(self.stage, self.home, self.history)
        (backup / 'originals/a').write_text('damaged')
        with self.assertRaisesRegex(ValueError, 'integrity'):
            installer.restore_transaction(backup, self.home)
        self.assertEqual((self.home / 'a').read_text(), 'new')

    def test_explicit_conflict_preservation_makes_restore_usable_after_runtime_edits(self):
        self.put(self.home, 'theme', 'original')
        self.put(self.stage, 'theme', 'installed')
        backup = installer.install_transaction(self.stage, self.home, self.history)
        (self.home / 'theme').write_text('runtime-generated palette')
        installer.restore_transaction(backup, self.home, save_conflicts=True)
        self.assertEqual((self.home / 'theme').read_text(), 'original')
        saved = next((backup / 'conflicts').glob('*/files/theme'))
        self.assertEqual(saved.read_text(), 'runtime-generated palette')

    def test_symlinked_parent_and_escaping_stage_link_are_rejected(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (self.home / '.config').symlink_to(outside, target_is_directory=True)
        self.put(self.stage, '.config/theme', 'new')
        with self.assertRaisesRegex(ValueError, 'real directory'):
            installer.changes(self.stage, self.home)
        (self.home / '.config').unlink()
        (self.stage / 'escape').symlink_to('/etc/passwd')
        with self.assertRaisesRegex(ValueError, 'escapes'):
            installer.changes(self.stage, self.home)
        self.assertFalse(list(outside.iterdir()))
        with self.assertRaises(ValueError):
            installer.checked_path(self.home, '../escape')

    def test_merges_preserve_custom_handlers_and_session_commands(self):
        old = '[Default Applications]\nx-scheme-handler/https=custom.desktop\nimage/png=old.desktop\n[Added Associations]\napplication/zip=other.desktop;\n'
        new = '[Default Applications]\nimage/png=galinia.desktop\n[Added Associations]\napplication/zip=galinia.desktop;\n'
        merged = installer.merged_mime(old, new)
        self.assertIn('x-scheme-handler/https=custom.desktop', merged)
        self.assertIn('image/png=galinia.desktop', merged)
        self.assertIn('application/zip=galinia.desktop;other.desktop;', merged)
        self.assertEqual(installer.merged_mime(merged, new), merged)
        session = installer.merged_xsession('export MY_SETTING=keep\n', 'export GALINIA=1\n')
        self.assertIn('export MY_SETTING=keep', session)
        self.assertEqual(installer.merged_xsession(session, 'export GALINIA=1\n'), session)

    def test_running_session_is_refused_even_without_display_environment(self):
        result = type('Result', (), {'returncode': 0})()
        with patch.object(installer.subprocess, 'run', return_value=result):
            with self.assertRaisesRegex(ValueError, 'Log out'):
                installer.require_logged_out()

    def test_unfinished_install_and_restore_order_are_enforced(self):
        for ident, status in [('20261127T000000Z-11111111', 'installing'), ('20261127T000001Z-22222222', 'installed')]:
            path = self.history / ident
            path.mkdir()
            (path / 'journal.json').write_text(json.dumps({'status': status}))
        with self.assertRaisesRegex(ValueError, 'interrupted'):
            installer.check_history(self.history)
        with self.assertRaisesRegex(ValueError, 'newer'):
            installer.check_history(self.history, '20261127T000000Z-11111111')


if __name__ == '__main__':
    unittest.main()
