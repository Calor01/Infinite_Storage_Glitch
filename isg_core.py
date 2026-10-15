"""Motor local de ISG Desktop: fichero -> vídeo -> fichero.

Implementación independiente inspirada por KKarmugil/Infinite_Storage_Glitch
(MIT). No promete compatibilidad con los vídeos del proyecto original.
Formato ISG-DESKTOP 2: índices/CRC por fotograma, SHA-256 global.
"""
from __future__ import annotations

import hashlib
from functools import lru_cache
import json
import math
import os
import contextlib
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import threading
import zlib

MAGIC_FRAME = b"ISGFRM02"
MAGIC_META = b"ISGMETA2"
FRAME_HEADER = struct.Struct(">8s8sIIII")  # magic, id, indice, total, longitud, CRC32
FILE_HEADER = struct.Struct(">8sQ32sH")  # magic, tamano, SHA256, nombre_len
RESOLUTIONS = [(1280, 720), (1920, 1080)]
BLOCKS = (8, 12, 16)
MAX_FRAMES = 10_000_000
MAX_BYTES = 100 * (1024 ** 3)
VERSION = "1.0.0"

class ISGError(Exception):
    """Error seguro para mostrar en la interfaz."""


def _check_tools(*commands: str) -> None:
    missing = [name for name in commands if shutil.which(name) is None]
    if missing:
        raise ISGError("Faltan los programas: " + ", ".join(missing))


def _check_stop(cancel: threading.Event | None) -> None:
    if cancel is not None and cancel.is_set():
        raise ISGError("Operación cancelada.")


def _capacity(width: int, height: int, block: int) -> int:
    cols = width // block
    rows = height // block
    if cols * rows % 8 != 0:
        raise ISGError("Resolución y tamaño de bloque incompatibles.")
    usable = cols * rows // 8 - FRAME_HEADER.size
    if usable <= 0:
        raise ISGError("Fotograma demasiado pequeño.")
    return usable



def estimate_encode(input_file: str, width: int = 1280, height: int = 720,
                    block: int = 8, copies: int = 2) -> dict:
    """Estimación sin leer el archivo: fotogramas y duración teórica (no tamaño MP4)."""
    path = Path(input_file).expanduser()
    if not path.is_file():
        raise ISGError("El archivo de origen no existe.")
    if (width, height) not in RESOLUTIONS or block not in BLOCKS or copies not in (1, 2, 3):
        raise ISGError("Parámetros de codificación no válidos.")
    raw_name = path.name.encode("utf-8")
    if len(raw_name) > 65535:
        raise ISGError("Nombre de archivo demasiado largo.")
    input_bytes = path.stat().st_size
    total_bytes = FILE_HEADER.size + len(raw_name) + input_bytes
    capacity = _capacity(width, height, block)
    frames = math.ceil(total_bytes / capacity)
    if frames > MAX_FRAMES or total_bytes > MAX_BYTES:
        raise ISGError("El archivo supera el límite de esta versión.")
    video_frames = frames * copies
    return {"input_bytes": input_bytes, "total_bytes": total_bytes, "capacity_bytes": capacity,
            "frames": frames, "video_frames": video_frames,
            "video_seconds": video_frames / 24.0}


def _input_chunks(path: Path, header: bytes, size: int, source_digest=None):
    buf = bytearray(header)
    with path.open("rb") as src:
        while True:
            if len(buf) >= size:
                yield bytes(buf[:size])
                del buf[:size]
            else:
                chunk = src.read(max(1024 * 1024, size))
                if not chunk:
                    break
                if source_digest is not None:
                    source_digest.update(chunk)
                buf.extend(chunk)
        if buf:
            yield bytes(buf)


def _file_signature(path: Path) -> tuple[int, int, int, int]:
    """Detecta sustituciones y modificaciones del origen durante la operación."""
    info = path.stat()
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


@contextlib.contextmanager
def _cancel_watch(proc: subprocess.Popen, cancel: threading.Event | None):
    """Detiene FFmpeg aunque la operación esté bloqueada esperando un pipe.

    Al finalizar libera siempre el observador (evita hilos residuales).
    """
    done = threading.Event()
    observer = None
    if cancel is not None:
        def watch():
            while not done.wait(0.1):
                if cancel.is_set():
                    if proc.poll() is None:
                        with contextlib.suppress(ProcessLookupError, OSError):
                            proc.kill()
                    return
        observer = threading.Thread(target=watch, name="isg-cancel-watch", daemon=True)
        observer.start()
    try:
        yield
    finally:
        done.set()
        if observer is not None:
            observer.join(timeout=1)


