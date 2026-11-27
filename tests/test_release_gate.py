import importlib.util
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('gate', Path(__file__).resolve().parents[1] / 'tools/release_gate.py')
gate = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(gate)


class ReleaseGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.iso = self.root / 'fixture.iso'; self.iso.write_bytes(b'fixture, not a bootable image')
        self.log = self.root / 'boot.log'; self.log.write_text('fixture evidence')
        self.policy = {'version': '0.1-alpha1', 'required_checks': ['boot', 'install']}
        self.report = {'version': '0.1-alpha1', 'source_commit': 'fixture', 'iso_sha256': gate.sha256(self.iso),
                       'checks': [{'id': name, 'status': 'pass', 'evidence': [{'path': 'boot.log', 'sha256': gate.sha256(self.log)}]} for name in ['boot','install']]}

    def evaluate(self):
        return gate.evaluate(self.policy, self.report, self.root, self.iso)

    def test_bound_complete_report(self):
        self.assertEqual(self.evaluate(), [])

    def test_missing_install_is_not_a_pass(self):
        self.report['checks'].pop()
        self.assertTrue(any('install' in e for e in self.evaluate()))

    def test_evidence_mutation_or_different_iso_blocks_release(self):
        self.log.write_text('changed')
        self.iso.write_bytes(b'another image')
        errors = self.evaluate()
        self.assertTrue(any('ISO' in e for e in errors))
        self.assertTrue(any('hash mismatch' in e for e in errors))

    def test_no_evidence_and_duplicate_claims_block_release(self):
        self.report['checks'][0]['evidence'] = []
        self.report['checks'].append(self.report['checks'][1])
        errors = self.evaluate()
        self.assertIn('duplicate test IDs', errors)
        self.assertTrue(any('evidence missing' in e for e in errors))

    def test_evidence_outside_report_is_rejected(self):
        self.report['checks'][0]['evidence'][0]['path'] = '../outside.log'
        self.assertTrue(any('outside' in e for e in self.evaluate()))
