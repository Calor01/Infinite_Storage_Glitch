"""Drag-and-drop handling with Tk Tcl lists and same-directory destinations."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from isg_gui import App


def main():
    with tempfile.TemporaryDirectory() as td, patch('isg_gui.messagebox.showwarning') as warn:
        root = Path(td)
        one = root/'archivo con espacios.txt'; one.write_text('content')
        two = root/'vídeo con acentos.mp4'; two.write_bytes(b'not a valid MP4')
        app = App()
        try:
            assert app._handle_drop('create', app.tk.call('list', str(one))) == 'copy'
            assert app.source_file.get() == str(one)
            assert app.video_dest.get() == str(one)+'.mp4'
            assert app._handle_drop('restore', app.tk.call('list', str(two))) == 'copy'
            assert app.restore_video.get() == str(two)
            assert app.restore_folder.get() == str(root)
            assert app._handle_drop('batch', app.tk.call('list', str(one), str(two))) == 'copy'
            assert len(app.batch_files) == 2
            assert app._handle_drop('batch', app.tk.call('list', str(one))) == 'copy'
            assert len(app.batch_files) == 2
            assert app._handle_drop('batch_decode', app.tk.call('list', str(two))) == 'copy'
            assert app.decode_batch_files == [str(two)]
            app.batch_folder.set('')
            assert app._handle_drop('create', app.tk.call('list', str(one), str(two))) == 'refuse_drop'
            assert warn.called
        finally:
            app.destroy()
    print('PASS: arrastrar y soltar, nombres con espacios y carpetas origen')

if __name__ == '__main__':
    main()
