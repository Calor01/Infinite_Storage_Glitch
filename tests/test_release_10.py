"""Pruebas para recuperación por lotes y regresiones de la edición 1.0."""
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from isg_batch import (prepare_decode_jobs, execute_decode_jobs,
                       MAX_BATCH, prepare_jobs)
from isg_core import ISGError, encode, decode, _render_lut


class ReleaseTests(unittest.TestCase):
    def test_decode_batch_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            videos, recovered = root / 'videos', root / 'recovered'
            videos.mkdir(); recovered.mkdir()
            expected = {}
            for number in (1, 2):
                name = f'ejemplo-{number}.bin'
                content = os.urandom(113 * number)
                src = root / name
                src.write_bytes(content)
                video = videos / (name + '.mp4')
                encode(str(src), str(video), block=12, copies=2)
                expected[name] = content
            output = []
            status = execute_decode_jobs(
                prepare_decode_jobs([str(f) for f in videos.iterdir()], str(recovered)),
                cancel=threading.Event(), progress=lambda _p, _m: None,
                item_done=lambda src, dest, ok, msg: output.append((src, dest, ok, msg)))
            self.assertEqual((status['succeeded'], status['failed']), (2, 0))
            self.assertEqual(status['output_folder'], str(recovered))
            self.assertEqual(len(output), 2)
            self.assertTrue(all(row[2] for row in output))
            for name, content in expected.items():
                self.assertEqual((recovered / name).read_bytes(), content)

    def test_duplicate_recovered_name_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            src = root / 'mismo.bin'; src.write_bytes(b'UNICO' * 25)
            video = root / 'original.mp4'
            encode(str(src), str(video), block=16, copies=1)
            second = root / 'copia.mp4'; second.write_bytes(video.read_bytes())
            dest = root / 'salida'; dest.mkdir()
            rows = []
            output = execute_decode_jobs(prepare_decode_jobs([str(video), str(second)], str(dest)),
                cancel=threading.Event(), progress=lambda _p, _m: None,
                item_done=lambda src, target, ok, msg: rows.append((src, target, ok, msg)))
            self.assertEqual((output['succeeded'], output['failed']), (1, 1))
            self.assertIn('ya existe', rows[1][3])
            self.assertEqual((dest / 'mismo.bin').read_bytes(), src.read_bytes())

    def test_missing_video_does_not_stop_next(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            src = root / 'data.bin'; src.write_bytes(b'good'*27)
            video = root / 'video.mp4'; encode(str(src), str(video))
            bad = root / 'invalid.mp4'; bad.write_bytes(b'NOT-A-MOVIE')
            dest = root / 'out'; dest.mkdir()
            rows = []
            result = execute_decode_jobs(prepare_decode_jobs([str(bad), str(video)], str(dest)),
                cancel=threading.Event(), progress=lambda _p, _m: None,
                item_done=lambda src, target, ok, msg: rows.append(ok))
            self.assertEqual((result['succeeded'], result['failed']), (1, 1))
            self.assertEqual(rows, [False, True])
            self.assertEqual((dest / src.name).read_bytes(), src.read_bytes())

    def test_batch_limits_and_deduplication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); movie = root / 'a.mp4'; movie.write_bytes(b'dummy')
            with self.assertRaisesRegex(ISGError, 'duplicada'):
                prepare_decode_jobs([str(movie), str(movie)], str(root))
            with self.assertRaises(ISGError):
                prepare_decode_jobs([str(movie)] * (MAX_BATCH + 1), str(root))
            with self.assertRaises(ISGError):
                prepare_decode_jobs([], str(root))

    def test_cancel_queue_before_start(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); movie = root / 'a.mp4'; movie.write_bytes(b'dummy')
            event = threading.Event(); event.set()
            with self.assertRaisesRegex(ISGError, 'cancelada'):
                execute_decode_jobs(prepare_decode_jobs([str(movie)], str(root)),
                   cancel=event, progress=lambda *_: None,
                   item_done=lambda *_: self.fail('El trabajo no debe arrancar'))

    def test_default_per_file_folders(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            aa = root/'a'; bb = root/'b'; aa.mkdir(); bb.mkdir()
            first = aa/'same.bin'; second = bb/'same.bin'
            first.write_bytes(b'a'); second.write_bytes(b'b')
            jobs = prepare_jobs([str(first), str(second)], '')
            self.assertEqual(jobs[0][1], aa/'same.bin.mp4')
            self.assertEqual(jobs[1][1], bb/'same.bin.mp4')
            self.assertEqual(prepare_decode_jobs([str(first), str(second)], ''),
                             [(first, aa), (second, bb)])

    def test_lut_is_cached(self):
        self.assertIs(_render_lut(8), _render_lut(8))


if __name__ == '__main__':
    unittest.main()
