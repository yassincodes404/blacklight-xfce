"""Welcome persistence checks without a display or GTK dependency in CI."""
import ast
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ast.parse((ROOT / 'home/.local/share/galinia/welcome.py').read_text())
STATE = next(n for n in SOURCE.body if isinstance(n, ast.FunctionDef) and n.name == 'state_file')
WELCOME = next(n for n in SOURCE.body if isinstance(n, ast.ClassDef) and n.name == 'Welcome')
COMPLETE = next(n for n in WELCOME.body if isinstance(n, ast.FunctionDef) and n.name == 'complete')


class WelcomeStateTests(unittest.TestCase):
    def helpers(self):
        namespace = {'os': os, 'Path': Path}
        exec(compile(ast.Module(body=[STATE, COMPLETE], type_ignores=[]), 'welcome-state', 'exec'), namespace)
        return namespace

    def test_completion_is_per_user_persistent_and_repeatable(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {'XDG_STATE_HOME': temp}):
            helpers = self.helpers()
            app = types.SimpleNamespace(quit=Mock(), notice=Mock())
            self.assertFalse(helpers['state_file']().exists())
            helpers['complete'](app, None)
            self.assertEqual(helpers['state_file']().read_text(), '1\n')
            helpers['complete'](app, None)
            self.assertEqual(app.quit.call_count, 2)
            app.notice.show.assert_not_called()

    def test_failed_completion_reports_error_and_keeps_window_open(self):
        with tempfile.TemporaryDirectory() as temp:
            blocker = Path(temp) / 'not-a-directory'
            blocker.write_text('keep')
            with patch.dict(os.environ, {'XDG_STATE_HOME': str(blocker)}):
                helpers = self.helpers()
                app = types.SimpleNamespace(quit=Mock(), notice=Mock())
                helpers['complete'](app, None)
                app.quit.assert_not_called()
                app.notice.show.assert_called_once()
                self.assertIn('Could not save', app.notice.set_text.call_args.args[0])
                self.assertEqual(blocker.read_text(), 'keep')


if __name__ == '__main__':
    unittest.main()
