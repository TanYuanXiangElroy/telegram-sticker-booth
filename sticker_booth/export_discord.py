"""Resize stickers to Discord guild sticker PNG limits (not a pack ZIP installer).

  python -m sticker_booth.export_discord examples/stickers --out out/discord

Discord custom stickers: exactly 320x320 PNG, <= 512 KB (server Boost required to upload).
See docs/PLATFORM_EXPORTS.md. This does not upload to Discord.
"""
import argparse
from pathlib import Path

from PIL import Image

from .env import utf8_console

SIZE = 320
MAX_BYTES = 512 * 1024
README = """Discord custom stickers (honest export)
======================================

Files are exactly 320x320 PNG, <= 512 KB.

Upload path: Server Settings -> Stickers (requires Server Boost). Discord does not
install a portable pack from this folder/ZIP automatically.
  https://support.discord.com/hc/en-us/articles/4402687377815
  https://docs.discord.com/developers/resources/sticker

This export is image conversion only.
"""


def to_discord_png(src: Path, dest: Path):
    im = Image.open(src).convert("RGBA")
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    t = im.copy()
    t.thumbnail((SIZE, SIZE), Image.LANCZOS)
    canvas.paste(t, ((SIZE - t.width) // 2, (SIZE - t.height) // 2), t)
    dest.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dest, "PNG", optimize=True)
    n = dest.stat().st_size
    if n > MAX_BYTES:
        raise ValueError(f"{dest.name}: {n} bytes > {MAX_BYTES}")
    return n


def export_dir(src: Path, out: Path):
    src, out = Path(src), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "README_DISCORD.txt").write_text(README, encoding="utf-8")
    pngs = sorted(src.glob("*.png"))
    if not pngs:
        raise FileNotFoundError(f"no .png stickers in {src}")
    return [(png.stem + ".png", to_discord_png(png, out / f"{png.stem}.png")) for png in pngs]


def main(argv=None):
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", help="folder of PNG stickers")
    ap.add_argument("--out", default="out/discord")
    a = ap.parse_args(argv)
    try:
        rows = export_dir(Path(a.src), Path(a.out))
    except (FileNotFoundError, ValueError) as e:
        raise SystemExit(str(e))
    for name, n in rows:
        print(f"  {name} {n} bytes")
    print(f"{len(rows)} file(s) -> {a.out} (Discord image conversion only)")


if __name__ == "__main__":
    main()
