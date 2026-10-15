import os
from pathlib import Path
import tempfile
import unittest

from isg_core import ISGError, estimate_encode
from isg_gui import readable_size, readable_time


class EstimateTests(unittest.TestCase):
    def test_estimate_ranges(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "abc.bin"
            path.write_bytes(os.urandom(17_333))
            result = estimate_encode(str(path), 1280, 720, 8, 2)
            self.assertEqual(result["input_bytes"], 17_333)
            self.assertGreater(result["frames"], 0)
            self.assertEqual(result["frames"] * 2, result["video_frames"])
            self.assertAlmostEqual(result["video_frames"] / 24, result["video_seconds"])

    def test_rejects_bad_parameters(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "test.bin"
            path.write_bytes(b"abc")
            for block in (-1, 7, 100):
                with self.assertRaises(ISGError):
                    estimate_encode(str(path), block=block)

    def test_format_helpers(self):
        self.assertEqual(readable_size(1024), "1.0 KiB")
        self.assertEqual(readable_time(65), "1 min 05 s")


if __name__ == "__main__":
    unittest.main()
