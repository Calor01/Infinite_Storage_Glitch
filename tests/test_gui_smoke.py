"""Smoke test gráfico de todos los paneles con ventana redimensionada."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from isg_gui import App


def test_gui():
    app = App()
    try:
        app.update_idletasks()
        assert app.title() == 'ISG Desktop'
        assert app.tabs.index('end') == 4
        assert 'Información' in [app.tabs.tab(i, 'text') for i in app.tabs.tabs()]
        assert not hasattr(app, 'disclaimer')
        assert not hasattr(app, 'history')
        assert app.stop_button.instate(['disabled'])
        assert not hasattr(app, 'diagnostics')
        assert not hasattr(app, 'open_folder')
        for tab in range(app.tabs.index('end')):
            app.tabs.select(tab)
            app.update_idletasks()
        app.geometry('710x500+0+0')
        app.update_idletasks()
        assert app.footer.winfo_rooty() + app.footer.winfo_height() <= app.winfo_rooty() + app.winfo_height(), (
            app.footer.winfo_rooty(), app.footer.winfo_height(), app.winfo_height())
        assert app.start_batch.winfo_exists()
        assert app.batch_list.winfo_exists()
        assert app.decode_batch_list.winfo_exists()
        assert app.start_decode_batch.winfo_exists()
    finally:
        app.destroy()
    print('PASS: cuatro pestañas, ventana pequeña y progreso actual.')


if __name__ == '__main__':
    test_gui()
