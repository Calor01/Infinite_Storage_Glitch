"""Regresión: título, cabecera y logo de ventana/desktop (sin conexiones de red)."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from isg_gui import App

def test_identity():
    root = Path(__file__).resolve().parent.parent
    desktop = (root / "packaging/isg-desktop.desktop").read_text()
    assert "Name=ISG Desktop\n" in desktop
    assert "Icon=isg-desktop\n" in desktop
    assert "StartupWMClass=Isgdesktop\n" in desktop
    for size in (32,64,128):
        import struct
        image = (root/f"assets/isg-desktop-{size}.png").read_bytes()
        assert image[:8] == b"\x89PNG\r\n\x1a\n"
        assert struct.unpack(">II", image[16:24]) == (size,size)
    app = App()
    try:
        app.update_idletasks()
        assert app.title() == "ISG Desktop"
        assert app.winfo_class() == "Isgdesktop"
        assert app._icon_images
        assert len(app._icon_images) == 3
        assert not hasattr(app, 'header')
        forbidden = ("MP4", ".mp4", ".mkv", ".webm")
        def all_labels(w):
            labels=[]
            for c in w.winfo_children():
                if c.winfo_class() in {"TLabel", "TButton"}:
                    labels.append(c.cget("text"))
                labels.extend(all_labels(c))
            return labels
        assert all(not any(item in str(label) for item in forbidden)
                   for label in all_labels(app))
        assert not any("MP4" in line or ".mp4" in line
                       for line in (app.status.get(), app.estimate.get()))
    finally:
        app.destroy()
    print('PASS: título, etiqueta, logo y ausencia de referencias visibles al contenedor')
if __name__ == '__main__':
    test_identity()
