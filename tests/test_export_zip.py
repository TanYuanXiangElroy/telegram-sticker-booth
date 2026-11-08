"""Offline checks for PNG/WebP ZIP export (no Telegram token)."""
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sticker_booth.export_zip import collect_pairs, write_zip  # noqa: E402

EXAMPLES = ROOT / "examples" / "stickers"


class ExportZipTests(unittest.TestCase):
    def test_archive_contents_and_dimensions(self):
        pairs = collect_pairs(EXAMPLES)
        self.assertGreaterEqual(len(pairs), 8)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "pack.zip"
            write_zip(pairs, out)
            with zipfile.ZipFile(out) as zf:
                names = set(zf.namelist())
            self.assertIn("README_IMPORT_INSTRUCTIONS.txt", names)
            for stem, _, _ in pairs:
                self.assertIn(f"png/{stem}.png", names)
                self.assertIn(f"webp/{stem}.webp", names)
            # no photos/credentials
            joined = "\n".join(names).lower()
            self.assertNotIn(".env", joined)
            self.assertNotIn("photos/", joined)
            from PIL import Image
            import io
            with zipfile.ZipFile(out) as zf:
                raw = zf.read(f"png/{pairs[0][0]}.png")
                im = Image.open(io.BytesIO(raw))
                self.assertEqual(im.size, (512, 512))
                self.assertEqual(im.mode, "RGBA")

    def test_only_filter_and_filenames_match(self):
        pairs = collect_pairs(EXAMPLES, names=["laugh", "cry"])
        self.assertEqual([p[0] for p in pairs], ["laugh", "cry"])

    def test_missing_dir(self):
        with self.assertRaises(FileNotFoundError):
            collect_pairs(ROOT / "does-not-exist")

    def test_missing_pair(self):
        with self.assertRaises(FileNotFoundError):
            collect_pairs(EXAMPLES, names=["laugh", "no_such_sticker"])

    def test_cli_ok_and_invalid(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "t.zip"
            r = subprocess.run(
                [sys.executable, "-m", "sticker_booth.export_zip", str(EXAMPLES),
                 "--out", str(out), "--only", "laugh"],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            self.assertTrue(out.is_file())
            bad = subprocess.run(
                [sys.executable, "-m", "sticker_booth.export_zip", str(ROOT / "missing"),
                 "--out", str(Path(td) / "x.zip")],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertNotEqual(bad.returncode, 0)


if __name__ == "__main__":
    unittest.main()
