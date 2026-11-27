"""Check Firefox preference preservation/rollback and proportional-memory grouping."""
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import firefox_memory as memory
import memory_report


class FirefoxMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.profile = Path(self.temp.name)
        (self.profile / 'prefs.js').write_text('user_pref("browser.cache.memory.capacity", 65536);\nuser_pref("keep.this", true);\n')

    def test_apply_is_idempotent_and_preserves_unrelated_preferences(self):
        user = self.profile / 'user.js'
        user.write_text('user_pref("keep.custom", "hello");\n')
        memory.apply(self.profile, 'aggressive')
        self.assertIn('user_pref("keep.custom", "hello");', user.read_text())
        self.assertIsNone(memory.apply(self.profile, 'aggressive'))
        self.assertEqual(user.read_text().count(memory.START), 1)

    def test_restore_clears_saved_new_prefs_and_keeps_other_browser_changes(self):
        backup = memory.apply(self.profile, 'aggressive')
        prefs = self.profile / 'prefs.js'
        prefs.write_text(prefs.read_text() + 'user_pref("browser.tabs.unloadOnLowMemory", true);\nuser_pref("keep.later", 7);\n')
        memory.restore(self.profile, backup)
        self.assertFalse((self.profile / 'user.js').exists())
        self.assertNotIn('browser.tabs.unloadOnLowMemory', prefs.read_text())
        self.assertIn('user_pref("browser.cache.memory.capacity", 65536);', prefs.read_text())
        self.assertIn('user_pref("keep.later", 7);', prefs.read_text())

    def test_running_profile_and_later_user_edits_block_restore(self):
        backup = memory.apply(self.profile, 'aggressive')
        lock = self.profile / 'lock'
        lock.symlink_to('127.0.0.1:+' + str(os.getpid()))
        with self.assertRaisesRegex(ValueError, 'Close Firefox'):
            memory.restore(self.profile, backup)
        lock.unlink()
        user = self.profile / 'user.js'
        user.write_text(user.read_text() + '// a later edit\n')
        with self.assertRaisesRegex(ValueError, 'changed since'):
            memory.restore(self.profile, backup)

    def test_switching_modes_and_restoring_previous_mode_preserves_user_js(self):
        memory.apply(self.profile, 'balanced')
        original = (self.profile / 'user.js').read_text()
        backup = memory.apply(self.profile, 'aggressive')
        memory.restore(self.profile, backup)
        self.assertEqual((self.profile / 'user.js').read_text(), original)

    def test_malformed_block_is_rejected_without_overwrite(self):
        user = self.profile / 'user.js'
        user.write_text(memory.START + '\n')
        with self.assertRaises(ValueError):
            memory.apply(self.profile, 'aggressive')
        self.assertEqual(user.read_text(), memory.START + '\n')


class MemoryReportTests(unittest.TestCase):
    def test_child_processes_group_under_their_app_without_double_counting(self):
        rows = {1: {'pid': 1, 'ppid': 0, 'name': 'firefox-bin'},
                2: {'pid': 2, 'ppid': 1, 'name': 'Web Content'},
                3: {'pid': 3, 'ppid': 0, 'name': 'code'}}
        self.assertEqual(memory_report.group(rows[2], rows), 'Firefox')
        self.assertEqual(memory_report.group(rows[3], rows), 'VS Code')

    def test_process_cycles_do_not_hang_and_meminfo_fields_are_parsed(self):
        row = {'pid': 1, 'ppid': 1, 'name': 'unknown'}
        self.assertEqual(memory_report.group(row, {1: row}), 'Other user processes')
        self.assertEqual(memory_report.fields('Pss: 1024 kB\nRss: 2048 kB\n'), {'Pss': 1024, 'Rss': 2048})
