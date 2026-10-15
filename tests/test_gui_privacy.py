"""No logs, no preferences persisted on window use, only removal of legacy files."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from isg_gui import App
from isg_privacy import legacy_paths


def test_gui_privacy():
    with tempfile.TemporaryDirectory() as folder:
        with patch.dict(os.environ, {'XDG_CONFIG_HOME': folder + '/config',
                                     'XDG_STATE_HOME': folder + '/state'}):
            a, b = legacy_paths()
            for p in (a, b):
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text('historical data')
            app = App()
            try:
                app.update()
                app.resolution.set('1920x1080')
                app.batch_folder.set('/tmp/sample')
                assert not hasattr(app, 'history')
                assert not hasattr(app, 'log')
                assert not hasattr(app, '_save_log')
                assert not hasattr(app, '_record_history')
                assert 'Historial' not in [app.tabs.tab(i, 'text') for i in app.tabs.tabs()]
                assert not hasattr(app, '_start_download')
                assert not hasattr(app, '_diagnose')
                assert not hasattr(app, 'open_folder')
                assert [app.tabs.tab(i, 'text') for i in app.tabs.tabs()] == ['Crear', 'Recuperar', 'Lotes', 'Información']
            finally:
                app.destroy()
            assert not a.exists() and not b.exists()
    print('PASS: interfaz sin persistencia, sin registro ni descargador')

if __name__ == '__main__':
    test_gui_privacy()
