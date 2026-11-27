"""Check native/local Flameshot routing without launching a capture UI."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FlameshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.native = self.root / 'system/flameshot'
        self.local = self.root / 'local'
        self.wrapper = self.root / 'flameshot'
        source = (ROOT / 'home/.local/bin/flameshot').read_text()
        source = source.replace('/usr/bin/flameshot', str(self.native))
        source = source.replace('$HOME/.local/opt/flameshot', str(self.local))
        self.wrapper.write_text(source)
        self.wrapper.chmod(0o755)
        self.log = self.root / 'log.json'
        self.env = {**os.environ, 'TEST_LOG': str(self.log)}

    def provider(self, path, label):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('#!/usr/bin/python3\nimport os,sys,json\nfrom pathlib import Path\n'
                        + 'Path(os.environ["TEST_LOG"]).write_text(json.dumps({"provider":' + repr(label)
                        + ',"arguments":sys.argv[1:],"extract":os.environ.get("APPIMAGE_EXTRACT_AND_RUN")}))\n')
        path.chmod(0o755)

    def test_distribution_package_takes_priority(self):
        self.provider(self.native, 'native')
        self.provider(self.local / 'extracted/AppRun', 'extracted')
        subprocess.run([str(self.wrapper), 'gui', '--clipboard'], env=self.env, check=True)
        report = json.loads(self.log.read_text())
        self.assertEqual(report['provider'], 'native')
        self.assertEqual(report['arguments'], ['gui', '--clipboard'])

    def test_extracted_app_runs_without_fuse(self):
        self.provider(self.local / 'extracted/AppRun', 'extracted')
        subprocess.run([str(self.wrapper), '--version'], env=self.env, check=True)
        self.assertEqual(json.loads(self.log.read_text())['provider'], 'extracted')

    def test_appimage_fallback_explicitly_avoids_fuse(self):
        self.provider(self.local / 'Flameshot.AppImage', 'appimage')
        subprocess.run([str(self.wrapper), 'gui'], env=self.env, check=True)
        self.assertEqual(json.loads(self.log.read_text())['extract'], '1')

    def test_missing_provider_fails_with_actionable_message(self):
        # No notification backend is required for a readable failure.
        result = subprocess.run([str(self.wrapper)], env={**self.env, 'PATH': '/nonexistent'}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('install the flameshot package', result.stderr)

    def test_x11_screenshot_shortcut_forwards_to_flameshot_with_clipboard_enabled(self):
        self.env["XDG_SESSION_TYPE"] = "x11"
        self.provider(self.wrapper, 'shortcut')
        shortcut = self.root / 'galinia-screenshot'
        shortcut.write_text((ROOT / 'home/.local/bin/galinia-screenshot').read_text())
        shortcut.chmod(0o755)
        subprocess.run([str(shortcut)], env=self.env, check=True)
        self.assertEqual(json.loads(self.log.read_text())['arguments'], ['gui', '--clipboard'])
