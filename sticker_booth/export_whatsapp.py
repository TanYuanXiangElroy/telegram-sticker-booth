"""Recompress stickers to WhatsApp static WebP limits (not a pack installer).

  python -m sticker_booth.export_whatsapp examples/stickers --out out/whatsapp

WhatsApp static stickers: 512x512 WebP, <= 100 KB each (see docs/PLATFORM_EXPORTS.md).
This writes files + README_WHATSAPP.txt. It does NOT install a WhatsApp sticker pack;
use WhatsApp's sticker creator / a sticker app per Meta's docs.
"""
import argparse
import io
from pathlib import Path

from PIL import Image

from .env import utf8_console

SIZE = 512
MAX_BYTES = 100 * 1024
README = """WhatsApp static stickers (honest export)
=======================================

Files in this folder are 512x512 WebP aiming for <= 100 KB each.

WhatsApp does NOT install a pack by opening a random ZIP from this project.
Use WhatsApp's in-app sticker tools or a sticker app that follows:
  https://faq.whatsapp.com/1056840314992666/
  https://github.com/WhatsApp/stickers

This export is image conversion only.
"""


def to_whatsapp_webp(src: Path, dest: Path, max_bytes=MAX_BYTES):
    im = Image.open(src).convert("RGBA")
    if im.size != (SIZE, SIZE):
        # centre on 512 canvas if needed
        canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        t = im.copy()
        t.thumbnail((SIZE, SIZE), Image.LANCZOS)
        canvas.paste(t, ((SIZE - t.width) // 2, (SIZE - t.height) // 2))
        im = canvas
    best = None
    for q in range(90, 9, -5):
        buf = io.BytesIO()
        im.save(buf, "WEBP", quality=q, method=6)
        data = buf.getvalue()
        best = data
        if len(data) <= max_bytes:
            break
    if best is None or len(best) > max_bytes:
        raise ValueError(f"{src.name}: could not fit under {max_bytes} bytes (got {len(best) if best else 0})")
    dest.write_bytes(best)
    return len(best)


def export_dir(src: Path, out: Path):
    src, out = Path(src), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "README_WHATSAPP.txt").write_text(README, encoding="utf-8")
    pngs = sorted(src.glob("*.png"))
    if not pngs:
        raise FileNotFoundError(f"no .png stickers in {src}")
    written = []
    for png in pngs:
        dest = out / f"{png.stem}.webp"
        n = to_whatsapp_webp(png, dest)
        written.append((dest.name, n))
    return written


def main(argv=None):
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", help="folder of 512 PNG stickers")
    ap.add_argument("--out", default="out/whatsapp", help="output folder")
    a = ap.parse_args(argv)
    try:
        rows = export_dir(Path(a.src), Path(a.out))
    except (FileNotFoundError, ValueError) as e:
        raise SystemExit(str(e))
    for name, n in rows:
        print(f"  {name} {n} bytes")
    print(f"{len(rows)} file(s) -> {a.out} (WhatsApp image conversion only; not pack install)")


if __name__ == "__main__":
    main()
