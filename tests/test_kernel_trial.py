import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('kernel_trial', Path(__file__).resolve().parents[1] / 'tools/kernel_trial.py')
trial = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(trial)


class KernelTrialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.journal = self.root / 'state/journal.json'
        initial = {'mglru': '0x0007', 'autogroup': '1', 'zswap_pool': '20', 'zswap': 'N'}
        for key, value in initial.items():
            path = self.root / trial.PATHS[key]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value)
        path = self.root / 'proc/sys/kernel/random/boot_id'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('boot-one')
        (self.root / 'proc/swaps').write_text('Filename Type Size Used Priority\n/swap.img file 1024 0 -1\n')

    def test_already_enabled_features_are_not_rewritten_and_trial_restores(self):
        record = trial.apply(self.root, self.journal)
        self.assertEqual(set(record['changes']), {'zswap'})
        self.assertEqual(self.journal.stat().st_mode & 0o777, 0o600)
        self.assertEqual(trial.state(self.root)['zswap'], 'Y')
        trial.restore(self.root, self.journal)
        self.assertEqual(trial.state(self.root)['zswap'], 'N')
        self.assertFalse(self.journal.exists())

    def test_no_swap_or_zram_refuses_before_writes(self):
        for swap in ['', '/dev/zram0 partition 1024 0 100\n']:
            (self.root / 'proc/swaps').write_text('header\n' + swap)
            with self.assertRaises(ValueError):
                trial.apply(self.root, self.journal)
            self.assertFalse(self.journal.exists())

    def test_existing_policy_and_recovery_journal_are_preserved(self):
        trial.apply(self.root, self.journal)
        before = self.journal.read_bytes()
        with self.assertRaises(ValueError):
            trial.apply(self.root, self.journal)
        self.assertEqual(before, self.journal.read_bytes())

    def test_write_failure_rolls_back(self):
        def fail(root, key, value):
            trial.write_setting(root, key, value)
            if value == 'Y':
                raise OSError('injected failure')
        with self.assertRaises(OSError):
            trial.apply(self.root, self.journal, fail)
        self.assertEqual(trial.state(self.root)['zswap'], 'N')
        self.assertFalse(self.journal.exists())

    def test_later_admin_change_is_not_overwritten(self):
        (self.root / trial.PATHS['zswap_pool']).write_text('10')
        trial.apply(self.root, self.journal)
        (self.root / trial.PATHS['zswap_pool']).write_text('15')
        with self.assertRaisesRegex(ValueError, 'Later administrator'):
            trial.restore(self.root, self.journal)
        self.assertEqual(trial.state(self.root)['zswap_pool'], '15')

    def test_reboot_invalidates_runtime_recovery(self):
        trial.apply(self.root, self.journal)
        (self.root / 'proc/sys/kernel/random/boot_id').write_text('boot-two')
        with self.assertRaisesRegex(ValueError, 'Different boot'):
            trial.restore(self.root, self.journal)
