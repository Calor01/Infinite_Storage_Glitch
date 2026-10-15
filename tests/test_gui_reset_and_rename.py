"""End-to-end GUI reset (success, failure, batch) and renamed-video recovery."""
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from isg_gui import App
from isg_privacy import DEFAULTS


def finished(app, timeout=40):
    end = time.monotonic() + timeout
    while app.running and time.monotonic() < end:
        app.update()
        time.sleep(.02)
    app.update()
    assert not app.running, 'Timeout'


def empty_and_defaults(app):
    assert app.resolution.get() == DEFAULTS['resolution']
    assert app.block_size.get() == DEFAULTS['block_size']
    assert app.redundancy.get() == DEFAULTS['redundancy']
    for value in (app.source_file, app.video_dest, app.restore_video,
                  app.restore_folder, app.batch_folder, app.decode_batch_folder):
        assert value.get() == '', (str(value), value.get())
    assert app.batch_files == [] and app.decode_batch_files == []
    assert app.progress_value.get() == 0 and app.percent.get() == '0 %'
    assert app.status.get() == 'Preparado.'


def test_workflow():
    with tempfile.TemporaryDirectory() as td, \
         patch.dict(os.environ, {'XDG_CONFIG_HOME': td+'/config', 'XDG_STATE_HOME': td+'/state'}), \
         patch('isg_gui.messagebox.showinfo'), patch('isg_gui.messagebox.showerror') as errors:
        p = Path(td)
        source = p/'datos privados y ü.txt'
        source.write_bytes(bytes(range(100))*9)
        app = App()
        try:
            assert app.tabs.index('end') == 4
            assert [app.tabs.tab(i, 'text') for i in app.tabs.tabs()] == ['Crear', 'Recuperar', 'Lotes', 'Información']
            assert not any(hasattr(app, key) for key in ('open_folder', 'diagnostics', 'last_output', 'history', 'log'))
            app.source_file.set(str(source))
            video = Path(app.video_dest.get())
            app.resolution.set('1920x1080'); app.block_size.set('16'); app.redundancy.set('3')
            app._start_encode()
            finished(app)
            assert video.is_file() and video.stat().st_size
            empty_and_defaults(app)
            assert not errors.called, errors.call_args_list
            # The original name must be restored from the payload, not from the MP4 name.
            renamed = p/'sin-relacion-con-el-original.mp4'
            video.rename(renamed)
            restored = p/'recuperados'; restored.mkdir()
            app.restore_video.set(str(renamed))
            app.restore_folder.set(str(restored))
            app._start_decode()
            finished(app)
            assert (restored/source.name).read_bytes() == source.read_bytes()
            empty_and_defaults(app)
            # Failure must also reset any potentially sensitive filenames/parameters.
            app.source_file.set(str(p/'no-existe'))
            app.resolution.set('1920x1080')
            app._start_encode()
            finished(app)
            assert errors.called
            empty_and_defaults(app)
            errors.reset_mock()
            # User cancellation also discards active session data.
            app.source_file.set(str(source))
            app.block_size.set('16')
            def abort(_callback):
                raise ValueError('Operación cancelada.')
            app._start_task('Cancelando…', abort, 'encode')
            finished(app)
            empty_and_defaults(app)
            # With a fresh selection, the default output is calculated again.
            other = p/'otro.dat'; other.write_bytes(b'abc')
            app.source_file.set(str(other))
            assert app.video_dest.get() == str(other) + '.mp4'
            app.source_file.set(''); app.video_dest.set('')
            app.batch_files = [str(other)]; app._batch_refresh()
            app.resolution.set('1920x1080')
            app._start_batch(); finished(app)
            assert (p/'otro.dat.mp4').exists()
            empty_and_defaults(app)
        finally:
            app.destroy()
    print('PASS: reinicio automático tras éxito/error/lote y recuperación de MP4 renombrado')


if __name__ == '__main__':
    test_workflow()
