"""Regression for the no-persistence requirement."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from isg_privacy import cleanup_legacy_state, legacy_paths


class NoPersistenceTests(unittest.TestCase):
    def test_no_prefs_or_history_writer(self):
        import isg_privacy
        self.assertFalse(hasattr(isg_privacy, 'save_settings'))
        self.assertFalse(hasattr(isg_privacy, 'append_history'))
        self.assertFalse(hasattr(isg_privacy, 'load_history'))

    def test_cleanup_legacy_only(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(os.environ,
             {'XDG_CONFIG_HOME': td+'/cfg', 'XDG_STATE_HOME': td+'/state'}):
            settings, history = legacy_paths()
            for filename in [settings, history]:
                filename.parent.mkdir(parents=True, exist_ok=True)
                filename.write_text('test')
            other = settings.parent / 'user_keep.txt'
            other.write_text('keep')
            cleanup_legacy_state()
            self.assertFalse(settings.exists())
            self.assertFalse(history.exists())
            self.assertEqual(other.read_text(), 'keep')
