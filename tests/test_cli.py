"""La CLI permite hacer copias y restaurarlas sin abrir una pantalla gráfica."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / 'isg_cli.py'


class CLITests(unittest.TestCase):
    def test_version_and_estimate(self):
        res = subprocess.run([sys.executable, str(CLI), '--version'],
                             capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn('1.0.0', res.stdout)
        with tempfile.TemporaryDirectory() as d:
            src = Path(d)/'test.bin'; src.write_bytes(b'123456')
            res = subprocess.run([sys.executable, str(CLI), 'estimate', str(src)],
                                 capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)
            self.assertEqual(json.loads(res.stdout)['input_bytes'], 6)

    def test_cli_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            src = p/'test.bin'; src.write_bytes(b'CLI SAMPLE' * 33)
            video = p/'test.mp4'
            restored = p/'restore'; restored.mkdir()
            created = subprocess.run([sys.executable, str(CLI), 'create', str(src), str(video),
                                      '--block', '12', '--copies', '1'],
                                     capture_output=True, text=True, timeout=40)
            self.assertEqual(created.returncode, 0, created.stderr)
            decoded = subprocess.run([sys.executable, str(CLI), 'recover', str(video), str(restored)],
                                     capture_output=True, text=True, timeout=40)
            self.assertEqual(decoded.returncode, 0, decoded.stderr)
            self.assertEqual((restored/src.name).read_bytes(), src.read_bytes())


if __name__ == '__main__':
    unittest.main()
