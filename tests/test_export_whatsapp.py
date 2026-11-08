import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sticker_booth.export_whatsapp import MAX_BYTES, export_dir, to_whatsapp_webp  # noqa: E402

EX = ROOT / "examples" / "stickers"


class WhatsAppExportTests(unittest.TestCase):
    def test_size_limit(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            rows = export_dir(EX, out)
            self.assertGreaterEqual(len(rows), 8)
            for name, n in rows:
                self.assertLessEqual(n, MAX_BYTES, name)
                p = out / name
                self.assertTrue(p.is_file())
                from PIL import Image
                with Image.open(p) as im:
                    self.assertEqual(im.size, (512, 512))
            self.assertTrue((out / "README_WHATSAPP.txt").is_file())

    def test_missing(self):
        with self.assertRaises(FileNotFoundError):
            export_dir(ROOT / "missing", Path(tempfile.mkdtemp()))

    def test_cli(self):
        with tempfile.TemporaryDirectory() as td:
            r = subprocess.run(
                [sys.executable, "-m", "sticker_booth.export_whatsapp", str(EX), "--out", td],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)


if __name__ == "__main__":
    unittest.main()
