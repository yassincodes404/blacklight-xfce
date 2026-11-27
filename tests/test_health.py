"""Readiness must distinguish on-demand services, failures and duplicate agents."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
spec = importlib.util.spec_from_file_location('galinia_health', ROOT / 'tools/health.py')
health = importlib.util.module_from_spec(spec); spec.loader.exec_module(health)


class HealthTests(unittest.TestCase):
    def test_on_demand_inactivity_is_not_reported_as_a_failure(self):
        state = {'LoadState': 'loaded', 'ActiveState': 'inactive'}
        self.assertEqual(health.service_result('portal', state, demand=True)['status'], 'info')
        self.assertEqual(health.service_result('audio', state)['status'], 'warn')

    def test_masked_and_failed_services_are_not_reported_healthy(self):
        for state in [{'LoadState': 'masked', 'ActiveState': 'inactive'},
                      {'LoadState': 'loaded', 'ActiveState': 'failed'}]:
            self.assertEqual(health.service_result('portal', state, demand=True)['status'], 'warn')

    def test_multiple_agents_are_visible_instead_of_silently_killed(self):
        names = ['agent-a', 'agent-b']
        self.assertEqual(health.process_check('auth', names, ['agent-a'])['status'], 'ok')
        self.assertEqual(health.process_check('auth', names, names)['status'], 'warn')

    def test_unavailable_user_bus_is_reported_without_crashing(self):
        with patch.object(health.subprocess, 'run', return_value=types.SimpleNamespace(returncode=1)):
            self.assertEqual(health.unit_state('pipewire.service', user=True), {})

    def test_missing_wayland_locker_is_visible(self):
        result = health.wayland_lock_result({'swaylock': False, 'swayidle': True}, True, False)
        self.assertEqual(result['status'], 'warn')
        self.assertIn('swaylock', result['detail'])

    def test_ready_locker_does_not_claim_authentication_was_tested(self):
        result = health.wayland_lock_result({'swaylock': True}, True, True)
        self.assertEqual(result['status'], 'info')
        self.assertIn('real password test', result['detail'])

    def test_portal_active_with_zero_sources_is_not_healthy(self):
        for value in ['u 0', '', 'bad response']:
            self.assertEqual(health.portal_capture_result(value)['status'], 'warn')
        self.assertEqual(health.portal_capture_result('u 1')['status'], 'info')
