"""Cola de conversión: éxito, fallos, cancelación y colisiones."""
from pathlib import Path
import os
import tempfile
import threading
import unittest
from unittest.mock import patch

from isg_batch import prepare_jobs, execute_jobs
from isg_core import ISGError, decode


class PlanningTests(unittest.TestCase):
    def test_collision_and_existing_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            inputs = [root / 'a' / 'foo.txt', root / 'b' / 'foo.txt']
            for p in inputs:
                p.parent.mkdir(); p.write_bytes(b'abc')
            output = root / 'out'; output.mkdir()
            with self.assertRaisesRegex(ISGError, 'mismo nombre'):
                prepare_jobs([str(p) for p in inputs], str(output))
            (output / 'foo.txt.mp4').write_bytes(b'not ours')
            with self.assertRaisesRegex(ISGError, 'ya existe'):
                prepare_jobs([str(inputs[0])], str(output))
            self.assertEqual((output / 'foo.txt.mp4').read_bytes(), b'not ours')

    def test_validation_of_batch_length_and_folder(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ISGError):
                prepare_jobs([], d)
            with self.assertRaises(ISGError):
                prepare_jobs(['no-such-file'], d)
            with self.assertRaises(ISGError):
                prepare_jobs(['a'], str(Path(d) / 'missing'))


class ExecutionTests(unittest.TestCase):
    def test_batch_roundtrip_and_continue_on_failure(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); out = root / 'out'; out.mkdir()
            a, b = root / 'a.bin', root / 'b.bin'
            data_a, data_b = os.urandom(2700), os.urandom(2800)
            a.write_bytes(data_a); b.write_bytes(data_b)
            jobs = prepare_jobs([str(a), str(b)], str(out))
            seen = []; progress = []
            report = execute_jobs(jobs, width=1280, height=720, block=16, copies=1,
                                  cancel=threading.Event(), progress=lambda n, s: progress.append(n),
                                  item_done=lambda src, dest, ok, info: seen.append((src, dest, ok)))
            self.assertEqual(report['succeeded'], 2)
            self.assertEqual(report['failed'], 0)
            self.assertTrue(all(x[2] for x in seen))
            self.assertEqual(progress[-1], 1.0)
            restore = root / 'restored'; restore.mkdir()
            self.assertEqual(decode(str(out / 'a.bin.mp4'), str(restore)).read_bytes(), data_a)
            self.assertEqual(decode(str(out / 'b.bin.mp4'), str(restore)).read_bytes(), data_b)

    def test_continue_if_file_deleted_after_plan(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); out = root/'out'; out.mkdir()
            a, b = root/'a', root/'b'
            a.write_bytes(b'123'); b.write_bytes(b'456')
            jobs = prepare_jobs([str(a), str(b)], str(out))
            a.unlink()
            outcomes = []
            result = execute_jobs(jobs, width=1280, height=720, block=16, copies=1,
                                  cancel=threading.Event(), progress=lambda *_: None,
                                  item_done=lambda *items: outcomes.append(items[2]))
            self.assertEqual((result['failed'], result['succeeded']), (1, 1))
            self.assertEqual(outcomes, [False, True])

    def test_cancelled_batch_does_not_start_jobs(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); a = root/'a'; a.write_bytes(b'abc')
            stop = threading.Event(); stop.set()
            jobs = prepare_jobs([str(a)], d)
            with self.assertRaisesRegex(ISGError, 'cancelada'):
                execute_jobs(jobs, width=1280, height=720, block=16, copies=1,
                             cancel=stop, progress=lambda *_: None, item_done=lambda *_: None)
            self.assertFalse((root/'a.mp4').exists())


if __name__ == '__main__':
    unittest.main()
