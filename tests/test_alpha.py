import os
import unittest

import numpy as np
from PIL import Image

from spritetools.ops import alpha
from tests.helpers import TempDirTestCase, quiet


def sprite(size=64, color=(255, 40, 0, 255)):
    """An opaque square in the middle of transparent black, plus one half-transparent pixel."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    img.paste(color, (size // 4, size // 4, size * 3 // 4, size * 3 // 4))
    img.putpixel((size * 3 // 4 - 1, size * 3 // 4 - 1), (0, 0, 255, 128))
    return img


class BleedTests(unittest.TestCase):

    def test_visible_pixels_and_alpha_are_unchanged(self):
        before = np.asarray(sprite())
        after = np.asarray(alpha.bleed(sprite()))
        visible = before[..., 3] > 0
        np.testing.assert_array_equal(after[visible], before[visible])
        np.testing.assert_array_equal(after[..., 3], before[..., 3])

    def test_transparent_pixels_take_nearby_color(self):
        img = alpha.bleed(sprite())
        self.assertEqual(img.getpixel((15, 20)), (255, 40, 0, 0))  # right next to the edge
        self.assertEqual(img.getpixel((0, 0)), (255, 40, 0, 0))    # far corner, filled coarsely

    def test_no_black_left(self):
        after = np.asarray(alpha.bleed(sprite(size=300)))
        hidden = after[after[..., 3] == 0]
        self.assertFalse((hidden[:, :3].sum(axis=1) == 0).any())

    def test_two_colors_each_bleed_their_own_side(self):
        img = Image.new("RGBA", (40, 10), (0, 0, 0, 0))
        img.paste((255, 0, 0, 255), (0, 0, 10, 10))
        img.paste((0, 0, 255, 255), (30, 0, 40, 10))
        out = alpha.bleed(img)
        self.assertEqual(out.getpixel((11, 5))[:3], (255, 0, 0))
        self.assertEqual(out.getpixel((28, 5))[:3], (0, 0, 255))

    def test_images_without_transparency_are_returned_as_is(self):
        img = Image.new("RGB", (8, 8), (1, 2, 3))
        self.assertIs(alpha.bleed(img), img)

    def test_fully_transparent_image_is_unchanged(self):
        img = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        self.assertEqual(alpha.bleed(img).tobytes(), img.tobytes())

    def test_odd_sizes(self):
        for size in [(1, 1), (1, 7), (13, 3), (33, 65)]:
            with self.subTest(size=size):
                img = Image.new("RGBA", size, (0, 0, 0, 0))
                img.putpixel((0, 0), (9, 9, 9, 255))
                self.assertEqual(alpha.bleed(img).getpixel((size[0] - 1, size[1] - 1))[:3], (9, 9, 9))


class FixHalosTests(TempDirTestCase):

    def test_writes_to_halo_fixed_folder_by_default(self):
        src = self.path("a.png")
        sprite().save(src)
        counts = alpha.fix_halos([src], log=quiet)
        self.assertEqual((counts["fixed"], counts["output_dir"]), (1, self.path("halo_fixed")))
        with Image.open(self.path("halo_fixed", "a.png")) as img:
            self.assertEqual(img.getpixel((0, 0)), (255, 40, 0, 0))
        with Image.open(src) as img:
            self.assertEqual(img.getpixel((0, 0)), (0, 0, 0, 0))

    def test_overwrite_keeps_format(self):
        src = self.path("a.tga")
        sprite().save(src)
        alpha.fix_halos([src], overwrite=True, log=quiet)
        with Image.open(src) as img:
            self.assertEqual(img.format, "TGA")
            self.assertEqual(img.getpixel((0, 0)), (255, 40, 0, 0))

    def test_skips_images_without_alpha_and_earlier_output(self):
        jpg = self.make_image("a.jpg", mode="RGB", color=(1, 2, 3))
        old = self.make_image("halo_fixed/b.png")
        counts = alpha.fix_halos([jpg, old], log=quiet)
        self.assertEqual((counts["fixed"], counts["skipped"]), (0, 2))


if __name__ == "__main__":
    unittest.main()