def _publish_no_overwrite(temporary: Path, target: Path) -> None:
    """Publicación atómica sin riesgo de sustituir un archivo creado entretanto."""
    try:
        os.link(temporary, target)
    except FileExistsError as exc:
        raise ISGError(f"La salida ya existe: {target}. No se sobrescribirá.") from exc
    except OSError as exc:
        raise ISGError(f"No se puede publicar el archivo en ese sistema de ficheros: {exc}") from exc
    temporary.unlink()


def _sha256(path: Path, cancel=None, progress=None):
    digest = hashlib.sha256()
    size = path.stat().st_size
    done = 0
    with path.open("rb") as src:
        while data := src.read(1024 * 1024):
            _check_stop(cancel)
            digest.update(data)
            done += len(data)
            if progress:
                progress(0.05 * done / max(size, 1), "Comprobando integridad…")
    return digest.digest()


@lru_cache(maxsize=4)
def _render_lut(block: int) -> tuple[bytes, ...]:
    black, white = bytes(block), bytes([255])*block
    return tuple(b"".join(white if (v >> shift) & 1 else black
                          for shift in range(7, -1, -1)) for v in range(256))


def _render_frame(packet: bytes, width: int, height: int, block: int) -> bytes:
    cols = width // block
    rows = height // block
    pixels = cols * rows
    payload = packet.ljust(pixels // 8, b"\0")
    black = b"\x00" * block
    white = b"\xff" * block
    lut = _render_lut(block)
    src_row_bytes = cols // 8
    # Para bloques no divisibles por 8 columnas, usar la representación completa.
    if cols % 8:
        whole = [bool(byte & (1 << bit)) for byte in payload for bit in range(7, -1, -1)]
        rows_data = [b"".join(white if bit else black for bit in whole[i * cols:(i + 1) * cols])
                     for i in range(rows)]
    else:
        rows_data = [b"".join(lut[c] for c in payload[i*src_row_bytes:(i+1)*src_row_bytes])
                     for i in range(rows)]
    pad_x = b"\xff" * (width - cols * block)
    out = bytearray()
    for row in rows_data:
        expanded = row + pad_x
        for _ in range(block):
            out.extend(expanded)
    out.extend(b"\xff" * (width * (height - rows * block)))
    return bytes(out)


def encode(input_file: str, output_file: str, width=1280, height=720, block=8,
           copies=2, cancel=None, progress=None) -> Path:
    """Produce un MP4 con archivos locales, sin conexiones de red."""
    _check_tools("ffmpeg")
    src, dest = Path(input_file).expanduser(), Path(output_file).expanduser()
    if not src.is_file():
        raise ISGError("El archivo de entrada no existe.")
    if src.resolve() == dest.resolve():
        raise ISGError("Entrada y salida no pueden ser iguales.")
    if dest.exists() or dest.is_symlink():
        raise ISGError("El archivo de salida ya existe. No se sobrescribirá.")
    if (width, height) not in RESOLUTIONS or block not in BLOCKS or copies not in (1, 2, 3):
        raise ISGError("Parámetros de codificación incorrectos.")
    if not dest.parent.is_dir():
        raise ISGError("La carpeta de destino no existe.")
    encoded_name = src.name.encode("utf-8")
    if len(encoded_name) > 65535:
        raise ISGError("Nombre de archivo demasiado largo.")
    cap = _capacity(width, height, block)
    total_size = FILE_HEADER.size + len(encoded_name) + src.stat().st_size
    frame_count = math.ceil(total_size / cap)
    if frame_count > MAX_FRAMES or total_size > MAX_BYTES:
        raise ISGError("El archivo supera el límite de esta versión.")

    _check_stop(cancel)
    signature = _file_signature(src)
    digest = _sha256(src, cancel, progress)
    if signature != _file_signature(src):
        raise ISGError("El archivo de origen cambió durante la comprobación de integridad.")
    header = FILE_HEADER.pack(MAGIC_META, src.stat().st_size, digest, len(encoded_name)) + encoded_name
    stream_id = os.urandom(8)
    tmp_dest = dest.with_name("." + dest.stem + ".isg-partial-" + stream_id.hex() + ".mp4")
    cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
           "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{width}x{height}",
           "-r", "24", "-protocol_whitelist", "pipe", "-i", "pipe:0", "-an", "-c:v", "libx264",
           "-preset", "veryfast", "-crf", "12", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", str(tmp_dest)]
    proc = None
    with tempfile.TemporaryFile() as ffmpeg_errors:
      try:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=ffmpeg_errors)
        assert proc.stdin is not None
        stream_digest = hashlib.sha256()
        with _cancel_watch(proc, cancel):
          for i, chunk in enumerate(_input_chunks(src, header, cap, stream_digest)):
              _check_stop(cancel)
              checksum = zlib.crc32(chunk) & 0xffffffff
              packet = FRAME_HEADER.pack(MAGIC_FRAME, stream_id, i, frame_count,
                                         len(chunk), checksum) + chunk
              pixels = _render_frame(packet, width, height, block)
              for _ in range(copies):
                  _check_stop(cancel)
                  proc.stdin.write(pixels)
              if progress:
                  progress(0.05 + 0.94*(i+1)/frame_count,
                           f"Codificando bloque {i+1}/{frame_count} ({copies} copias)")
          proc.stdin.close()
          code = proc.wait()
        _check_stop(cancel)
        if code != 0:
            ffmpeg_errors.seek(0)
            msg = ffmpeg_errors.read().decode("utf-8", errors="replace")
            raise ISGError("FFmpeg no pudo crear el vídeo: " + msg[-1200:])
        if stream_digest.digest() != digest or signature != _file_signature(src):
            raise ISGError("El archivo de origen cambió durante la codificación; no se entrega el vídeo.")
        _publish_no_overwrite(tmp_dest, dest)
        if progress:
            progress(1.0, "Vídeo generado localmente.")
        return dest
      except (BrokenPipeError, OSError) as exc:
        _check_stop(cancel)
        raise ISGError("Error durante la conversión: " + str(exc)) from exc
      finally:
        if proc is not None:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            if proc.stdin:
                with contextlib.suppress(OSError):
                    proc.stdin.close()
        if tmp_dest.exists():
            tmp_dest.unlink()


