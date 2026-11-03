"""Green-screen (#00FF00) model output -> Telegram static sticker (512x512 PNG + WEBP).

Usage:
  python -m sticker_booth.postprocess in.png out/laugh [--stroke 10] [--shadow] [--keep-holes] [--lo 40 --hi 170]
  -> out/laugh.png and out/laugh.webp

Steps: chroma key (soft tolerance) -> keep largest blob, fill its holes -> un-mix + despill the
edge fringe -> crop and scale to fit 512 -> white stroke (+ optional shadow) -> PNG/WEBP <= 512 KB.
"""
import argparse
import io
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

KEY = np.array([0, 255, 0], np.float32)
SIZE = 512


def chroma_key(rgb, lo=40, hi=170):
    """Alpha from 'greenness' = G - max(R, B). <= lo is opaque, >= hi is transparent, linear between."""
    g = rgb[..., 1] - np.maximum(rgb[..., 0], rgb[..., 2])
    return np.clip((hi - g) / (hi - lo), 0, 1)


def keep_largest(alpha, keep_holes=False, edge=3, pure=None, min_hole=12):
    """Keep only the biggest blob (drops stray specks). Unless keep_holes, everything inside the outer
    contour becomes fully opaque, which protects green clothing etc. inside the white die-cut border;
    soft alpha stays only in a thin band along the outer edge.

    pure: optional bool mask of near-pure key green (alpha == 0 under the key, i.e. G - max(R, B) >= hi). Enclosed patches of it
    (e.g. background showing between arms and head) are punched back out, with a soft key edge, so only
    real green props/clothing (less saturated than the key) stay protected."""
    lab, n = ndi.label(alpha > 0.5)
    if n == 0:
        raise ValueError("no subject found (is the background really #00FF00?)")
    sizes = ndi.sum(np.ones_like(lab), lab, range(1, n + 1))
    blob = lab == (1 + int(np.argmax(sizes)))
    solid = blob if keep_holes else ndi.binary_fill_holes(blob)
    a = alpha * ndi.binary_dilation(solid, iterations=2)  # keep soft edge pixels next to the blob
    if keep_holes:
        return a
    core = ndi.binary_erosion(solid, iterations=edge)
    a[core] = 1.0
    if pure is not None:
        holes = solid & ~blob
        gap = holes & pure
        hl, hn = ndi.label(gap)
        if hn:
            hs = ndi.sum(np.ones_like(hl), hl, range(1, hn + 1))
            gap = np.isin(hl, 1 + np.flatnonzero(hs >= min_hole))  # ignore single noisy pixels
            ring = ndi.binary_dilation(gap, iterations=edge) & ~gap & core
            a[gap] = 0.0
            a[ring] = alpha[ring]  # soft key edge around each punched-out gap
    return a


def clean_edges(rgb, a, band=3):
    """Remove green fringe: un-mix the key colour from semi-transparent pixels, then despill near edges."""
    out = rgb.copy()
    semi = (a > 0.02) & (a < 0.98)
    aa = a[semi][:, None]
    out[semi] = (rgb[semi] - (1 - aa) * KEY) / aa  # C = a*F + (1-a)*K  ->  F
    edge = ndi.binary_dilation(a < 0.98, iterations=band) & (a > 0)
    mx = np.maximum(out[..., 0], out[..., 2])
    spill = edge & (out[..., 1] > mx)
    out[..., 1][spill] = mx[spill]  # G := max(R, B), only in the edge band
    return np.clip(out, 0, 255)


def stroke_and_shadow(rgba, width, shadow):
    a = rgba[..., 3] / 255.0
    dist = ndi.distance_transform_edt(a < 0.5)
    sa = np.clip(width + 0.5 - dist, 0, 1) if width else np.zeros_like(a)
    base_a = np.maximum(sa, a)
    out = np.zeros_like(rgba, dtype=np.float32)
    out[..., :3] = 255
    out[..., 3] = base_a  # white stroke layer
    if shadow:
        sh = ndi.shift(ndi.gaussian_filter(base_a, 4), (5, 4), order=1) * 0.45
        out_a = base_a + sh * (1 - base_a)
        out[..., :3] = (255 * base_a[..., None]) / np.maximum(out_a, 1e-6)[..., None]
        out[..., 3] = out_a
    fa = a[..., None]
    ba = out[..., 3:4]
    oa = fa + ba * (1 - fa)  # subject composited over stroke/shadow
    out[..., :3] = (rgba[..., :3] * fa + out[..., :3] * ba * (1 - fa)) / np.maximum(oa, 1e-6)
    out[..., 3:4] = oa
    out[..., 3] *= 255
    return np.clip(out, 0, 255).astype(np.uint8)


