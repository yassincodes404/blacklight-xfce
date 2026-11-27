"""Notification controls must write native typed settings without touching app rules."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('notifications', ROOT/'home/.local/share/galinia/notifications.py')
notifications = importlib.util.module_from_spec(spec); spec.loader.exec_module(notifications)


class Channel:
    def __init__(self):
        self.data = {'/applications/muted_applications': ['private-app']}
        self.writes = []

    def __getattr__(self, name):
        if name.startswith('get_'):
            return lambda key, default: self.data.get(key, default)
        if name.startswith('set_'):
            def write(key, value):
                self.writes.append((name, key, value)); self.data[key] = value
                return True
            return write
        raise AttributeError(name)


class NotificationSettings(unittest.TestCase):
    def setUp(self):
        self.channel = Channel(); self.settings = notifications.Settings(self.channel)

    def test_reading_settings_has_no_writes(self):
        for key in notifications.SETTINGS:
            self.settings.read(key)
        self.assertEqual(self.channel.writes, [])

    def test_native_boolean_and_integer_types_are_used(self):
        self.settings.write('do-not-disturb', True)
        self.settings.write('log-max-size', 100)
        self.assertIn(('set_bool', '/do-not-disturb', True), self.channel.writes)
        self.assertIn(('set_uint', '/log-max-size', 100), self.channel.writes)
        self.assertEqual(self.channel.data['/applications/muted_applications'], ['private-app'])

    def test_logging_is_bounded_before_it_is_enabled(self):
        self.settings.write('notification-log', True)
        self.assertEqual(self.channel.writes[0], ('set_bool', '/log-max-size-enabled', True))
        self.assertEqual(self.channel.writes[1], ('set_bool', '/notification-log', True))

    def test_disabling_logging_does_not_delete_history_or_change_focus_mode(self):
        self.settings.write('notification-log', False)
        self.assertEqual(self.channel.writes, [('set_bool', '/notification-log', False)])

    def test_invalid_values_cannot_reach_xfconf(self):
        for key, value in [('do-not-disturb', 1), ('expire-timeout', True), ('expire-timeout', 0),
                           ('log-max-size', -1), ('notify-location', 'unknown')]:
            with self.assertRaises(ValueError):
                self.settings.write(key, value)
        self.assertEqual(self.channel.writes, [])

    def test_failed_writes_are_reported(self):
        self.channel.set_bool = lambda *_: False
        with self.assertRaises(RuntimeError):
            self.settings.write('do-not-disturb', True)
