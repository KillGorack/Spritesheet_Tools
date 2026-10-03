import math
import os

from PIL import Image

from .alpha import bleed
from .util import base_name, unique_path


def dissect(path, frame_size, start_index=0, fix_halos=False, log=print):
    """Cut a spritesheet into frame_###.png files in a 'sources' folder next to it.

    Partial frames at the right/bottom edge are skipped. fix_halos bleeds each frame (see alpha.py).
    Returns (output_dir, frame_count).
    """
    output_dir = os.path.join(os.path.dirname(path), "sources")
    os.makedirs(output_dir, exist_ok=True)
    frame_index = start_index
    with Image.open(path) as img:
        img_width, img_height = img.size
        for y in range(0, img_height - frame_size + 1, frame_size):
            for x in range(0, img_width - frame_size + 1, frame_size):
                frame = img.crop((x, y, x + frame_size, y + frame_size))
                if fix_halos:
                    frame = bleed(frame)
                frame.save(os.path.join(output_dir, f"frame_{frame_index:03}.png"))
                frame_index += 1
    count = frame_index - start_index
    log(f"Extracted {count} frames to:")
    log(output_dir)
    return output_dir, count


def resize(path, base_frame_size, target_sizes, resample=Image.Resampling.LANCZOS, fix_halos=False, log=print):
    """Rescale a sheet of base_frame_size frames so each frame becomes each target size.

    fix_halos bleeds each output (see alpha.py).
    Outputs <name>_<size>.png next to the input. Returns the output paths.
    """
    directory = os.path.dirname(path)
    name = base_name(path)
    outputs = []
    with Image.open(path) as img:
        width, height = img.size
        if width % base_frame_size or height % base_frame_size:
            log(f"Warning: image dimensions are not cleanly divisible by {base_frame_size}.")
        for size in target_sizes:
            scale = size / base_frame_size
            new_width = int(width * scale)
            new_height = int(height * scale)
            out_name = f"{name}_{size:03d}.png"
            out_path = os.path.join(directory, out_name)
            resized = img.resize((new_width, new_height), resample)
            if fix_halos:
                resized = bleed(resized)
            resized.save(out_path, format="PNG", optimize=True)
            log(f"Saved: {out_name} ({new_width}x{new_height})")
            outputs.append(out_path)
    return outputs


def grid_columns(count, columns=0):
    """Columns for a grid of count frames: as given, or 0 for a roughly square grid."""
    if columns <= 0:
        columns = math.ceil(math.sqrt(count))
    return max(1, min(columns, count))


def stitch(paths, layout, columns=0, fix_halos=False, log=print):
    """Combine same-sized frames (sorted by name) into one sheet.

    layout is "right" (one row), "down" (one column) or "grid" (columns wide, left to
    right then top to bottom; 0 columns means roughly square). Unused grid cells stay
    transparent. fix_halos bleeds the result (see alpha.py).
    Returns the output path. Raises ValueError if frame sizes differ.
    """
    if layout not in ("right", "down", "grid"):
        raise ValueError("layout must be 'right', 'down' or 'grid'")
    paths = sorted(paths)
    images = []
    for p in paths:
        with Image.open(p) as img:
            images.append(img.convert("RGBA"))
    w, h = images[0].size
    mismatched = [os.path.basename(p) for p, img in zip(paths, images) if img.size != (w, h)]
    if mismatched:
        raise ValueError(f"all frames must be {w}x{h}. Mismatched: {', '.join(mismatched)}")
    count = len(images)
    cols = {"right": count, "down": 1}.get(layout) or grid_columns(count, columns)
    rows = math.ceil(count / cols)
    composite = Image.new("RGBA", (w * cols, h * rows), (0, 0, 0, 0))
    for i, img in enumerate(images):
        composite.paste(img, ((i % cols) * w, (i // cols) * h))
    if fix_halos:
        composite = bleed(composite)
    out_path = unique_path(os.path.join(os.path.dirname(paths[0]), "tilesheet.png"))
    composite.save(out_path)
    log(f"Saved: {out_path} ({cols}x{rows} frames of {w}x{h})")
    return out_path
