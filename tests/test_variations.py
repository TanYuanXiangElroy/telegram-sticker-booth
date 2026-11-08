"""Offline checks for optional --variations / --seed (prompt choices only)."""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sticker_booth.prompts import build_prompt, resolve_emojis, variation_extra  # noqa: E402


class VariationsTests(unittest.TestCase):
    def test_defaults_unchanged_without_flag(self):
        e = resolve_emojis("laugh")[0]
        self.assertEqual(build_prompt(e, "pixel"), build_prompt(e, "pixel", variations=False))
        self.assertNotIn("Pose tweak:", build_prompt(e, "pixel"))

    def test_seed_reproduces_prompt_choices(self):
        e = resolve_emojis("dragon")[0]
        a = build_prompt(e, "pixel", variations=True, seed=42)
        b = build_prompt(e, "pixel", variations=True, seed=42)
        c = build_prompt(e, "pixel", variations=True, seed=43)
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertIn("Pose tweak:", a)
        self.assertIn("jet-black hair", a)
        self.assertEqual(variation_extra(e, 7), variation_extra(e, 7))

    def test_variations_require_seed(self):
        e = resolve_emojis("laugh")[0]
        with self.assertRaises(ValueError):
            build_prompt(e, "pixel", variations=True, seed=None)

    def test_cli_seed_without_variations_exits(self):
        r = subprocess.run(
            [sys.executable, "-m", "sticker_booth.generate", "photos/x.jpg",
             "--seed", "1", "--dry-run"],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--seed requires --variations", r.stderr + r.stdout)

    def test_cli_invalid_seed(self):
        r = subprocess.run(
            [sys.executable, "-m", "sticker_booth.generate", "photos/x.jpg",
             "--variations", "--seed", "nope", "--dry-run"],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertNotEqual(r.returncode, 0)

    def test_cli_dry_run_seed_stable(self):
        photo = ROOT / "examples" / "sample_raw.png"
        cmd = [sys.executable, "-m", "sticker_booth.generate", str(photo),
               "--emojis", "laugh", "--style", "pixel", "--variations", "--seed", "99", "--dry-run"]
        a = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True)
        b = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True)
        self.assertEqual(a.stdout, b.stdout)
        self.assertIn("Pose tweak:", a.stdout)
        base = subprocess.run(
            [sys.executable, "-m", "sticker_booth.generate", str(photo),
             "--emojis", "laugh", "--style", "pixel", "--dry-run"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        )
        self.assertNotIn("Pose tweak:", base.stdout)


if __name__ == "__main__":
    unittest.main()
