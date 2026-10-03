import os
import re

from PIL import Image, ImageSequence

from .util import base_name


def animation_name(paths):
    """Name for an animation made from frame files: the first file's name without its
    frame number, e.g. ball_000.png -> "ball"."""
    name = re.sub(r"[\s._-]*\d+$", "", base_name(sorted(paths)[0]))
    return name or "animation"


def guess_grid(width, height):
    """(columns, rows) for a sheet that is one strip of square frames, else None."""
    if width % height == 0:
        return width // height, 1
    if height % width == 0:
        return 1, height // width
    return None


def sheet_info(width, height, columns, rows):
    """A line describing how a sheet is cut, e.g. "1024x512 sheet → 8 × 4 frames of 128x128"."""
    text = f"{width}x{height} sheet → {columns} × {rows} frames of {width // columns}x{height // rows}"
    if width % columns or height % rows:
        text += " (doesn't divide evenly: check columns and rows)"
    return text


def cut_sheet(sheet, columns, rows):
    """The sheet's frames as a list of rows, each a list of RGBA frames. Empty (fully
    transparent) cells are left out, e.g. the unused end of a grid."""
    fw, fh = sheet.width // columns, sheet.height // rows
    if not fw or not fh:
        raise ValueError(f"{columns} columns × {rows} rows doesn't fit a {sheet.width}x{sheet.height} image")
    cut = []
    for r in range(rows):
        frames = []
        for c in range(columns):
            frame = sheet.crop((c * fw, r * fh, (c + 1) * fw, (r + 1) * fh))
            if frame.getchannel("A").getbbox():
                frames.append(frame)
        cut.append(frames)
    return cut


def load_clips(paths, source, columns=1, rows=1, mode="row", row=1):
    """The animations to make, as a list of (name, frames). Frames are RGBA.

    source "frames": the files are the frames, in file-name order (one animated
    APNG/GIF/WEBP file gives its own frames).
    source "sheet": paths[0] is cut into columns × rows frames, and mode says what's animated:
    "row" that row (counting from 1), "sheet" every frame left to right then top to bottom,
    "rows" every row as its own animation.
    """
    if source == "frames":
        if len(paths) == 1:
            with Image.open(paths[0]) as img:
                return [(base_name(paths[0]), [f.convert("RGBA") for f in ImageSequence.Iterator(img)])]
        frames = []
        for p in sorted(paths):
            with Image.open(p) as img:
                frames.append(img.convert("RGBA"))
        return [(animation_name(paths), frames)]

    name = base_name(paths[0])
    with Image.open(paths[0]) as img:
        cut = cut_sheet(img.convert("RGBA"), columns, rows)
    if mode == "sheet":
        clips = [(name, [frame for frames in cut for frame in frames])]
    elif mode == "rows":
        clips = [(f"{name}_row{r + 1}", frames) for r, frames in enumerate(cut)]
    else:
        if row > rows:
            raise ValueError(f"row {row} doesn't exist: the sheet has {rows} rows")
        clips = [(f"{name}_row{row}", cut[row - 1])]
    clips = [(n, frames) for n, frames in clips if frames]
    if not clips:
        raise ValueError("those frames are all empty")
    return clips


def load_frames(paths, source, columns=1, rows=1, mode="row", row=1, log=print):
    """The frames to preview. For "rows" that's the chosen row, the one you're tuning."""
    clips = load_clips(paths, source, columns, rows, "row" if mode == "rows" else mode, row)
    frames = clips[0][1]
    log(f"Loaded {len(frames)} frames ({clips[0][0]})")
    return frames
