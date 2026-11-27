"""Exercise fresh-account image seeding in disposable homes, without root."""
import importlib.machinery
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import control
import install

loader = importlib.machinery.SourceFileLoader('image_initializer', str(ROOT / 'packaging/galinia-defaults/initialize-home'))
spec = importlib.util.spec_from_loader(loader.name, loader)
initializer = importlib.util.module_from_spec(spec); loader.exec_module(initializer)


class ImageSeedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.home = self.base / 'fresh account'
        self.home.mkdir()
        self.payload = self.base / 'payload'
        profile = self.payload / 'home'
        (profile / '.config/blacklight-rice').mkdir(parents=True)
        (profile / '.config/mimeapps.list').write_text('[Default Applications]\nimage/png=galinia.desktop\n')
        (profile / '.xsessionrc').write_text('export GALINIA_HOME="@HOME@"\n')
        (profile / 'launcher.desktop').write_text('[Desktop Entry]\nExec="@HOME@/.local/bin/galinia-welcome"\n')
        (self.payload / 'config').mkdir()
        (self.payload / 'config/retired-files.json').write_text('[]\n')
        self.marker = self.home / '.config/galinia/initialize'
        self.marker.parent.mkdir(parents=True)

    def seed(self):
        with patch.object(control, 'ROOT', ROOT), patch.object(install, 'ROOT', ROOT):
            initializer.initialize(self.home, self.payload)

    def test_fresh_marked_account_resolves_its_home_and_initializes_only_once(self):
        self.marker.write_text('preview\n')
        self.seed()
        self.assertFalse(self.marker.exists())
        self.assertIn(str(self.home), (self.home / 'launcher.desktop').read_text())
        self.assertNotIn('@HOME@', (self.home / 'launcher.desktop').read_text())
        (self.home / 'launcher.desktop').write_text('later user customization')
        self.seed()
        self.assertEqual((self.home / 'launcher.desktop').read_text(), 'later user customization')

    def test_existing_unmarked_account_is_untouched(self):
        (self.home / '.xsessionrc').write_text('personal setup\n')
        self.seed()
        self.assertEqual((self.home / '.xsessionrc').read_text(), 'personal setup\n')
        self.assertFalse((self.home / 'launcher.desktop').exists())

    def test_failure_retains_marker_for_visible_recovery(self):
        self.marker.write_text('preview\n')
        with patch.object(install, 'install_transaction', side_effect=OSError('disk failure')):
            with self.assertRaisesRegex(OSError, 'disk failure'):
                self.seed()
        self.assertTrue(self.marker.exists())

    def test_navigation_reference_is_bound_in_both_sessions(self):
        xfce = ET.parse(ROOT / 'home/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-keyboard-shortcuts.xml')
        values = {n.get('name'): n.get('value') for n in xfce.findall("./property[@name='commands']/property[@name='custom']/property")}
        self.assertIn('galinia-shortcuts', values['<Super>slash'])
        labwc = ET.parse(ROOT / 'home/.config/xfce4/labwc/rc.xml')
        bindings = {n.get('key'): n.find('action').get('command') for n in labwc.findall('./keyboard/keybind')}
        self.assertIn('galinia-shortcuts', bindings['W-slash'])
        self.assertNotIn('W-a', bindings)


if __name__ == '__main__':
    unittest.main()
