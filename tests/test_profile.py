"""Portability and failure-path checks; never changes the live desktop."""
import ast
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('control',ROOT/'tools/control.py')
control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)

class ProfileTests(unittest.TestCase):
    def test_render_for_different_user_preserves_syntax_and_aliases(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'staged'
            target=Path('/home/developer & design')
            control.render(types.SimpleNamespace(output=out,target_home=target,wallpaper=None,monitor=None))
            for p in out.rglob('*'):
                if p.is_symlink():
                    self.assertTrue(p.exists(),str(p));continue
                if not p.is_file():continue
                if p.suffix=='.xml':ET.parse(p)
                elif p.suffix=='.json':json.loads(p.read_text())
                elif p.suffix=='.py':ast.parse(p.read_text())
            shortcuts=ET.parse(out/'.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-keyboard-shortcuts.xml')
            commands=shortcuts.findall("./property[@name='commands']/property[@name='custom']/property")
            command=next(n.get('value') for n in commands if n.get('name')=='<Super>s')
            self.assertEqual(command,'"/home/developer & design/.local/bin/galinia-settings"')
            self.assertEqual((out/'.config/blacklight-rice/wallpaper').read_text().strip(),str(target/'.local/share/backgrounds/Galinia/galinia-dusk.png'))
            desktop=ET.parse(out/'.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml')
            self.assertFalse(any(n.get('name','').startswith('monitor') for n in desktop.iter('property')))
            self.assertTrue((out/'.local/share/backgrounds/Galinia/galinia-dusk.png').is_file())

    def test_refuses_nonempty_stage_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);sentinel=out/'keep';sentinel.write_text('unchanged')
            with self.assertRaises(SystemExit):control.fresh(out)
            self.assertEqual(sentinel.read_text(),'unchanged')
            self.assertEqual(list(out.iterdir()),[sentinel])

    def test_startup_continues_after_first_service_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);log=directory/'calls';stub=directory/'systemctl'
            stub.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$CALL_LOG"\ncase "$*" in *"restart sysmon-widget.service"*) exit 1;; esac\nexit 0\n')
            stub.chmod(0o755)
            env={**os.environ,'PATH':str(directory)+':'+os.environ['PATH'],'CALL_LOG':str(log)}
            activation=directory/'dbus-update-activation-environment'
            activation.write_text('#!/bin/sh\nexit 0\n');activation.chmod(0o755)
            env['XDG_SESSION_TYPE']='x11'
            result=subprocess.run(['sh',str(ROOT/'home/.local/bin/galinia-session'),'--once'],env=env,capture_output=True,text=True,timeout=5)
            self.assertEqual(result.returncode,1)
            calls=log.read_text()
            self.assertIn('restart blacklight-wallpaper-sync.service',calls)
            self.assertIn('restart galinia-search.service',calls)
            self.assertIn('failed to start sysmon-widget.service',result.stderr)

    def test_atomic_write_replaces_complete_file_and_cleans_failed_temp(self):
        # Extract the pure helper to avoid needing a graphical session in CI.
        source=ast.parse((ROOT/'home/.local/bin/blacklight-wallpaper-sync.py').read_text())
        fn=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='atomic_write')
        ns={'os':os,'tempfile':tempfile};exec(compile(ast.Module(body=[fn],type_ignores=[]),'atomic_write','exec'),ns)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'palette';ns['atomic_write'](p,'original')
            with patch.object(os,'replace',side_effect=OSError('test failure')):
                with self.assertRaises(OSError):ns['atomic_write'](p,'partial')
            self.assertEqual(p.read_text(),'original')
            self.assertEqual(list(Path(tmp).iterdir()),[p])
            ns['atomic_write'](p,'complete');self.assertEqual(p.read_text(),'complete')

    def test_manifest_rejects_duplicate_wm_actions(self):
        tree=ET.parse(ROOT/'home/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-keyboard-shortcuts.xml')
        nodes=tree.findall("./property[@name='xfwm4']/property[@name='custom']/property")
        actions=[n.get('value') for n in nodes if n.get('value','').endswith('_key')]
        self.assertEqual(len(actions),len(set(actions)))

if __name__=='__main__':unittest.main()