def to_512(rgba_u8, margin):
    """Crop to the subject, scale evenly (no squashing) to fit 512 minus margin, centre on 512x512."""
    im = Image.fromarray(rgba_u8, "RGBA")
    im = im.crop(im.getbbox())
    r = (SIZE - 2 * margin) / max(im.size)
    im = im.resize((max(1, round(im.width * r)), max(1, round(im.height * r))), Image.LANCZOS)
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    canvas.paste(im, ((SIZE - im.width) // 2, (SIZE - im.height) // 2))
    return canvas


def process(src, stroke=10, shadow=False, keep_holes=False, lo=40, hi=170):
    """src: path or PIL image of the green-screen generation. Returns a 512x512 RGBA PIL image."""
    im = src if isinstance(src, Image.Image) else Image.open(src)
    rgb = np.asarray(im.convert("RGB")).astype(np.float32)
    alpha = chroma_key(rgb, lo, hi)
    a = keep_largest(alpha, keep_holes=keep_holes, pure=alpha <= 0.0)
    rgb = clean_edges(rgb, a)
    rgba = np.dstack([rgb, a * 255]).astype(np.uint8)
    rgba[a == 0, :3] = 0
    margin = stroke + (10 if shadow else 2)
    small = np.asarray(to_512(rgba, margin))  # scale first so the stroke width is in sticker pixels
    return Image.fromarray(stroke_and_shadow(small.astype(np.float32), stroke, shadow), "RGBA")


def save_webp(im, path, limit=512 * 1024):
    """Lossless if it fits under Telegram's 512 KB, otherwise step down the quality."""
    for q in (100, 90, 80, 70, 60):
        buf = io.BytesIO()
        im.save(buf, "WEBP", lossless=(q == 100), quality=q, method=6)
        if buf.tell() <= limit:
            break
    Path(path).write_bytes(buf.getvalue())
    return buf.tell()


def save_sticker(im, out_base):
    """Write <out_base>.png and <out_base>.webp. Returns (png_path, webp_path)."""
    out_base = Path(out_base)
    out_base.parent.mkdir(parents=True, exist_ok=True)
    png, webp = out_base.with_name(out_base.name + ".png"), out_base.with_name(out_base.name + ".webp")
    im.save(png, optimize=True)
    save_webp(im, webp)
    return png, webp


def contact_sheet(items, path=None, cols=4, tile=256, pad=16, label_h=28, first=None):
    """items: [(label, image)]; first: optional (label, image) tile shown first.
    Tiles are fitted with thumbnail(), so aspect ratios are kept (no squashing)."""
    tiles = ([first] if first else []) + list(items)
    cols = min(cols, len(tiles))
    rows = (len(tiles) + cols - 1) // cols
    W = cols * (tile + pad) + pad
    H = rows * (tile + label_h + pad) + pad
    sheet = Image.new("RGB", (W, H), (236, 238, 242))
    draw = ImageDraw.Draw(sheet)
    for i, (label, im) in enumerate(tiles):
        x = pad + (i % cols) * (tile + pad)
        y = pad + (i // cols) * (tile + label_h + pad)
        cell = Image.new("RGBA", (tile, tile), (205, 208, 214, 255))
        t = im.convert("RGBA").copy()
        t.thumbnail((tile, tile), Image.LANCZOS)
        cell.alpha_composite(t, ((tile - t.width) // 2, (tile - t.height) // 2))
        sheet.paste(cell.convert("RGB"), (x, y))
        draw.text((x + 4, y + tile + 6), label, fill=(30, 30, 30))
    if path:
        sheet.save(path)
    return sheet


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("src", help="green-screen image from Gemini")
    p.add_argument("out", help="output base path without extension, e.g. out/laugh")
    p.add_argument("--stroke", type=int, default=10, help="white border width in px (default 10)")
    p.add_argument("--shadow", action="store_true", help="add a soft drop shadow")
    p.add_argument("--keep-holes", action="store_true", help="let green inside the subject become transparent")
    p.add_argument("--lo", type=int, default=40, help="greenness at or below this stays opaque")
    p.add_argument("--hi", type=int, default=170, help="greenness at or above this becomes transparent")
    a = p.parse_args()
    im = process(a.src, a.stroke, a.shadow, a.keep_holes, a.lo, a.hi)
    png, webp = save_sticker(im, a.out)
    print(f"{png} {im.size} {im.mode} {os.path.getsize(png) // 1024} KB | {webp} {os.path.getsize(webp) // 1024} KB")


if __name__ == "__main__":
    main()
