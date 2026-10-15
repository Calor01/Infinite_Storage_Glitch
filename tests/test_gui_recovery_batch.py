"""Integración real de la recuperación por lotes desde interfaz bajo Xvfb."""
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from isg_core import encode
from isg_gui import App


def main():
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        videos = base / 'videos'; videos.mkdir()
        restored = base / 'restored'; restored.mkdir()
        originals = []
        for index in range(2):
            src = base / f'test{index}.dat'
            src.write_bytes(bytes(range(32)) * (index + 2))
            video = videos / f'video{index}.mp4'
            encode(str(src), str(video), block=16, copies=1)
            originals.append((src, video))
        errors = []
        env = patch.dict(os.environ, {'XDG_CONFIG_HOME': str(base/'config'),
                                     'XDG_STATE_HOME': str(base/'state')})
        with env, patch('isg_gui.messagebox.showinfo'), \
             patch('isg_gui.messagebox.showwarning'), \
             patch('isg_gui.messagebox.showerror', side_effect=lambda _t, msg: errors.append(msg)):
            app = App()
            try:
                app.decode_batch_files = [str(video) for _src, video in originals]
                app._decode_batch_refresh()
                app.decode_batch_folder.set(str(restored))
                app.tabs.select(2)
                app._start_decode_batch()
                limit = time.monotonic() + 60
                while app.running and time.monotonic() < limit:
                    app.update()
                    time.sleep(0.03)
                app.update()
                assert not app.running, 'No terminó el lote de recuperación'
                assert not errors, errors
                assert app.progress_value.get() == 0
                assert app.decode_batch_folder.get() == ""
                assert app.decode_batch_files == []
            finally:
                app.destroy()
        for src, _video in originals:
            assert (restored/src.name).read_bytes() == src.read_bytes()
    print('PASS: dos archivos recuperados y comprobados desde la cola gráfica.')


if __name__ == '__main__':
    main()
