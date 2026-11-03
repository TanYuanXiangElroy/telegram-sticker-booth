"""Photo(s) x emoji scenes -> Gemini image edit (green screen) -> 512px Telegram stickers.

  python -m sticker_booth.generate <photo_or_folder> [--style cartoon|cyberpunk|pixel]
         [--emojis classic|dev|moods|reactions|all|laugh,cry|😂,👍] [--out out] [--dry-run] [--model gemini-3.1-flash-lite-image]
  python -m sticker_booth.generate --from-raw raw.png --emojis laugh --out out   # cleanup only, no API call

Needs GEMINI_API_KEY (in .env or the environment) with billing on; the free tier has 0 image quota.
Output: <out>/<photo_stem>/{raw/<name>.png, <name>.png, <name>.webp, pack.json, sheet.png}
Re-running the same command skips stickers whose raw image already exists.
"""
import argparse
import base64
import io
import json
import os
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from PIL import Image, ImageOps

from . import postprocess
from .env import load_env, utf8_console
from .prompts import EMOJIS, STYLES, build_prompt, resolve_emojis

try:  # optional HEIC support: pip install pillow-heif
    import pillow_heif
    pillow_heif.register_heif_opener()
    EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
except ImportError:
    EXTS = {".jpg", ".jpeg", ".png", ".webp"}

MODEL = "gemini-3.1-flash-lite-image"
COST_PER_IMAGE = 0.034  # USD per image at 1K, check current Gemini pricing
API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
WORKERS, MAX_TRIES = 2, 5


class StopRun(Exception):
    """Fatal for the whole run (no credits, no quota, bad key)."""


stop = threading.Event()
lock = threading.Lock()
done = {"ok": 0, "fail": 0}


def photo_jpeg(path, long_side=1024):
    """Load a photo, apply EXIF rotation, shrink to 1024px and return JPEG bytes."""
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    im.thumbnail((long_side, long_side), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=90)
    return buf.getvalue()


