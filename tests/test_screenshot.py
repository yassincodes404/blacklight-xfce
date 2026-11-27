"""Exercise capture routing and failures with fake backends, without capturing a desktop."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import ast
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class ScreenshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.pictures = self.root / 'Pictures with spaces'
        self.script = self.bin / 'galinia-screenshot'
        shutil.copy2(ROOT / 'home/.local/bin/galinia-screenshot', self.script)
        self.env = {**os.environ, 'PATH': str(self.bin) + ':' + os.environ['PATH'],
                    'XDG_SESSION_TYPE': 'x11', 'WAYLAND_DISPLAY': '',
                    'TEST_PICTURES': str(self.pictures), 'TEST_LOG': str(self.root / 'calls.json')}
        self.stub('xdg-user-dir', 'import os\nprint(os.environ["TEST_PICTURES"])\n')
        self.stub('notify-send', 'raise SystemExit(1)\n')
        self.stub('xfce4-screenshooter', '''import json,os,sys
from pathlib import Path
Path(os.environ['TEST_LOG']).write_text(json.dumps(sys.argv[1:]))
if os.environ.get('TEST_CANCEL'): raise SystemExit(0)
if os.environ.get('TEST_FAIL'): raise SystemExit(1)
Path(sys.argv[sys.argv.index('--save')+1]).write_text('fake PNG')
''')
        helper = self.root / 'share/galinia/screenshot-clipboard.py'
        helper.parent.mkdir(parents=True)
        helper.write_text('import os,sys\nfrom pathlib import Path\nPath(os.environ["TEST_LOG"]+".clipboard").write_text(Path(sys.argv[1]).read_text())\n')
        (helper.parent / 'screenshot-region.py').write_text('''import os,sys,json
from pathlib import Path
Path(os.environ['TEST_LOG']).write_text(json.dumps(sys.argv[1:]))
if os.environ.get('TEST_CANCEL'): raise SystemExit(0)
if os.environ.get('TEST_FAIL'): raise SystemExit(1)
Path(sys.argv[1]).write_text('fake PNG')
''')
        self.stub('slurp', 'import os\nprint("" if os.environ.get("TEST_CANCEL") else "10,20 300x200")\n')
        self.stub('grim', '''import os,sys
from pathlib import Path
if os.environ.get('TEST_FAIL'): raise SystemExit(1)
Path(sys.argv[-1]).write_text('fake PNG')
''')
        self.stub('wl-copy', '''import os,sys
from pathlib import Path
if os.environ.get('TEST_CLIPBOARD_FAIL'): raise SystemExit(1)
Path(os.environ['TEST_LOG']+'.clipboard').write_text(sys.stdin.read())
''')

    def stub(self, name, code):
        path = self.bin / name
        path.write_text('#!/usr/bin/python3\n' + code)
        path.chmod(0o755)

    def capture(self, **env):
        return subprocess.run(['sh', str(self.script)], env={**self.env, **env},
                              capture_output=True, text=True, timeout=5)

    def captures(self):
        return list(self.pictures.glob('Screenshots/*.png'))

    def test_x11_saves_and_copies_without_using_broken_flameshot_wrapper(self):
        self.stub('flameshot', 'raise SystemExit("Should not use Flameshot")\n')
        result = self.capture()
        self.assertEqual(result.returncode, 0, result.stderr)
        arguments = json.loads((self.root / 'calls.json').read_text())
        self.assertEqual(arguments, [str(self.captures()[0])])
        self.assertEqual(len(self.captures()), 1)
        self.assertEqual((self.root / 'calls.json.clipboard').read_text(), 'fake PNG')

    def test_x11_escape_does_not_publish_an_empty_file_or_change_clipboard(self):
        result = self.capture(TEST_CANCEL='1')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.captures())
        self.assertFalse((self.root / 'calls.json.clipboard').exists())

    def test_x11_capture_failure_cleans_up_placeholder(self):
        result = self.capture(TEST_FAIL='1')
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.captures())

    def test_wayland_saves_and_copies(self):
        result = self.capture(XDG_SESSION_TYPE='wayland')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.captures()), 1)
        self.assertEqual((self.root / 'calls.json.clipboard').read_text(), 'fake PNG')

    def test_wayland_cancel_does_not_create_a_capture(self):
        result = self.capture(XDG_SESSION_TYPE='wayland', TEST_CANCEL='1')
        self.assertEqual(result.returncode, 0)
        self.assertFalse(self.captures())

    def test_wayland_clipboard_failure_retains_the_saved_image(self):
        result = self.capture(XDG_SESSION_TYPE='wayland', TEST_CLIPBOARD_FAIL='1')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(len(self.captures()), 1)

    def test_wayland_capture_failure_cleans_up(self):
        result = self.capture(XDG_SESSION_TYPE='wayland', TEST_FAIL='1')
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.captures())

    def test_shortcuts_match_sessions_and_keep_ctrl_s_available_to_apps(self):
        xfce = ET.parse(ROOT / 'home/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-keyboard-shortcuts.xml')
        commands = {n.get('name'): n.get('value') for n in xfce.findall("./property[@name='commands']/property[@name='custom']/property")}
        self.assertIn('galinia-screenshot', commands['Print'])
        self.assertEqual(commands['Print'], commands['<Super><Shift>s'])
        self.assertNotIn('<Primary>s', commands)
        labwc = ET.parse(ROOT / 'home/.config/xfce4/labwc/rc.xml')
        binds = {n.get('key'): n.find('action').get('command') for n in labwc.findall('./keyboard/keybind')}
        self.assertEqual(binds['Print'], binds['W-S-s'])


class RegionGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = ast.parse((ROOT / 'home/.local/share/galinia/screenshot-region.py').read_text())
        helper = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == 'crop_rectangle')
        namespace = {}
        exec(compile(ast.Module(body=[helper], type_ignores=[]), 'crop-geometry', 'exec'), namespace)
        cls.crop = staticmethod(namespace['crop_rectangle'])

    def test_reverse_drag_and_clamping_at_screen_edges(self):
        self.assertEqual(self.crop((90, 70), (-10, -20), (100, 80), (100, 80)), (0, 0, 90, 70))
        self.assertEqual(self.crop((10, 20), (300, 400), (100, 80), (100, 80)), (10, 20, 90, 60))

    def test_hidpi_crop_uses_original_pixels(self):
        self.assertEqual(self.crop((10, 20), (60, 50), (100, 80), (200, 160)), (20, 40, 100, 60))

    def test_click_without_drag_has_no_capture_area(self):
        self.assertEqual(self.crop((10, 20), (10, 20), (100, 80), (100, 80)), (10, 20, 0, 0))


if __name__ == '__main__':
    unittest.main()
