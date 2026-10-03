"""Alpha bleeding: removes the dark fringe ("halo") engines show around sprites.

Fully transparent pixels usually store black. They're invisible, but when an engine
filters, scales, rotates or mipmaps the texture it blends them into the visible edge
pixels, which leaves a dark outline. Bleeding gives every fully transparent pixel the
color of the nearest visible pixels. Alpha and visible pixels are never changed.
"""
import os

import numpy as np
from PIL import Image


EXACT_PX = 4  # pixels around visible edges that get exact neighbor colors


def has_alpha(img):
    return "A" in img.getbands() or "transparency" in img.info


def bleed(img):
    """RGBA copy of img with fully transparent pixels colored like their surroundings.

    Images without transparency, or with nothing visible, are returned unchanged.
    """
    if not has_alpha(img):
        return img
    arr = np.asarray(img.convert("RGBA"), dtype=np.float32)
    filled = arr[..., 3] > 0
    if filled.all() or not filled.any():
        return img.convert("RGBA")
    rgb = arr[..., :3].copy()
    _exact_fill(rgb, filled)

    # Further away (only matters for mipmaps): a coarse fill that reaches every pixel
    if not filled.all():
        rgb = np.where(filled[..., None], rgb, _push_pull(rgb, filled))

    arr[..., :3] = np.rint(rgb)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def _exact_fill(rgb, filled):
    """Close to the edge (what filtering actually samples): give unfilled pixels the average
    of their filled neighbors, one ring at a time. Changes rgb and filled in place."""
    # Only the area within EXACT_PX of visible pixels can change, so work on that crop
    ys, xs = np.nonzero(filled)
    y0, y1 = max(ys.min() - EXACT_PX, 0), ys.max() + EXACT_PX + 1
    x0, x1 = max(xs.min() - EXACT_PX, 0), xs.max() + EXACT_PX + 1
    rgb, filled = rgb[y0:y1, x0:x1], filled[y0:y1, x0:x1]  # views: writes go to the originals
    for _ in range(EXACT_PX):
        # color * weight in channels 0-2, weight in channel 3, so one neighborhood sum does both
        weighted = np.empty(rgb.shape[:2] + (4,), np.float32)
        weighted[..., 3] = filled
        np.multiply(rgb, weighted[..., 3:], out=weighted[..., :3])
        sums = _box3(weighted)
        new = ~filled & (sums[..., 3] > 0)
        rgb[new] = sums[new, :3] / sums[new, 3:]
        filled |= new
        if filled.all():
            break


def _box3(a):
    """Sum over each pixel's 3x3 neighborhood (outside the image counts as 0)."""
    p = np.pad(a, [(1, 1), (1, 1)] + [(0, 0)] * (a.ndim - 2))
    rows = p[:-2] + p[1:-1]
    rows += p[2:]
    out = rows[:, :-2] + rows[:, 1:-1]
    out += rows[:, 2:]
    return out


def _push_pull(rgb, filled):
    """Color for every pixel: known pixels as-is, unknown ones from a half-size version, recursively."""
    h, w = filled.shape
    if h == 1 and w == 1:
        return rgb
    weight = filled.astype(np.float32)
    color = rgb * weight[..., None]
    pad = [(0, h % 2), (0, w % 2)]
    weight = np.pad(weight, pad)
    color = np.pad(color, pad + [(0, 0)])
    h2, w2 = weight.shape[0] // 2, weight.shape[1] // 2
    weight2 = weight.reshape(h2, 2, w2, 2).sum(axis=(1, 3))
    color2 = color.reshape(h2, 2, w2, 2, 3).sum(axis=(1, 3))
    known2 = weight2 > 0
    color2[known2] /= weight2[known2, None]
    coarse = _push_pull(color2, known2)
    up = np.repeat(np.repeat(coarse, 2, axis=0), 2, axis=1)[:h, :w]
    return np.where(filled[..., None], rgb, up)


def fix_halos(paths, overwrite=False, log=print):
    """Bleed each image. Saves into a halo_fixed folder next to it, or over it with overwrite.

    Images without transparency are skipped.
    Returns {"fixed": n, "skipped": n, "failed": n, "output_dir": folder of the first result or None}.
    """
    counts = {"fixed": 0, "skipped": 0, "failed": 0, "output_dir": None}
    for src in paths:
        folder = os.path.dirname(src)
        if os.path.basename(folder) == "halo_fixed":
            counts["skipped"] += 1  # an earlier run's output
            continue
        try:
            with Image.open(src) as img:
                img.load()
                fmt = img.format
                if not has_alpha(img):
                    log(f"– {src} (no transparency)")
                    counts["skipped"] += 1
                    continue
                fixed = bleed(img)
            if overwrite:
                dst = src
            else:
                os.makedirs(os.path.join(folder, "halo_fixed"), exist_ok=True)
                dst = os.path.join(folder, "halo_fixed", os.path.basename(src))
            fixed.save(dst, fmt)
            counts["fixed"] += 1
            counts["output_dir"] = counts["output_dir"] or os.path.dirname(dst)
            log(f"✔ {dst}")
        except Exception as e:
            counts["failed"] += 1
            log(f"✖ Failed: {src} ({e})")
    log(f"Fixed: {counts['fixed']}, skipped: {counts['skipped']}, failed: {counts['failed']}")
    return counts
