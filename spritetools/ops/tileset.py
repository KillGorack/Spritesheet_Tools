"""Autotile tilesets from a border image and a fill tile (ported from TileMapCreator).

The border image is cut into pieces at `border` pixels from each edge. Every tile in
the tileset is the fill tile with some of those pieces drawn on top, in place. Which
pieces each tile gets is its recipe.

- 9-slice: the border image is cut into a 3x3 grid. 47 recipes (every "blob" tile), a 12 x 4
  sheet with the last cell empty.
- 4-block: the border is exactly half the image, so it's cut into 4 quadrants.
  16 recipes, a 4 x 4 sheet.

Pieces are numbered left to right, top to bottom:

    9-slice:  1 2 3      4-block:  1 2
              4 5 6                3 4
              7 8 9
"""
import os

from PIL import Image

from .alpha import bleed
from .util import base_name, unique_path

# Each tile is one way the neighbors can differ: an edge piece (2 top, 4 left, 6 right,
# 8 bottom) where the neighbor on that side is different, which also takes that edge's
# two corners, and a corner piece alone (an inner corner) where only the diagonal
# neighbor is different. That makes 47 tiles. The first 42 are in TileMapCreator's
# order; its two repeats are gone, and the 5 tiles it was missing come last.
RECIPES_9 = [
    (1, 2, 3, 6, 7, 8, 9), (1, 2, 3, 4, 7), (1, 2, 3, 4, 7, 9), (1, 2, 3, 7, 9), (1, 3, 4, 7), (1, 4, 7),
    (7, 9), (9,), (1, 2, 3, 7, 8, 9), (1, 3, 7), (), (1, 3, 4, 6, 7, 8, 9),
    (1, 2, 3, 6, 9), (1, 2, 3, 6, 7, 9), (1, 3, 7, 8, 9), (1, 3, 6, 9), (3, 6, 9), (1, 3),
    (7,), (1, 3, 4, 6, 7, 9), (3, 7, 9), (1, 2, 3, 4, 6, 7, 8, 9), (1, 2, 3, 4, 6, 7, 9), (1, 4, 7, 8, 9),
    (1, 3, 4, 7, 8, 9), (1, 3, 4, 7, 9), (1, 2, 3, 7), (1, 2, 3), (3, 9), (3,),
    (3, 7), (1, 3, 9), (1, 2, 3, 4, 7, 8, 9), (3, 6, 7, 8, 9), (1, 3, 6, 7, 8, 9), (1, 3, 6, 7, 9),
    (1, 2, 3, 9), (7, 8, 9), (1, 7), (1,), (1, 9), (1, 3, 7, 9),
    (1, 7, 9), (1, 4, 7, 9), (1, 7, 8, 9), (3, 6, 7, 9), (3, 7, 8, 9),
]
RECIPES_4 = [
    (2, 3, 4), (1, 3, 4), (1, 2, 4), (1, 2, 3),
    (1, 2), (3, 4), (1, 3), (2, 4),
    (1,), (2,), (3,), (4,),
    (2, 3), (1, 4), (), (1, 2, 3, 4),
]
LAYOUTS = {"9-slice": (RECIPES_9, 12, 4), "4-block": (RECIPES_4, 4, 4)}  # recipes, columns, rows


def mode_for(width, height, border):
    """ "4-block" when the border is exactly half the image, else "9-slice".
    Raises ValueError if the border doesn't fit."""
    if border < 1:
        raise ValueError("the border size must be at least 1 px")
    if border * 2 > width or border * 2 > height:
        raise ValueError(f"a {border} px border is more than half of the {width}x{height} border image")
    return "4-block" if border * 2 == width and border * 2 == height else "9-slice"


def pieces(width, height, border):
    """The border image's pieces as (left, top, right, bottom) boxes, numbered from 1."""
    if mode_for(width, height, border) == "4-block":
        xs, ys = (0, border, width), (0, border, height)
    else:
        xs, ys = (0, border, width - border, width), (0, border, height - border, height)
    boxes = [(xs[c], ys[r], xs[c + 1], ys[r + 1]) for r in range(len(ys) - 1) for c in range(len(xs) - 1)]
    return dict(enumerate(boxes, start=1))


def describe(border_size, border_dims, fill_dims=None):
    """A line saying what will be made, e.g. "9-slice: 47 tiles, 12 × 4 sheet of 64x64 (768x256)"."""
    mode = mode_for(*border_dims, border_size)
    recipes, cols, rows = LAYOUTS[mode]
    tw, th = fill_dims or border_dims
    text = f"{mode}: {len(recipes)} tiles, {cols} × {rows} sheet of {tw}x{th} ({cols * tw}x{rows * th})"
    if fill_dims and fill_dims != border_dims:
        text += f" (the border image is {border_dims[0]}x{border_dims[1]}: they must be the same size)"
    return text


def build(border, fill, border_size):
    """The tileset image, plus (mode, columns, rows). Both inputs must be the same size."""
    if border.size != fill.size:
        raise ValueError(f"the border image is {border.width}x{border.height} and the fill tile "
                         f"{fill.width}x{fill.height}: they must be the same size")
    mode = mode_for(border.width, border.height, border_size)
    recipes, cols, rows = LAYOUTS[mode]
    boxes = pieces(border.width, border.height, border_size)
    border, fill = border.convert("RGBA"), fill.convert("RGBA")
    crops = {n: border.crop(box) for n, box in boxes.items()}
    tw, th = fill.size
    sheet = Image.new("RGBA", (cols * tw, rows * th), (0, 0, 0, 0))
    for i, recipe in enumerate(recipes):
        tile = fill.copy()
        for n in recipe:
            tile.alpha_composite(crops[n], dest=boxes[n][:2])
        sheet.paste(tile, ((i % cols) * tw, (i // cols) * th))
    return sheet, (mode, cols, rows)


def make_tileset(border_path, fill_path, border_size, fix_halos=False, log=print):
    """Build the tileset and save it as <border image name>_tileset.png next to the border
    image (never overwritten). fix_halos bleeds the result (see alpha.py). Returns the path."""
    with Image.open(border_path) as border, Image.open(fill_path) as fill:
        sheet, (mode, cols, rows) = build(border, fill, border_size)
    if fix_halos:
        sheet = bleed(sheet)
    out = unique_path(os.path.join(os.path.dirname(border_path), f"{base_name(border_path)}_tileset.png"))
    sheet.save(out)
    log(f"Saved: {out} ({mode}, {cols} × {rows} tiles)")
    return out
