"""Check session routing and cancellation without accessing the desktop or clipboard."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CaptureRouting(unittest.TestCase):
    def test_capture_uses_the_session_backend(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            shutil.copy2(ROOT/'home/.local/bin/galinia-screenshot',root/'galinia-screenshot')
            for name in ['flameshot','galinia-wayland-screenshot']:
                script=root/name;script.write_text('#!/bin/sh\nprintf "%s " "'+name+'" "$@"\n');script.chmod(0o755)
            for session,expected in [('wayland','galinia-wayland-screenshot'),('x11','flameshot gui --clipboard')]:
                result=subprocess.check_output([str(root/'galinia-screenshot')],env={**os.environ,'XDG_SESSION_TYPE':session},text=True)
                self.assertEqual(result.strip(),expected)

    def test_cancelled_selection_does_not_capture_or_touch_clipboard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);binary=root/'.local/bin';binary.mkdir(parents=True)
            for name in ['grim','wl-copy','slurp']:
                script=binary/name
                script.write_text('#!/bin/sh\nexit 1\n' if name=='slurp' else '#!/bin/sh\necho unexpected >> "$HOME/called"\n')
                script.chmod(0o755)
            subprocess.run(['sh',str(ROOT/'home/.local/bin/galinia-wayland-screenshot')],env={**os.environ,'HOME':str(root)},check=True)
            self.assertFalse((root/'called').exists())
            self.assertFalse((root/'Pictures').exists())
