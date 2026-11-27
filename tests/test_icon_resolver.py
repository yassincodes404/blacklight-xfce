"""Run the actual C desktop resolver against isolated launcher metadata."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class NativeIconResolver(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('cc') or not shutil.which('pkg-config'):
            raise unittest.SkipTest('Native compiler and GIO headers required')
        flags=subprocess.run(['pkg-config','--cflags','--libs','gio-unix-2.0'],capture_output=True,text=True)
        if flags.returncode:raise unittest.SkipTest('GIO development headers required')
        cls.build=tempfile.TemporaryDirectory();cls.binary=Path(cls.build.name)/'resolve'
        subprocess.run(['cc','-Wno-deprecated-declarations',str(ROOT/'packaging/windowing/test-resolver.c'),'-o',str(cls.binary),*flags.stdout.split()],check=True)

    @classmethod
    def tearDownClass(cls):cls.build.cleanup()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name);self.apps=self.home/'data/applications';self.apps.mkdir(parents=True)
        self.env={**os.environ,'HOME':str(self.home),'XDG_DATA_HOME':str(self.home/'data'),'XDG_DATA_DIRS':str(self.home/'empty'),'XDG_CONFIG_HOME':str(self.home/'config')}

    def entry(self,name,wmclass=None):
        text='[Desktop Entry]\nType=Application\nName=Fixture\nExec=/bin/true\nIcon=fixture-icon\n'
        if wmclass:text+='StartupWMClass='+wmclass+'\n'
        (self.apps/(name+'.desktop')).write_text(text)

    def resolve(self,identity):
        return subprocess.check_output([str(self.binary),identity],env=self.env,text=True).strip()

    def test_exact_desktop_identity_retains_priority(self):
        self.entry('player');self.entry('other','player')
        self.assertEqual(self.resolve('player'),'player.desktop')

    def test_case_fallback_is_preserved(self):
        self.entry('player');self.assertEqual(self.resolve('Player'),'player.desktop')

    def test_explicit_window_class_resolves_unrelated_launcher_name(self):
        self.entry('player','org.vendor.LegacyMain')
        self.assertEqual(self.resolve('org.vendor.LegacyMain'),'player.desktop')

    def test_profile_suffix_resolves_only_an_installed_desktop(self):
        self.entry('player')
        self.assertEqual(self.resolve('player (/home/example/Profile)'),'player.desktop')
        self.assertEqual(self.resolve('missing (/home/example/Profile)'),'NONE')

    def test_ambiguous_window_class_is_not_guessed(self):
        self.entry('one','LegacyMain');self.entry('two','LegacyMain')
        self.assertEqual(self.resolve('LegacyMain'),'NONE')

    def test_nonpath_parentheses_are_not_stripped(self):
        self.entry('player')
        self.assertEqual(self.resolve('player (Unrelated Mode)'),'NONE')
