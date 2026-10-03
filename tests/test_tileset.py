import os
import unittest
from itertools import combinations, product

import numpy as np
from PIL import Image

from spritetools.config import Config
from spritetools.ops import alpha, tileset
from spritetools.ui.tools import TOOLS_BY_KEY
from tests.helpers import TempDirTestCase, quiet

IMAGES = os.path.join(os.path.dirname(__file__), "test_images")
FILL = (120, 85, 55, 255)
PIECE_COLORS = {n: (n * 25, 255 - n * 25, 100, 255) for n in range(1, 10)}


def border_image(size=24, border=8):
    """Each piece filled with its own color, so tiles show exactly which pieces they got."""
    img = Image.new("RGBA", (size, size))
    for n, box in tileset.pieces(size, size, border).items():
        img.paste(PIECE_COLORS[n], box)
    return img


def pieces_in_tile(sheet, index, cols, size=24, border=8):
    """Which pieces a tile shows, by checking the middle pixel of each piece's area."""
    x0, y0 = (index % cols) * size, (index // cols) * size
    shown = []
    for n, (l, t, r, b) in tileset.pieces(size, size, border).items():
        if sheet.getpixel((x0 + (l + r) // 2, y0 + (t + b) // 2)) == PIECE_COLORS[n]:
            shown.append(n)
    return tuple(shown)


class LayoutTests(unittest.TestCase):

    def test_recipe_counts(self):
        self.assertEqual(len(tileset.RECIPES_9), 47)
        self.assertEqual(len(tileset.RECIPES_4), 16)

    def test_9_slice_has_every_blob_tile_once(self):
        # An edge piece needs its two corners; corners without an edge are inner corners
        edge_corners = {2: (1, 3), 4: (1, 7), 6: (3, 9), 8: (7, 9)}
        valid = set()
        for n in range(5):
            for edges in combinations(edge_corners, n):
                forced = {c for e in edges for c in edge_corners[e]}
                free = [c for c in (1, 3, 7, 9) if c not in forced]
                for picks in product((False, True), repeat=len(free)):
                    valid.add(frozenset(edges) | forced | {c for c, p in zip(free, picks) if p})
        recipes = [frozenset(r) for r in tileset.RECIPES_9]
        self.assertEqual(len(valid), 47)
        self.assertEqual(len(set(recipes)), len(recipes))
        self.assertEqual(set(recipes), valid)

    def test_4_block_has_every_quadrant_combination_once(self):
        everything = {frozenset(c) for n in range(5) for c in combinations((1, 2, 3, 4), n)}
        self.assertEqual({frozenset(r) for r in tileset.RECIPES_4}, everything)
        self.assertEqual(len(tileset.RECIPES_4), 16)

    def test_modes(self):
        self.assertEqual(tileset.mode_for(64, 64, 16), "9-slice")
        self.assertEqual(tileset.mode_for(64, 64, 32), "4-block")
        self.assertEqual(tileset.mode_for(64, 32, 16), "9-slice")  # half the height only
        with self.assertRaisesRegex(ValueError, "more than half"):
            tileset.mode_for(64, 64, 33)
        with self.assertRaisesRegex(ValueError, "at least 1"):
            tileset.mode_for(64, 64, 0)

    def test_pieces_numbered_left_to_right_top_to_bottom(self):
        boxes = tileset.pieces(64, 64, 16)
        self.assertEqual(boxes[1], (0, 0, 16, 16))
        self.assertEqual(boxes[5], (16, 16, 48, 48))
        self.assertEqual(boxes[9], (48, 48, 64, 64))
        self.assertEqual(tileset.pieces(64, 64, 32)[3], (0, 32, 32, 64))

    def test_describe(self):
        self.assertEqual(tileset.describe(16, (64, 64)), "9-slice: 47 tiles, 12 × 4 sheet of 64x64 (768x256)")
        self.assertIn("must be the same size", tileset.describe(16, (64, 64), (32, 32)))


class BuildTests(unittest.TestCase):

    def test_9_slice_tiles_follow_their_recipes(self):
        fill = Image.new("RGBA", (24, 24), FILL)
        sheet, layout = tileset.build(border_image(), fill, 8)
        self.assertEqual((layout, sheet.size), (("9-slice", 12, 4), (288, 96)))
        for i, recipe in enumerate(tileset.RECIPES_9):
            with self.subTest(tile=i):
                self.assertEqual(pieces_in_tile(sheet, i, 12), tuple(sorted(recipe)))
        self.assertEqual(sheet.getpixel((11 * 24 + 12, 3 * 24 + 12))[3], 0)  # the 48th cell is empty

    def test_4_block_tiles_follow_their_recipes(self):
        fill = Image.new("RGBA", (24, 24), FILL)
        sheet, layout = tileset.build(border_image(border=12), fill, 12)
        self.assertEqual((layout, sheet.size), (("4-block", 4, 4), (96, 96)))
        for i, recipe in enumerate(tileset.RECIPES_4):
            with self.subTest(tile=i):
                self.assertEqual(pieces_in_tile(sheet, i, 4, border=12), tuple(sorted(recipe)))

    def test_fill_shows_through_transparent_border(self):
        border = Image.new("RGBA", (24, 24), (0, 0, 0, 0))
        sheet, _ = tileset.build(border, Image.new("RGBA", (24, 24), FILL), 8)
        tiles = np.asarray(sheet).copy()
        tiles[72:, 264:] = FILL  # the empty 48th cell
        self.assertTrue((tiles == FILL).all())

    def test_half_transparent_border_blends_over_fill(self):
        border = Image.new("RGBA", (24, 24), (255, 255, 255, 128))
        sheet, _ = tileset.build(border, Image.new("RGBA", (24, 24), (0, 0, 0, 255)), 8)
        r, g, b, a = sheet.getpixel((0, 0))  # tile 1 has piece 1
        self.assertEqual(a, 255)
        self.assertAlmostEqual(r, 128, delta=1)

    def test_sizes_must_match(self):
        with self.assertRaisesRegex(ValueError, "same size"):
            tileset.build(border_image(), Image.new("RGBA", (16, 16)), 8)


class ReferenceTilesetTests(unittest.TestCase):
    """test_images/ holds a border image, a fill tile and the tilesets made from them
    (with Fix edge halos on). Building them again must give the same pixels."""

    def check(self, reference, border_size):
        with Image.open(os.path.join(IMAGES, "border.png")) as border, \
                Image.open(os.path.join(IMAGES, "fill.png")) as fill:
            sheet, _ = tileset.build(border, fill, border_size)
        with Image.open(os.path.join(IMAGES, reference)) as expected:
            np.testing.assert_array_equal(np.asarray(alpha.bleed(sheet)), np.asarray(expected.convert("RGBA")))

    def test_9_slice(self):
        self.check("border_tileset_big.png", 16)

    def test_4_block(self):
        self.check("border_tileset.png", 32)


class MakeTilesetTests(TempDirTestCase):

    def test_saves_next_to_border_and_never_overwrites(self):
        border = self.path("grass.png")
        border_image().save(border)
        fill = self.make_image("dirt.png", size=(24, 24), color=FILL)
        first = tileset.make_tileset(border, fill, 8, log=quiet)
        second = tileset.make_tileset(border, fill, 8, log=quiet)
        self.assertEqual((first, second), (self.path("grass_tileset.png"), self.path("grass_tileset_1.png")))
        with Image.open(first) as img:
            self.assertEqual(img.size, (288, 96))

    def test_render_for_the_view(self):
        render = TOOLS_BY_KEY["tileset"].render
        border = self.path("grass.png")
        border_image().save(border)
        fill = self.make_image("dirt.png", size=(24, 24), color=FILL)
        cfg = Config(border_size=8)
        self.assertEqual(render(cfg, {})["message"], "Choose a border image and a fill tile")
        self.assertEqual(render(cfg, {"border": [border]})["message"], "Choose a fill tile to see the tileset")
        self.assertEqual(render(cfg, {"border": [border], "fill": [fill]})["layout"], ("9-slice", 12, 4))
        self.assertIn("more than half", render(Config(border_size=20), {"border": [border]})["message"])


if __name__ == "__main__":
    unittest.main()
