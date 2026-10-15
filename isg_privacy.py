"""Sin configuración ni historial persistentes; limpieza de archivos heredados."""
from __future__ import annotations
from pathlib import Path
import os

DEFAULTS = {"resolution": "1280x720", "block_size": "8", "redundancy": "2",
            "restore_folder": "", "batch_folder": "", "decode_batch_folder": "",
}


def legacy_paths() -> tuple[Path, Path]:
    def directory(var: str, default: str) -> Path:
        value = os.environ.get(var, "")
        root = Path(value) if value and Path(value).is_absolute() else Path.home() / default
        return root / "isg-desktop"
    return (directory("XDG_CONFIG_HOME", ".config") / "settings.json",
            directory("XDG_STATE_HOME", ".local/state") / "history.json")


def cleanup_legacy_state() -> list[Path]:
    """Retira ficheros conocidos de versiones antiguas, sin borrar otros datos.

    No es un borrado forense: las copias o snapshots del sistema pueden conservarlos.
    """
    remaining = []
    for path in legacy_paths():
        try:
            path.unlink(missing_ok=True)
        except OSError:
            remaining.append(path)
    return remaining
