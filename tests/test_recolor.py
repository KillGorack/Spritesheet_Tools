import colorsys
import os
import unittest

import numpy as np
from PIL import Image

from spritetools.config import Config
from spritetools.ops import recolor
from spritetools.ui.tools import TOOLS_BY_KEY, Option
from tests.helpers import TempDirTestCase, quiet

RED, GREEN, GREY = (200, 30, 30, 255), (30, 200, 30, 255), (128, 128, 128, 255)


def strip(*colors):
    img = Image.new("RGBA", (len(colors), 1))
    img.putdata(colors)
    return img


def pixels(img):
    return [img.getpixel((x, 0)) for x in range(img.width)]


class ColorMathTests(unittest.TestCase):

    def test_hsv_matches_colorsys_and_round_trips(self):
        rgb = np.random.default_rng(0).random((500, 3))
        h, s, v = recolor.rgb_to_hsv(rgb)
        expected = np.array([colorsys.rgb_to_hsv(*p) for p in rgb])
        np.testing.assert_allclose(np.stack([h / 360, s, v], axis=1), expected, atol=1e-12)
        np.testing.assert_allclose(recolor.hsv_to_rgb(h, s, v), rgb, atol=1e-12)

    def test_hex(self):
        self.assertEqual(recolor.rgb_to_hex((200, 30, 255)), "#c81eff")
        self.assertEqual(recolor.hex_to_rgb("#c81eff"), (200, 30, 255))

    def test_hue_distance_wraps_around(self):
        self.assertEqual(float(recolor.hue_distance(350, 10)), 20)


class ShiftHueTests(unittest.TestCase):

    def test_only_the_range_changes(self):
        out = pixels(recolor.shift_hue(strip(RED, GREEN, GREY), hue=0, spread=20, new_hue=240))
        self.assertEqual(out[0], (30, 30, 200, 255))   # red became blue, same shade
        self.assertEqual(out[1:], [GREEN, GREY])       # other hues and greys untouched

    def test_alpha_is_kept(self):
        out = recolor.shift_hue(strip((200, 30, 30, 90)), 0, 20, 120)
        self.assertEqual(out.getpixel((0, 0))[3], 90)

    def test_edge_of_range_blends(self):
        # hue 30 is 10° past the edge of a 20° range, inside the 15° fade-out
        orange = colorsys.hsv_to_rgb(30 / 360, 0.85, 0.8)
        img = strip(tuple(round(c * 255) for c in orange) + (255,))
        moved = recolor.hue_of(recolor.shift_hue(img, 0, 20, 120).getpixel((0, 0)))
        self.assertTrue(30 < moved < 150, moved)  # moved part of the way, not all of it

    def test_saturation_and_brightness(self):
        out = recolor.shift_hue(strip(RED), 0, 20, 0, saturation=-100, brightness=-50).getpixel((0, 0))
        self.assertEqual(out, (100, 100, 100, 255))  # no saturation left, half as bright


class SwapTests(unittest.TestCase):

    def test_palette_most_used_first_and_ignores_transparent(self):
        img = strip(RED, RED, GREEN, (1, 2, 3, 0))
        self.assertEqual(recolor.palette([img]), [((200, 30, 30), 2), ((30, 200, 30), 1)])

    def test_swap_keeps_alpha(self):
        out = recolor.swap_colors(strip(RED, (200, 30, 30, 50), GREEN), {(200, 30, 30): (1, 2, 3)})
        self.assertEqual(pixels(out), [(1, 2, 3, 255), (1, 2, 3, 50), GREEN])

    def test_swaps_happen_at_once(self):
        out = recolor.swap_colors(strip(RED, GREEN), {RED[:3]: GREEN[:3], GREEN[:3]: RED[:3]})
        self.assertEqual(pixels(out), [GREEN, RED])


class FilesTests(TempDirTestCase):

    def test_saves_into_named_folder_keeping_names_and_format(self):
        a = self.path("walk_000.png")
        strip(RED, GREEN).save(a)
        b = self.path("walk_001.tga")
        strip(RED).save(b)
        cfg = Config(recolor_mode="swap", recolor_map={"#c81e1e": "#0000ff"}, recolor_folder="blue")
        counts = recolor.recolor_files([a, b], cfg, log=quiet)
        self.assertEqual((counts["recolored"], counts["output_dir"]), (2, self.path("blue")))
        with Image.open(self.path("blue", "walk_001.tga")) as img:
            self.assertEqual((img.format, img.getpixel((0, 0))), ("TGA", (0, 0, 255, 255)))
        with Image.open(a) as img:
            self.assertEqual(img.getpixel((0, 0)), RED)  # originals untouched

    def test_skips_earlier_output(self):
        os.makedirs(self.path("blue"))
        old = self.path("blue", "x.png")
        strip(RED).save(old)
        self.assertEqual(recolor.recolor_files([old], Config(recolor_folder="blue"), log=quiet)["skipped"], 1)

    def test_render_for_the_view(self):
        render = TOOLS_BY_KEY["recolor"].render
        src = self.path("a.png")
        strip(RED, GREEN).save(src)
        self.assertEqual(render(Config(), None)["message"], "Choose images or a folder")
        data = render(Config(recolor_mode="swap", recolor_map={"#c81e1e": "#0000ff"}), [src])
        self.assertEqual(pixels(data["after"]), [(0, 0, 255, 255), GREEN])
        self.assertEqual(len(data["palette"]), 2)
        shifted = render(Config(recolor_hue=0, recolor_range=20, recolor_new_hue=240), [self.dir])
        self.assertEqual(shifted["after"].getpixel((0, 0)), (30, 30, 200, 255))


class OptionTests(unittest.TestCase):

    def test_slider_rounds_and_clamps(self):
        option = Option("recolor_hue", "Hue", "slider", minimum=0, maximum=359)
        self.assertEqual((option.parse(12.6), option.parse(400), option.parse(-3)), (13, 359, 0))

    def test_text_must_be_a_plain_folder_name(self):
        option = Option("recolor_folder", "Folder", "text")
        self.assertEqual(option.parse("  enemy_blue "), "enemy_blue")
        for bad in ("", "a/b", "..", "x:y"):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "folder name"):
                option.parse(bad)


if __name__ == "__main__":
    unittest.main()
