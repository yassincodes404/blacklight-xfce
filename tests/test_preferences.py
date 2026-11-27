"""Check reversible preferences, readable accents and app scheduling boundaries."""
import copy
import json
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'home/.local/share/galinia'))
import preferences
import performance


class PreferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'galinia/preferences.json'

    def test_invalid_or_unreadable_accent_cannot_overwrite_a_saved_profile(self):
        data = preferences.load(self.path)
        data['accent_mode'] = 'fixed'
        preferences.save(data, self.path)
        before = self.path.read_text()
        for invalid in ['#000000', '#123', 'not-a-color']:
            data['fixed_accent'] = invalid
            with self.assertRaises(ValueError):
                preferences.save(data, self.path)
            self.assertEqual(self.path.read_text(), before)

    def test_save_and_undo_restore_prior_preferences(self):
        data = preferences.load(self.path)
        data.update(accent_mode='fixed', fixed_accent='#9bbcff')
        preferences.save(data, self.path)
        self.assertEqual(preferences.load(self.path)['fixed_accent'], '#9bbcff')
        preferences.undo(self.path)
        self.assertEqual(preferences.load(self.path), preferences.DEFAULTS)
        self.assertFalse(self.path.with_name('preferences.previous.json').exists())

    def test_failed_runtime_change_rolls_panel_back_to_its_actual_previous_size(self):
        calls = []
        def run(command):
            calls.append(command)
            if command[0] == 'systemctl':
                raise RuntimeError('user bus unavailable')
            return types.SimpleNamespace(stdout='31\n')
        data = preferences.load(self.path)
        data.update(panel_size=40, monitor_enabled=False)
        with self.assertRaisesRegex(RuntimeError, 'user bus'):
            preferences.apply_desktop(data, self.path, run)
        self.assertEqual(calls[-1][-2:], ['-s', '31'])
        self.assertFalse(self.path.exists())

    def test_app_priorities_have_no_memory_cap_realtime_policy_or_cpu_quota(self):
        data = preferences.load(self.path)
        data['app_profiles']['org.example.App.desktop'] = 'background'
        flags = preferences.resource_flags('org.example.App.desktop', data)
        self.assertIn('--property=CPUWeight=20', flags)
        self.assertIn('--property=Nice=10', flags)
        self.assertEqual(preferences.resource_flags('other.desktop', data), ['--property=CPUWeight=100'])
        self.assertFalse(any(word in ' '.join(flags) for word in ['MemoryMax', 'CPUQuota', 'realtime']))

    def test_fixed_palette_changes_accents_without_mutating_source_palette(self):
        original = {'accent_hex': '#ffffff', 'accent_rgb': [255,255,255], 'bg_0': '#111111'}
        before = copy.deepcopy(original)
        data = preferences.load(self.path); data.update(accent_mode='fixed', fixed_accent='#9de6b6')
        result = preferences.apply_palette(original, data)
        self.assertEqual(original, before)
        self.assertEqual(result['accent_hex'], '#9de6b6')
        self.assertEqual(result['bg_0'], '#111111')
        self.assertGreaterEqual(preferences.contrast(result['accent_hex'], result['sel_fg_hex']), 4.5)

    def test_disabled_monitor_is_not_restarted_at_login(self):
        directory = Path(self.temp.name)
        data = preferences.load(self.path); data['monitor_enabled'] = False
        preferences.save(data, self.path)
        stub = directory / 'systemctl'
        stub.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$TEST_CALL_LOG"\nexit 0\n')
        stub.chmod(0o755)
        log = directory / 'calls'
        env = {**os.environ, 'PATH': str(directory) + ':' + os.environ['PATH'],
               'XDG_CONFIG_HOME': str(directory), 'TEST_CALL_LOG': str(log)}
        activation = directory / 'dbus-update-activation-environment'
        activation.write_text('#!/bin/sh\nexit 0\n'); activation.chmod(0o755)
        env['XDG_SESSION_TYPE'] = 'x11'
        subprocess.run(['sh', str(ROOT / 'home/.local/bin/galinia-session'), '--once'], env=env, check=True)
        calls = log.read_text()
        self.assertIn('stop sysmon-widget.service', calls)
        self.assertNotIn('restart sysmon-widget.service', calls)
        self.assertIn('restart galinia-search.service', calls)


class PressureTests(unittest.TestCase):
    def test_optional_kernel_files_can_be_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / 'proc').mkdir()
            (root / 'proc/meminfo').write_text('MemTotal: 4096000 kB\nMemAvailable: 2048000 kB\n')
            (root / 'proc/swaps').write_text('Filename Type Size Used Priority\n/dev/zram0 partition 1048576 512 -1\n')
            data = performance.snapshot(root)
            self.assertEqual(data['total_mib'], 4000)
            self.assertEqual(data['available_mib'], 2000)
            self.assertEqual(data['governor'], 'unavailable')
            self.assertEqual(data['swaps'][0]['type'], 'zram')
            self.assertEqual(data['cpu_pressure'], {})

    def test_idle_policy_uses_minutes_for_both_power_supplies(self):
        root = ROOT / 'home/.config/xfce4/xfconf/xfce-perchannel-xml'
        power = ET.parse(root / 'xfce4-power-manager.xml')
        entries = {node.get('name'): node.get('value') for node in power.iter('property')}
        for supply in ['ac', 'battery']:
            for key in [f'blank-on-{supply}', f'dpms-on-{supply}-sleep', f'dpms-on-{supply}-off', f'inactivity-on-{supply}']:
                self.assertEqual(entries[key], '40', key)
        saver = ET.parse(root / 'xfce4-screensaver.xml')
        delay = saver.find("./property[@name='saver']/property[@name='idle-activation']/property[@name='delay']")
        self.assertEqual(delay.get('value'), '40')

    def test_render_never_copies_runtime_python_caches(self):
        sys.path.insert(0, str(ROOT / 'tools'))
        import control
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'source/home/.config/blacklight-rice').mkdir(parents=True)
            (root / 'source/home/__pycache__').mkdir()
            (root / 'source/home/__pycache__/test.pyc').write_bytes(b'cache')
            (root / 'source/home/extra.pyc').write_bytes(b'cache')
            with patch.object(control, 'ROOT', root / 'source'):
                control.render(argparse.Namespace(output=root / 'stage', target_home=root / 'account', wallpaper=None))
            self.assertFalse((root / 'stage/__pycache__').exists())
            self.assertFalse((root / 'stage/extra.pyc').exists())


if __name__ == '__main__':
    unittest.main()
