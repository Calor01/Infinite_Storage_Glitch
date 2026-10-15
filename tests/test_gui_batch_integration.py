"""Integración real de cola gráfica: xvfb-run -a python3 tests/test_gui_batch_integration.py."""
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from isg_gui import App
from isg_core import decode


def main():
    with tempfile.TemporaryDirectory() as directory:
        p = Path(directory)
        env = patch.dict(os.environ, {'XDG_CONFIG_HOME': str(p/'config'),
                                    'XDG_STATE_HOME': str(p/'state')})
        with env:
            inputs = [p/'a.bin', p/'b.bin']
            for i, f in enumerate(inputs):
                f.write_bytes(bytes(range(240))*(i+3))
            destination = p/'videos'; destination.mkdir()
            errors = []
            with patch('isg_gui.messagebox.showinfo'), patch('isg_gui.messagebox.showerror',
                                                            side_effect=lambda _title, msg: errors.append(msg)):
                app = App()
                try:
                    app.batch_files = list(map(str, inputs))
                    app._batch_refresh()
                    app.batch_folder.set(str(destination))
                    app.tabs.select(2)
                    app._start_batch()
                    timeout = time.monotonic() + 40
                    while app.running and time.monotonic() < timeout:
                        app.update()
                        time.sleep(0.05)
                    app.update()
                    assert not app.running, 'Lote no finalizado'
                    assert not errors, errors
                    assert app.batch_folder.get() == ""
                    assert app.batch_files == []
                    assert app.progress_value.get() == 0
                finally:
                    app._on_close()
            recovered = p/'recovered'; recovered.mkdir()
            for file in inputs:
                output = decode(str(destination/(file.name+'.mp4')), str(recovered))
                assert output.read_bytes() == file.read_bytes()
            app = App()
            try:
                assert app.batch_folder.get() == ''
            finally:
                app.destroy()
    print('PASS: dos MP4 creados desde la interfaz, recuperados sin registro persistente.')


if __name__ == '__main__':
    main()
