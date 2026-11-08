"""Export approved stickers to a PNG+WebP ZIP (no Telegram bot token required).

  python -m sticker_booth.export_zip examples/stickers --out stickers_export.zip
  python -m sticker_booth.export_zip sessions/me/approved --out me_approved.zip

The archive contains only selected sticker files:
  png/<name>.png
  webp/<name>.webp
  README_IMPORT_INSTRUCTIONS.txt

Telegram does not import this ZIP as a pack automatically. Use @Stickers manually
or this project's bot upload flow. Never put photos, .env, or unrelated files in the ZIP.
"""
import argparse
import json
import zipfile
from pathlib import Path

from PIL import Image

from .env import utf8_console

IMPORT_README = """Telegram sticker import (honest steps)
=====================================

This ZIP is a file bundle for backup / hand import. Telegram does NOT open a ZIP
and install a sticker pack in one step (verified against common Bot API + @Stickers
workflows: packs are created sticker-by-sticker).

Option A — Official @Stickers bot (manual)
  1. Unzip this archive.
  2. Open Telegram and chat with @Stickers.
  3. /newpack (or /addsticker) and follow the prompts.
  4. Upload each file from the webp/ folder (preferred) or png/ folder.
  5. Assign the matching emoji (see filenames; e.g. laugh.webp -> 😂 if that was your pack).

Option B — This project's bot CLI (needs your own bot token; not in this ZIP)
  python -m sticker_booth.telegram_pack <folder> --user-id <YOUR_ID> --name <short> --title "<Title>"

Static sticker rules (Telegram):
  - PNG or WEBP
  - one side exactly 512 px (these exports are 512x512)
  - each file <= 512 KB

This archive includes only sticker images under png/ and webp/, plus this README.
It never includes photos, API keys, or session files.
"""


def collect_pairs(src: Path, names=None):
    """Find matching .png/.webp pairs under src (flat or png/+webp/ layout).

    names: optional iterable of basenames without extension; default = all png stems that have webp.
    """
    src = Path(src)
    if not src.is_dir():
        raise FileNotFoundError(f"not a directory: {src}")

    # Prefer pack.json order when present (sibling or inside src)
    pack = src / "pack.json"
    ordered = []
    if pack.is_file():
        data = json.loads(pack.read_text(encoding="utf-8"))
        for item in data.get("stickers", []):
            stem = Path(item.get("png") or item.get("webp") or "").stem
            if stem:
                ordered.append(stem)

    png_dir = src / "png" if (src / "png").is_dir() else src
    webp_dir = src / "webp" if (src / "webp").is_dir() else src

    if names is not None:
        stems = list(names)
    elif ordered:
        stems = ordered
    else:
        stems = sorted({p.stem for p in png_dir.glob("*.png")})

    pairs, missing = [], []
    for stem in stems:
        # booth approved files look like 11_error404.png — keep full stem
        png = png_dir / f"{stem}.png"
        webp = webp_dir / f"{stem}.webp"
        if not png.is_file() or not webp.is_file():
            missing.append(stem)
            continue
        pairs.append((stem, png, webp))
    if missing:
        raise FileNotFoundError(
            f"missing png/webp pair(s) for: {', '.join(missing)} (looked in {png_dir} and {webp_dir})"
        )
    if not pairs:
        raise FileNotFoundError(f"no stickers found in {src}")
    return pairs


def check_sticker(path: Path, expect_size=512):
    with Image.open(path) as im:
        size, mode = im.size, im.mode
    if expect_size not in size:
        raise ValueError(f"{path.name}: expected one side {expect_size}px, got {size}")
    return size, mode


def write_zip(pairs, out_zip: Path):
    out_zip = Path(out_zip)
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README_IMPORT_INSTRUCTIONS.txt", IMPORT_README)
        for stem, png, webp in pairs:
            check_sticker(png)
            check_sticker(webp)
            zf.write(png, f"png/{stem}.png")
            zf.write(webp, f"webp/{stem}.webp")
    return out_zip


def main(argv=None):
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", help="folder of stickers (flat png+webp, or with pack.json / png|webp subdirs)")
    ap.add_argument("--out", default="stickers_export.zip", help="output zip path (default: stickers_export.zip)")
    ap.add_argument("--only", default="", help="optional comma list of basenames, e.g. laugh,cry")
    a = ap.parse_args(argv)

    names = [x.strip() for x in a.only.split(",") if x.strip()] or None
    try:
        pairs = collect_pairs(Path(a.src), names=names)
        path = write_zip(pairs, Path(a.out))
    except (FileNotFoundError, ValueError) as e:
        raise SystemExit(str(e))
    print(f"Wrote {path} with {len(pairs)} sticker(s) (png/ + webp/ + README_IMPORT_INSTRUCTIONS.txt)")
    print("Note: Telegram does not auto-install packs from this ZIP; see the README inside.")


if __name__ == "__main__":
    main()
