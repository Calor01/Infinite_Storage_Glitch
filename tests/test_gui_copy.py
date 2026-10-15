"""Verifica los textos de interfaz solicitados y el ETA solo en memoria."""
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from isg_gui import App


def labels(widget):
    """Textos constantes de etiquetas y botones, sin incluir variables temporales."""
    found = []
    for child in widget.winfo_children():
        if child.winfo_class() in {"TLabel", "TButton"}:
            found.append(str(child.cget("text")))
        found.extend(labels(child))
    return found


def test_gui_copy():
    app = App()
    try:
        app.update_idletasks()
        strings = labels(app)
        assert "Convierte archivos en vídeos y recupéralos después." not in strings
        assert "ISG Desktop" not in strings
        assert "Crear vídeo" in strings
        assert "Crear vídeo MP4" not in strings
        assert not any("MP4" in label or ".mp4" in label for label in strings)
        assert "Genera un vídeo independiente por cada archivo" in strings
        assert "Cada vídeo recupera su archivo" in strings
        assert not any("Solo se entrega el archivo íntegro" in x for x in strings)
        assert not any("No sobrescribe destinos" in x for x in strings)
        assert not any("Comprobación de integridad" in x for x in strings)
        assert "Resolución" in strings
        assert "Bloque de píxeles" in strings
        assert "Copias" in strings
        assert "Archivos de salida y privacidad" not in strings
        assert "Sugerencia de inicio" not in strings
        assert app.tabs.index('end') == 4

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "prueba pequeña.txt"
            source.write_bytes(b"Hola ISG Desktop" * 1000)
            app.source_file.set(str(source))
            assert "Duración estimada del vídeo:" in app.estimate.get()
            assert "Tiempo estimado de procesamiento:" in app.estimate.get()
            assert "Bloques:" not in app.estimate.get()
            assert "Origen:" not in app.estimate.get()
            assert "Fotogramas:" not in app.estimate.get()
            # No se anticipan tiempos inventados. El tiempo se calcula al
            # observar progreso real y se olvida al finalizar la tarea.
            app.current_task = "encode"
            app.started = time.monotonic() - 10
            app.events.put(("progress", 0.5, "Generando"))
            app._read_events()
            assert "en total" in app.estimate.get()
            app._clear_session()
            assert app.source_file.get() == ""
            assert app.estimate.get() == "Selecciona un archivo para estimar la duración del vídeo."
    finally:
        app.destroy()
    print("PASS: textos breves, ETA real y restablecimiento.")


if __name__ == '__main__':
    test_gui_copy()
