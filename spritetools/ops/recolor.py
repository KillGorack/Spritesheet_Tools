"""Recoloring: swapping exact colors (pixel art), or shifting a range of hues (shaded art
such as renders, where one "color" is thousands of slightly different pixels).

Alpha is never changed.
"""
import os

import numpy as np
from PIL import Image

FEATHER_DEG = 15          # hue range edges blend out over this many degrees
GREY_SATURATION = 0.08    # pixels less saturated than this are greys and aren't shifted


def hex_to_rgb(text):
    text = text.lstrip("#")
    return tuple(int(text[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb[:3])


# ----- exact colors ---------------------------------------------------------

def palette(images):
    """The visible colors in the images, most used first, as [((r, g, b), pixel count)]."""
    counts = {}
    for img in images:
        arr = np.asarray(img.convert("RGBA"))
        rgb = arr[arr[..., 3] > 0][:, :3]
        if not len(rgb):
            continue
        packed = (rgb[:, 0].astype(np.uint32) << 16) | (rgb[:, 1].astype(np.uint32) << 8) | rgb[:, 2]
        values, n = np.unique(packed, return_counts=True)
        for v, c in zip(values.tolist(), n.tolist()):
            counts[v] = counts.get(v, 0) + c
    ordered = sorted(counts.items(), key=lambda item: -item[1])
    return [((v >> 16 & 255, v >> 8 & 255, v & 255), c) for v, c in ordered]


def swap_colors(img, mapping):
    """img with each color in mapping {(r, g, b): (r, g, b)} replaced, alpha kept."""
    arr = np.asarray(img.convert("RGBA")).copy()
    if mapping:
        rgb = arr[..., :3]
        packed = (rgb[..., 0].astype(np.uint32) << 16) | (rgb[..., 1].astype(np.uint32) << 8) | rgb[..., 2]
        out = rgb.copy()
        for src, dst in mapping.items():
            out[packed == ((src[0] << 16) | (src[1] << 8) | src[2])] = dst
        arr[..., :3] = out
    return Image.fromarray(arr, "RGBA")


# ----- hue ranges -----------------------------------------------------------

def rgb_to_hsv(rgb):
    """rgb floats 0-1, shape (..., 3) -> hue in degrees 0-360, saturation and value 0-1."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx, mn = rgb.max(axis=-1), rgb.min(axis=-1)
    delta = mx - mn
    safe = np.where(delta == 0, 1, delta)
    hue = np.where(mx == r, (g - b) / safe % 6, np.where(mx == g, (b - r) / safe + 2, (r - g) / safe + 4)) * 60
    hue = np.where(delta == 0, 0, hue)
    saturation = np.where(mx == 0, 0, delta / np.where(mx == 0, 1, mx))
    return hue, saturation, mx


def hsv_to_rgb(hue, saturation, value):
    """The inverse of rgb_to_hsv."""
    h = (hue % 360) / 60
    c = value * saturation
    x = c * (1 - np.abs(h % 2 - 1))
    zero = np.zeros_like(c)
    sector = np.floor(h).astype(int) % 6
    r = np.choose(sector, [c, x, zero, zero, x, c])
    g = np.choose(sector, [x, c, c, x, zero, zero])
    b = np.choose(sector, [zero, zero, x, c, c, x])
    m = value - c
    return np.stack([r + m, g + m, b + m], axis=-1)


def hue_distance(a, b):
    """Degrees between two hues, the short way around the circle."""
    d = np.abs(a - b) % 360
    return np.minimum(d, 360 - d)


def hue_of(rgb):
    """Hue in degrees of one (r, g, b) color."""
    hue, _, _ = rgb_to_hsv(np.array(rgb[:3], dtype=np.float64) / 255)
    return float(hue)


def shift_hue(img, hue, spread, new_hue, saturation=0, brightness=0):
    """Recolor the pixels whose hue is within `spread` degrees of `hue`.

    Their hue moves by (new_hue - hue), so the shading's small hue differences are kept,
    and saturation and brightness change by the given percentages (-100 to 100). The range
    fades out over FEATHER_DEG past its edges, and greys aren't touched.
    """
    arr = np.asarray(img.convert("RGBA")).astype(np.float64)
    rgb = arr[..., :3] / 255
    h, s, v = rgb_to_hsv(rgb)
    weight = np.clip((spread + FEATHER_DEG - hue_distance(h, hue)) / FEATHER_DEG, 0, 1)
    weight *= np.clip((s - GREY_SATURATION) / GREY_SATURATION, 0, 1)
    new = hsv_to_rgb(h + (new_hue - hue),
                     np.clip(s * (1 + saturation / 100), 0, 1),
                     np.clip(v * (1 + brightness / 100), 0, 1))
    rgb = rgb + (new - rgb) * weight[..., None]
    arr[..., :3] = np.rint(rgb * 255)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


# ----- files ----------------------------------------------------------------

def recolor(img, cfg):
    """img recolored with the Recolor settings in cfg (a Config)."""
    if cfg.recolor_mode == "swap":
        return swap_colors(img, {hex_to_rgb(a): hex_to_rgb(b) for a, b in cfg.recolor_map.items()})
    return shift_hue(img, cfg.recolor_hue, cfg.recolor_range, cfg.recolor_new_hue,
                     cfg.recolor_saturation, cfg.recolor_brightness)


def recolor_files(paths, cfg, log=print):
    """Recolor each image into a folder named cfg.recolor_folder next to it, keeping its name
    and format. Files already in such a folder are skipped.
    Returns {"recolored": n, "skipped": n, "failed": n, "output_dir": first output folder or None}.
    """
    counts = {"recolored": 0, "skipped": 0, "failed": 0, "output_dir": None}
    for src in paths:
        folder = os.path.dirname(src)
        if os.path.basename(folder) == cfg.recolor_folder:
            counts["skipped"] += 1  # an earlier run's output
            continue
        try:
            with Image.open(src) as img:
                img.load()
                fmt = img.format
                out = recolor(img, cfg)
            os.makedirs(os.path.join(folder, cfg.recolor_folder), exist_ok=True)
            dst = os.path.join(folder, cfg.recolor_folder, os.path.basename(src))
            if fmt == "JPEG":
                out = out.convert("RGB")
            out.save(dst, fmt)
            counts["recolored"] += 1
            counts["output_dir"] = counts["output_dir"] or os.path.dirname(dst)
            log(f"✔ {dst}")
        except Exception as e:
            counts["failed"] += 1
            log(f"✖ Failed: {src} ({e})")
    log(f"Recolored: {counts['recolored']}, skipped: {counts['skipped']}, failed: {counts['failed']}")
    return counts
