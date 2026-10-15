"""Integration: default output alongside input and a round-trip with no persistent files."""
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from isg_gui import App
from isg_privacy import legacy_paths


def until_finished(app, timeout=35):
    limit = time.monotonic() + timeout
    while app.running and time.monotonic() < limit:
        app.update()
        time.sleep(.03)
    app.update()
    assert not app.running, 'Operation timed out'


def main():
    with tempfile.TemporaryDirectory() as td, \
         patch.dict(os.environ, {'XDG_CONFIG_HOME': td+'/config', 'XDG_STATE_HOME': td+'/state'}), \
         patch('isg_gui.messagebox.showinfo'), patch('isg_gui.messagebox.showerror') as errors:
        base = Path(td)
        folder = base/'source files'; folder.mkdir()
        source = folder/'té con leche.dat'
        payload = bytes(range(101)) * 3
        source.write_bytes(payload)
        app = App()
        try:
            app.source_file.set(str(source))
            auto_video = source.with_name(source.name+'.mp4')
            assert app.video_dest.get() == str(auto_video)
            app._start_encode()
            until_finished(app)
            assert auto_video.is_file()
            # Avoid intentional collision: the recovered file's original name still exists.
            source.rename(folder/'renamed-copy.dat')
            app.restore_video.set(str(auto_video))
            assert app.restore_folder.get() == str(folder)
            app._start_decode()
            until_finished(app)
            assert source.read_bytes() == payload
            assert not errors.called, errors.call_args_list
            assert all(not path.exists() for path in legacy_paths())
        finally:
            app.destroy()
    print('PASS: salida predeterminada junto al origen, recuperación SHA-256 sin historial')

if __name__ == '__main__':
    main()
