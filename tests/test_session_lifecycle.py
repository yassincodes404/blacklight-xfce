"""Session switching must clear stale activation state and stop display clients."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'home/.local/share/galinia'))
spec = importlib.util.spec_from_file_location('galinia_session', ROOT / 'home/.local/share/galinia/session.py')
session = importlib.util.module_from_spec(spec); spec.loader.exec_module(session)


class SessionLifecycle(unittest.TestCase):
    def test_x11_clears_old_wayland_environment_in_both_managers(self):
        with patch.object(session, 'run') as run:
            session.import_environment({'DISPLAY': ':1', 'XDG_SESSION_TYPE': 'x11'})
        calls = [c.args for c in run.call_args_list]
        self.assertTrue(any(c[:3] == ('systemctl', '--user', 'unset-environment') and 'WAYLAND_DISPLAY' in c for c in calls))
        self.assertTrue(any(c[0] == 'dbus-update-activation-environment' and 'WAYLAND_DISPLAY=' in c for c in calls))

    def test_wayland_starts_backend_before_portal_broker(self):
        with patch.object(session, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')) as run:
            session.start_services({'XDG_SESSION_TYPE': 'wayland'}, {'audio_enabled': True, 'monitor_enabled': True})
        calls = [c.args for c in run.call_args_list]
        backend = calls.index(('systemctl', '--user', 'start', 'xdg-desktop-portal-wlr.service'))
        broker = calls.index(('systemctl', '--user', 'start', 'xdg-desktop-portal.service'))
        self.assertLess(backend, broker)
        self.assertTrue(any('/general/LockCommand' in c for c in calls))

    def test_x11_does_not_start_wayland_backend_or_idle(self):
        with patch.object(session, 'run') as run:
            session.start_services({'XDG_SESSION_TYPE': 'x11'}, {'audio_enabled': False, 'monitor_enabled': False})
        calls = [c.args for c in run.call_args_list]
        self.assertNotIn(('systemctl', '--user', 'start', 'xdg-desktop-portal-wlr.service'), calls)
        self.assertIn(('systemctl', '--user', 'stop', 'galinia-wayland-idle.service'), calls)
        self.assertIn(('systemctl', '--user', 'stop', 'galinia-audio.service'), calls)

    def test_custom_lock_command_is_not_silently_replaced(self):
        def result(*args, **kwargs):
            text = 'custom-locker\n' if '/general/LockCommand' in args else ''
            return subprocess.CompletedProcess(args, 0, text, '')
        with patch.object(session, 'run', side_effect=result) as run:
            with self.assertRaisesRegex(RuntimeError, 'Custom XFCE'):
                session.start_services({'XDG_SESSION_TYPE': 'wayland'}, {'audio_enabled': True, 'monitor_enabled': True})
        self.assertFalse(any('--set' in c.args for c in run.call_args_list))

    def test_session_exit_stops_target_even_after_startup_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            child = subprocess.Popen([sys.executable, '-c', 'pass'])
            try:
                with patch.dict(os.environ, {'XDG_RUNTIME_DIR': tmp}), patch.object(sys, 'argv', ['session']), \
                     patch.object(session, 'session_pid', return_value=child.pid), \
                     patch.object(session, 'start_services', side_effect=RuntimeError('missing provider')), \
                     patch.object(session, 'systemctl') as systemctl, patch.object(session.signal, 'signal'):
                    session.main()
                systemctl.assert_called_once_with('stop', 'galinia-session.target', check=False)
            finally:
                child.wait(timeout=5)

    def test_flameshot_autostart_skips_wayland(self):
        result = subprocess.run([str(ROOT / 'home/.local/bin/galinia-flameshot-autostart')],
                                env={**os.environ, 'XDG_SESSION_TYPE': 'wayland'}, capture_output=True)
        self.assertEqual(result.returncode, 0)

    def test_lock_uses_native_provider_and_waits_for_lock_acknowledgement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stub = root / 'swaylock'; stub.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n'); stub.chmod(0o755)
            result = subprocess.check_output([str(ROOT / 'home/.local/bin/galinia-lock')],
                    env={**os.environ, 'PATH': str(root)+':'+os.environ['PATH'], 'XDG_SESSION_TYPE': 'wayland'}, text=True)
            self.assertIn('--daemonize', result.splitlines())
            self.assertNotIn('xflock4', result)

    def test_adoption_does_not_restart_existing_apps_or_portals(self):
        with patch.object(session, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')) as run:
            session.start_services({'XDG_SESSION_TYPE': 'wayland'}, {'audio_enabled': True, 'monitor_enabled': True}, adopt=True)
        calls = [c.args for c in run.call_args_list]
        self.assertFalse(any(c[:3] == ('systemctl', '--user', 'restart') for c in calls))
        self.assertFalse(any(c[:3] == ('systemctl', '--user', 'stop') for c in calls))
