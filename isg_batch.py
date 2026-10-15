"""Colas secuenciales de creación y recuperación de ISG Desktop.

No se procesan trabajos en paralelo para evitar agotar RAM/CPU/disco al
codificar vídeos HD. Los resultados individuales se mantienen tras cancelar.
"""
from __future__ import annotations

from pathlib import Path
import threading
from typing import Callable

from isg_core import ISGError, decode, encode

MAX_BATCH = 500


def _prepare_inputs(files: list[str], folder: str) -> tuple[list[Path], Path | None]:
    dest_dir = Path(folder).expanduser() if folder.strip() else None
    if dest_dir is not None and not dest_dir.is_dir():
        raise ISGError("La carpeta de salida del lote no existe.")
    if not files or len(files) > MAX_BATCH:
        raise ISGError(f"Selecciona entre 1 y {MAX_BATCH} archivos.")
    result = []
    seen = set()
    for raw in files:
        src = Path(raw).expanduser()
        if not src.is_file():
            raise ISGError(f"Archivo de origen inexistente: {src.name}")
        # Evita duplicados incluso si se añade el mismo archivo con otra ruta.
        signature = str(src.resolve())
        if signature in seen:
            raise ISGError(f"Entrada duplicada: {src.name}")
        seen.add(signature)
        result.append(src)
    return result, dest_dir


def prepare_jobs(files: list[str], folder: str) -> list[tuple[Path, Path]]:
    """Prepara lotes de creación conservando la API de la v0.4."""
    sources, dest_dir = _prepare_inputs(files, folder)
    result = []
    output_names = set()
    for src in sources:
        out = (dest_dir or src.parent) / (src.name + ".mp4")
        if str(out.resolve()) in output_names:
            raise ISGError(f"Hay dos archivos con el mismo nombre: {src.name}. "
                           "Ponles nombres diferentes o crea lotes separados.")
        output_names.add(str(out.resolve()))
        if out.exists() or out.is_symlink():
            raise ISGError(f"El destino ya existe: {out.name}. No se sobrescribirá.")
        result.append((src, out))
    return result


def prepare_decode_jobs(files: list[str], folder: str) -> list[tuple[Path, Path]]:
    """Los nombres recuperados se obtienen del vídeo, no del nombre del MP4."""
    sources, dest_dir = _prepare_inputs(files, folder)
    return [(src, dest_dir or src.parent) for src in sources]


def _run_jobs(jobs: list[tuple[Path, Path]], *, cancel: threading.Event,
              progress: Callable[[float, str], None],
              item_done: Callable[[Path, Path, bool, str], None],
              operation: Callable[[Path, Path, Callable[[float, str], None]], Path],
              verb: str) -> dict:
    if not jobs:
        raise ISGError("El lote está vacío.")
    succeeded = failed = 0
    for index, (src, dest) in enumerate(jobs):
        if cancel.is_set():
            raise ISGError("Operación cancelada.")
        prefix = f"{verb} {index + 1}/{len(jobs)}: "
        progress(index / len(jobs), prefix + src.name)
        try:
            actual = operation(src, dest, lambda fraction, msg:
                               progress((index + min(max(fraction, 0), 1)) / len(jobs), prefix + msg))
            succeeded += 1
            item_done(src, actual, True, "Integridad comprobada" if verb == "Recuperando" else "Vídeo generado")
        except (ISGError, OSError, ValueError) as exc:
            if cancel.is_set():
                raise ISGError("Operación cancelada.") from exc
            failed += 1
            item_done(src, dest, False, str(exc))
    progress(1.0, f"Lote finalizado: {succeeded} correctos, {failed} fallidos")
    return {"succeeded": succeeded, "failed": failed,
            "output_folder": str(jobs[0][1] if verb == "Recuperando" else jobs[0][1].parent),
            "total": len(jobs)}


def execute_jobs(jobs: list[tuple[Path, Path]], *, width: int, height: int,
                 block: int, copies: int, cancel: threading.Event,
                 progress: Callable[[float, str], None],
                 item_done: Callable[[Path, Path, bool, str], None]) -> dict:
    """Crea los vídeos uno a uno. Si falla uno, pasa al siguiente."""
    return _run_jobs(jobs, cancel=cancel, progress=progress, item_done=item_done,
                     verb="Convirtiendo", operation=lambda src, dest, cb:
                     encode(str(src), str(dest), width, height, block, copies, cancel, cb))


def execute_decode_jobs(jobs: list[tuple[Path, Path]], *, cancel: threading.Event,
                        progress: Callable[[float, str], None],
                        item_done: Callable[[Path, Path, bool, str], None]) -> dict:
    """Recupera varios vídeos independientemente, verificando cada SHA-256."""
    return _run_jobs(jobs, cancel=cancel, progress=progress, item_done=item_done,
                     verb="Recuperando", operation=lambda src, dest, cb:
                     decode(str(src), str(dest), cancel, cb))
