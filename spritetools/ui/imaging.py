"""Showing PIL images on Tk canvases: scaling, checkerboard backdrops, conversion."""
import io
import math
import tkinter as tk

from PIL import Image

CHECKER_PX = 8


def to_photo(img):
    """Tk image of an RGB PIL image (PPM data: fast, and needs no PIL.ImageTk)."""
    buf = io.BytesIO()
    img.save(buf, "PPM")
    return tk.PhotoImage(data=buf.getvalue())


def fit_scale(size, room, zoom=0):
    """Display scale for an image of `size` in `room` (both (w, h)).

    zoom 0 (fit): the largest whole number that fits, so pixels stay sharp, or below 1
    if even 1x doesn't fit. Otherwise zoom, made smaller if it doesn't fit.
    """
    fit = min(room[0] / size[0], room[1] / size[1])
    if zoom:
        return min(zoom, fit)
    return math.floor(fit) if fit >= 1 else fit


def scaled(img, scale):
    """img resized by scale: nearest neighbor for whole-number zoom (sharp), smooth otherwise."""
    size = (max(1, round(img.width * scale)), max(1, round(img.height * scale)))
    if size == img.size:
        return img
    sharp = scale >= 1 and scale == int(scale)
    return img.resize(size, Image.Resampling.NEAREST if sharp else Image.Resampling.LANCZOS)


def checkerboard(size, light, dark):
    """RGBA checkerboard of `size` in two colors, the usual "this is transparent" pattern."""
    small = Image.new("RGBA", (math.ceil(size[0] / CHECKER_PX), math.ceil(size[1] / CHECKER_PX)), dark)
    light_rgba = Image.new("RGBA", (1, 1), light).getpixel((0, 0))
    px = small.load()
    for y in range(small.height):
        for x in range(y % 2, small.width, 2):
            px[x, y] = light_rgba
    return small.resize((small.width * CHECKER_PX, small.height * CHECKER_PX),
                        Image.Resampling.NEAREST).crop((0, 0) + tuple(size))


def on_checkerboard(img, light, dark):
    """Tk image of an RGBA image drawn over a checkerboard."""
    backdrop = checkerboard(img.size, light, dark)
    backdrop.alpha_composite(img.convert("RGBA"))
    return to_photo(backdrop.convert("RGB"))
