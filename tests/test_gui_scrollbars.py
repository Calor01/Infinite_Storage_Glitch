"""Regresión de barras automáticas para pestañas y listas."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from isg_gui import App


def settle(app):
    for _ in range(5):
        app.update_idletasks()
        app.update()


def main():
    app = App()
    try:
        app.geometry('960x740+0+0')
        settle(app)
        tabs = app._scrolled_tabs
        assert list(tabs) == ['Crear', 'Recuperar', 'Lotes', 'Información']
        for index, name in enumerate(tabs):
            app.tabs.select(index)
            settle(app)
            _, canvas, bar, inner = tabs[name]
            required = inner.winfo_reqheight() > canvas.winfo_height() + 1
            assert bool(bar.winfo_manager()) == required, (name, required, bar.winfo_manager(), inner.winfo_reqheight(), canvas.winfo_height())

        # Pestaña corta: nunca debe mostrar barra con espacio suficiente.
        app.tabs.select(3)
        app.geometry('1100x900+0+0')
        settle(app)
        assert not tabs['Información'][2].winfo_manager()
        # Reducir tamaño: la barra aparece si la pestaña excede la altura.
        app.tabs.select(2)
        app.geometry('710x500+0+0')
        settle(app)
        assert tabs['Lotes'][2].winfo_manager(), 'Lotes debe poder desplazarse en ventana reducida'
        _, canvas, bar, inner = tabs['Lotes']
        canvas.yview_moveto(1)
        settle(app)
        assert canvas.yview()[0] > 0
        # Ampliar la ventana más allá del tamaño de contenido: ocultar barra.
        app.geometry('1400x1550+0+0')
        settle(app)
        assert inner.winfo_reqheight() <= canvas.winfo_height() + 1
        assert not bar.winfo_manager(), 'La barra de Lotes debe ocultarse tras ampliar'
        assert canvas.yview()[0] == 0, 'Al ocultar barra volver al inicio'

        # Listas vacías no muestran barras. Si desbordan, sí.
        _,_,_,_ = tabs['Lotes']
        # Verificamos el gestor de las barras a partir de los widgets hijos.
        def list_scroll(listbox):
            return next(child for child in listbox.master.winfo_children()
                        if child.winfo_class() == 'TScrollbar')
        for target in (app.batch_list, app.decode_batch_list):
            bar = list_scroll(target)
            settle(app)
            assert not bar.winfo_manager(), 'Una lista vacía no necesita barra'
            for i in range(10):
                target.insert('end', f'archivo {i}')
            settle(app)
            assert bar.winfo_manager(), 'Una lista larga debe mostrar barra'
            target.delete(0, 'end')
            settle(app)
            assert not bar.winfo_manager(), 'Al vaciar la lista debe desaparecer la barra'
    finally:
        app.destroy()
    print('PASS: barras dinámicas de las 4 pestañas y 2 listas.')


if __name__ == '__main__':
    main()
