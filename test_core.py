"""Prueba de ida y vuelta, ejecución: python3 test_core.py"""
import hashlib
from pathlib import Path
import tempfile
from isg_core import encode, decode

with tempfile.TemporaryDirectory() as temp:
    folder = Path(temp)
    src = folder / 'archivo de prueba Español ü + bytes.bin'
    src.write_bytes(bytes(range(256)) * 20 + b'\x00\xff' * 5)
    video = folder / 'video.mp4'
    encode(str(src), str(video), width=1280, height=720, block=8, copies=2)
    output_dir = folder / 'recuperado'
    output_dir.mkdir()
    recovered = decode(str(video), str(output_dir))
    assert src.read_bytes() == recovered.read_bytes()
    print('PASS: Archivo restaurado con bytes idénticos')
    print('Vídeo local:', video.stat().st_size, 'bytes')
    print('SHA-256:', hashlib.sha256(recovered.read_bytes()).hexdigest())
