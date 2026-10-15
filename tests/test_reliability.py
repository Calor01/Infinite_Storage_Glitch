"""Regresiones de seguridad de datos y cancelación."""
from pathlib import Path
import os
import shutil
import tempfile
import threading
import unittest

from isg_core import ISGError, decode, encode, _publish_no_overwrite


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "Necesita FFmpeg")
class ReliabilityTests(unittest.TestCase):
    def test_cancel_encode_cleans_partial_video(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            src, dst = folder / "input.bin", folder / "output.mp4"
            src.write_bytes(os.urandom(75_000))
            stop = threading.Event()

            def tick(_value, msg):
                if "Codificando bloque" in msg:
                    stop.set()

            with self.assertRaisesRegex(ISGError, "cancelada"):
                encode(str(src), str(dst), block=8, copies=2, cancel=stop, progress=tick)
            self.assertFalse(dst.exists())
            self.assertEqual(list(folder.glob("*.isg-partial-*")), [])

    def test_cancel_decode_cleans_output(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            src, video = folder / "data.bin", folder / "sample.mp4"
            src.write_bytes(os.urandom(5_000))
            encode(str(src), str(video), block=16, copies=1)
            recovered = folder / "recovered"
            recovered.mkdir()
            stop = threading.Event()

            def tick(_value, msg):
                if "Analizados" in msg:
                    stop.set()

            with self.assertRaisesRegex(ISGError, "cancelada"):
                decode(str(video), str(recovered), cancel=stop, progress=tick)
            self.assertEqual(list(recovered.iterdir()), [])

    def test_source_changed_during_stream(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            src, video = folder / "input.bin", folder / "sample.mp4"
            src.write_bytes(os.urandom(10_000))
            changed = False

            def tick(_value, msg):
                nonlocal changed
                if not changed and "Codificando bloque" in msg:
                    with src.open("r+b") as writer:
                        writer.seek(0)
                        writer.write(b"changed")
                    changed = True

            with self.assertRaisesRegex(ISGError, "cambió"):
                encode(str(src), str(video), block=8, copies=1, progress=tick)
            self.assertTrue(changed)
            self.assertFalse(video.exists())


class AtomicPublicationTests(unittest.TestCase):
    def test_no_overwrite_if_target_created_late(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            source, target = folder / "temporary", folder / "result"
            source.write_bytes(b"generated")
            target.write_bytes(b"important-existing")
            with self.assertRaisesRegex(ISGError, "ya existe"):
                _publish_no_overwrite(source, target)
            self.assertEqual(target.read_bytes(), b"important-existing")
            self.assertEqual(source.read_bytes(), b"generated")

    def test_atomic_publication(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            source, target = folder / "temporary", folder / "result"
            source.write_bytes(b"tested")
            _publish_no_overwrite(source, target)
            self.assertFalse(source.exists())
            self.assertEqual(target.read_bytes(), b"tested")


if __name__ == "__main__":
    unittest.main()