def _read_exact(source, size: int):
    buf = bytearray()
    while len(buf) < size:
        part = source.read(size - len(buf))
        if not part:
            break
        buf.extend(part)
    return bytes(buf)


def _decode_pixels(raw: bytes, width: int, height: int, block: int) -> bytes:
    cols, rows = width // block, height // block
    out = bytearray(cols * rows // 8)
    acc = bits = index = 0
    half = block // 2
    for y in range(rows):
        offset = (y*block+half)*width + half
        for x in range(cols):
            acc = (acc << 1) | (raw[offset + x*block] > 127)
            bits += 1
            if bits == 8:
                out[index] = acc
                index += 1
                acc = bits = 0
    return bytes(out)


def _unpack_frame(raw: bytes, width: int, height: int, block: int):
    try:
        data = _decode_pixels(raw, width, height, block)
        if len(data) < FRAME_HEADER.size:
            return None
        magic, ident, index, total, size, checksum = FRAME_HEADER.unpack_from(data)
        if magic != MAGIC_FRAME or not (0 < total <= MAX_FRAMES) or index >= total:
            return None
        cap = _capacity(width, height, block)
        if total * cap > MAX_BYTES or not (0 < size <= cap):
            return None
        payload = data[FRAME_HEADER.size:FRAME_HEADER.size + size]
        if zlib.crc32(payload) & 0xffffffff != checksum:
            return None
        return ident, index, total, payload
    except (ValueError, struct.error, IndexError):
        return None


def _probe(path: Path):
    p = subprocess.run(["ffprobe", "-v", "error", "-protocol_whitelist", "file,pipe", "-format_whitelist", "mov,matroska,webm", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height,nb_frames",
                        "-of", "json", str(path)], capture_output=True, text=True)
    if p.returncode:
        raise ISGError("No se puede leer el vídeo: " + p.stderr[-500:])
    try:
        video = json.loads(p.stdout)["streams"][0]
        return int(video["width"]), int(video["height"]), int(video.get("nb_frames") or 0)
    except (IndexError, KeyError, ValueError, TypeError) as exc:
        raise ISGError("FFprobe no pudo leer la información del vídeo.") from exc


def decode(input_video: str, output_dir: str, cancel=None, progress=None) -> Path:
    """Recupera y verifica SHA-256. Nunca sobrescribe un fichero."""
    _check_tools("ffmpeg", "ffprobe")
    video, folder = Path(input_video).expanduser(), Path(output_dir).expanduser()
    if not video.is_file() or not folder.is_dir():
        raise ISGError("Vídeo de entrada o carpeta de salida inexistente.")
    width, height, approximate_frames = _probe(video)
    if (width, height) not in RESOLUTIONS:
        raise ISGError("Resolución no compatible; se necesita un vídeo compatible con ISG Desktop.")
    cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-protocol_whitelist", "file,pipe", "-format_whitelist", "mov,matroska,webm", "-i", str(video),
           "-an", "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1"]
    proc = None
    with tempfile.TemporaryFile() as ffmpeg_errors, tempfile.TemporaryDirectory(dir=folder, prefix=".isg-recuperacion-") as work:
        path_parts = Path(work) / "partes.bin"
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=ffmpeg_errors)
            assert proc.stdout is not None
            block = cap = ident = count = None
            received = set()
            decoded_frames = 0
            with _cancel_watch(proc, cancel), path_parts.open("w+b") as out:
                while True:
                    _check_stop(cancel)
                    raw = _read_exact(proc.stdout, width * height)
                    _check_stop(cancel)
                    if not raw:
                        break
                    if len(raw) != width * height:
                        raise ISGError("Fotograma incompleto.")
                    decoded_frames += 1
                    candidate = None
                    if block is None:
                        for blk in BLOCKS:
                            candidate = _unpack_frame(raw, width, height, blk)
                            if candidate is not None:
                                block = blk
                                cap = _capacity(width, height, block)
                                break
                    else:
                        candidate = _unpack_frame(raw, width, height, block)
                    if candidate:
                        this_id, index, this_count, payload = candidate
                        if ident is None:
                            ident, count = this_id, this_count
                            # La restauración ocupa aproximadamente 2 veces el tamaño
                            # de los bloques: reconstrucción + archivo verificado.
                            estimated_disk = count * cap * 2 + 8 * 1024 * 1024
                            if shutil.disk_usage(folder).free < estimated_disk:
                                raise ISGError("Espacio insuficiente para recuperar el archivo: "
                                               "se necesita aproximadamente el doble de su tamaño libre.")
                        if ident == this_id and count == this_count and index not in received:
                            out.seek(index * cap)
                            out.write(payload)
                            received.add(index)
                    if progress and decoded_frames % 3 == 0:
                        value = decoded_frames / approximate_frames if approximate_frames else 0.1
                        progress(min(value*0.8, 0.8),
                                 f"Analizados {decoded_frames} fotogramas; bloques únicos: {len(received)}")
            if proc.stdout:
                proc.stdout.close()
            code = proc.wait()
            _check_stop(cancel)
            if code != 0:
                ffmpeg_errors.seek(0)
                err = ffmpeg_errors.read().decode("utf-8", errors="replace")
                raise ISGError("FFmpeg no pudo decodificar: " + err[-1000:])
            if count is None:
                raise ISGError("No se encontraron bloques válidos. Puede ser un vídeo incompatible o estar dañado.")
            if len(received) != count:
                missing = sorted(set(range(count)) - received)
                preview = ", ".join(str(v) for v in missing[:12])
                raise ISGError(f"Faltan {count-len(received)} de {count} bloques. Índices: {preview}. "
                               "Una recodificación puede haber alterado el vídeo.")
            with path_parts.open("rb") as parts:
                head = _read_exact(parts, FILE_HEADER.size)
                if len(head) != FILE_HEADER.size:
                    raise ISGError("Cabecera de fichero incompleta.")
                magic, size, expected_hash, nlen = FILE_HEADER.unpack(head)
                if magic != MAGIC_META or size > MAX_BYTES or nlen > 8192:
                    raise ISGError("Cabecera de datos incorrecta.")
                raw_name = _read_exact(parts, nlen)
                try:
                    original_name = raw_name.decode("utf-8")
                except UnicodeError as exc:
                    raise ISGError("Nombre de archivo ilegible.") from exc
                name = Path(original_name).name
                if (not name or name in (".", "..") or any(ord(c) < 32 or ord(c) == 127 for c in name)
                        or "\\" in name or name != original_name or name.startswith(".isg-")):
                    raise ISGError("Nombre de archivo de salida no válido.")
                target = folder / name
                if target.exists() or target.is_symlink():
                    raise ISGError(f"La salida ya existe: {target}. No se sobrescribirá.")
                temporary_output = Path(work) / "reconstruido.part"
                digest = hashlib.sha256()
                remaining = size
                with temporary_output.open("wb") as dest:
                    while remaining:
                        _check_stop(cancel)
                        piece = parts.read(min(1024 * 1024, remaining))
                        if not piece:
                            raise ISGError("Faltan datos en el flujo reconstruido.")
                        dest.write(piece)
                        digest.update(piece)
                        remaining -= len(piece)
                        if progress and size:
                            progress(0.8 + 0.19*(size-remaining)/size,
                                     f"Comprobando integridad ({size-remaining:,}/{size:,} bytes)")
                _check_stop(cancel)
                if digest.digest() != expected_hash:
                    raise ISGError("Error de integridad: el archivo recuperado no coincide con el original.")
                # Publicación atómica después de verificar: sin archivos finales parciales.
                _publish_no_overwrite(temporary_output, target)
            if progress:
                progress(1.0, "Archivo recuperado y comprobado.")
            return target
        finally:
            if proc is not None:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait()
                if proc.stdout:
                    with contextlib.suppress(OSError):
                        proc.stdout.close()