def gemini(jpeg, prompt, model=MODEL):
    """Send photo + prompt to Gemini, return the generated image bytes. Retries transient errors."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise StopRun("GEMINI_API_KEY is not set. Copy .env.example to .env and fill it in.")
    body = {"contents": [{"parts": [
                {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(jpeg).decode()}},
                {"text": prompt}]}],
            "generationConfig": {"responseModalities": ["IMAGE"]}}
    for attempt in range(1, MAX_TRIES + 1):
        if stop.is_set():
            raise StopRun("stopped")
        try:
            r = requests.post(API.format(model=model), json=body, timeout=180,
                              headers={"x-goog-api-key": key})  # key goes in a header, never printed
        except requests.RequestException as e:
            status, msg = None, str(e)
        else:
            if r.ok:
                for c in r.json().get("candidates", []):
                    for p in c.get("content", {}).get("parts", []):
                        d = p.get("inlineData") or p.get("inline_data")
                        if d:
                            return base64.b64decode(d["data"])
                raise RuntimeError(f"no image in response: {r.text[:300]}")
            status = r.status_code
            try:
                msg = r.json().get("error", {}).get("message", r.text)
            except ValueError:
                msg = r.text
        low = msg.lower()
        if status == 402 or "prepayment" in low or ("credits" in low and "deplet" in low):
            raise StopRun("Gemini says your prepaid credits are used up (HTTP 402). Top up in AI Studio "
                          "(https://ai.studio/projects) and run again.")
        if status == 429 and ("limit: 0" in low or ("free_tier" in low and "limit" in low and " 0" in low)):
            raise StopRun("This key is on the free tier, which allows 0 image generations (HTTP 429). "
                          "Turn on billing for the key's project, then run again.")
        if status in (400, 401, 403, 404):
            raise StopRun(f"Gemini rejected the request (HTTP {status}): {msg[:200]}")
        if attempt == MAX_TRIES:
            raise RuntimeError(f"gave up after {MAX_TRIES} tries (HTTP {status}): {msg[:200]}")
        wait = min(60, 2 ** attempt) + random.random()
        print(f"  ...HTTP {status}, retrying in {wait:.0f}s ({attempt}/{MAX_TRIES - 1})", flush=True)
        time.sleep(wait)


def post(raw_path, out_dir, name):
    im = postprocess.process(raw_path)
    postprocess.save_sticker(im, Path(out_dir) / name)
    return im


def run_job(model, photo, jpeg, out_dir, emoji, style, extra, total):
    name = EMOJIS[emoji][0]
    raw = out_dir / "raw" / f"{name}.png"
    try:
        if not raw.exists():  # resume: skip already-generated raws
            raw.write_bytes(gemini(jpeg, build_prompt(emoji, style, extra), model))
        post(raw, out_dir, name)
        ok = True
    except StopRun:
        stop.set()
        raise
    except Exception as e:
        ok = False
        print(f"  x {photo.name} {emoji} {name}: {e}", flush=True)
    with lock:
        done["ok" if ok else "fail"] += 1
        if ok:
            print(f"  [{done['ok'] + done['fail']}/{total}] ok {photo.stem}/{name}.webp {emoji}", flush=True)
    return ok


def finish_photo(out_dir, emojis, first=None):
    """Write pack.json (emoji per file, read by sticker_booth.telegram_pack) and sheet.png."""
    pack, items = [], []
    for e in emojis:
        name = EMOJIS[e][0]
        png = out_dir / f"{name}.png"
        if png.exists():
            pack.append({"emoji": e, "png": png.name, "webp": f"{name}.webp"})
            items.append((name, Image.open(png)))
    (out_dir / "pack.json").write_text(json.dumps({"stickers": pack}, ensure_ascii=False, indent=2),
                                       encoding="utf-8")
    if items:
        postprocess.contact_sheet(items, out_dir / "sheet.png", first=first)
        print(f"  sheet: {out_dir / 'sheet.png'}")


def main():
    utf8_console()
    load_env()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", nargs="?", help="photo or folder of photos")
    ap.add_argument("--style", default="cartoon", choices=sorted(STYLES))
    ap.add_argument("--emojis", default="classic",
                    help="pack (classic, dev, moods, reactions), all, or a comma list of emojis/names, e.g. laugh,cry")
    ap.add_argument("--extra", default="", help="extra sentence appended to every prompt")
    ap.add_argument("--out", default="out")
    ap.add_argument("--dry-run", action="store_true", help="print prompts and cost, call nothing")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--from-raw", metavar="RAW", help="skip Gemini: clean up this green-screen image")
    a = ap.parse_args()

    try:
        emojis = resolve_emojis(a.emojis)
    except ValueError as e:
        sys.exit(str(e))

    if a.from_raw:  # cleanup + sheet only, no API call
        raw = Path(a.from_raw)
        out_dir = Path(a.out) / raw.stem
        out_dir.mkdir(parents=True, exist_ok=True)
        e = emojis[0]
        post(raw, out_dir, EMOJIS[e][0])
        print(f"  ok {out_dir / EMOJIS[e][0]}.png/.webp")
        finish_photo(out_dir, [e], first=("raw", Image.open(raw)))
        return

    if not a.src:
        ap.error("give a photo or folder (or --from-raw)")
    src = Path(a.src)
    photos = sorted(p for p in src.iterdir() if p.suffix.lower() in EXTS) if src.is_dir() else [src]
    if not photos:
        sys.exit(f"No photos ({', '.join(sorted(EXTS))}) found in {src}")
    total = len(photos) * len(emojis)
    print(f"{len(photos)} photo(s) x {len(emojis)} emoji = {total} stickers, style '{a.style}', model {a.model}")
    print(f"Estimated cost: ~${total * COST_PER_IMAGE:.2f} (at ${COST_PER_IMAGE}/image)")

    if a.dry_run:
        for p in photos:
            for e in emojis:
                print(f"\n--- {p.name} {e} -> {a.out}/{p.stem}/{EMOJIS[e][0]}.webp\n{build_prompt(e, a.style, a.extra)}")
        return

    try:
        with ThreadPoolExecutor(WORKERS) as pool:
            for p in photos:
                out_dir = Path(a.out) / p.stem
                (out_dir / "raw").mkdir(parents=True, exist_ok=True)
                jpeg = photo_jpeg(p)
                futs = [pool.submit(run_job, a.model, p, jpeg, out_dir, e, a.style, a.extra, total) for e in emojis]
                for f in futs:
                    f.result()  # re-raises StopRun
                finish_photo(out_dir, emojis, first=("photo", ImageOps.exif_transpose(Image.open(p))))
    except StopRun as e:
        stop.set()
        sys.stdout.flush()
        print(f"\nStopped: {e}\nDone so far: {done['ok']} ok, {done['fail']} failed. "
              f"Re-run the same command later; finished stickers are skipped.", file=sys.stderr)
        sys.exit(2)
    print(f"\nAll done: {done['ok']} ok, {done['fail']} failed -> {a.out}/")


if __name__ == "__main__":
    main()
