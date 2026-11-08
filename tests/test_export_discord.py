import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sticker_booth.export_discord import MAX_BYTES, SIZE, export_dir  # noqa: E402

EX = ROOT / "examples" / "stickers"


class DiscordExportTests(unittest.TestCase):
    def test_dimensions_and_size(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            rows = export_dir(EX, out)
            self.assertGreaterEqual(len(rows), 8)
            from PIL import Image
            for name, n in rows:
                self.assertLessEqual(n, MAX_BYTES)
                with Image.open(out / name) as im:
                    self.assertEqual(im.size, (SIZE, SIZE))
                    self.assertEqual(im.mode, "RGBA")
            self.assertTrue((out / "README_DISCORD.txt").is_file())

    def test_cli(self):
        with tempfile.TemporaryDirectory() as td:
            r = subprocess.run(
                [sys.executable, "-m", "sticker_booth.export_discord", str(EX), "--out", td],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)


if __name__ == "__main__":
    unittest.main()
