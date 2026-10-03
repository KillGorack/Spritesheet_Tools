import unittest

from PIL import Image

from spritetools.ops import apng, atlas, frames
from tests.helpers import COLORS, TempDirTestCase, quiet


class FrameFilesTests(TempDirTestCase):

    def test_several_files_in_name_order(self):
        paths = [self.make_image(f"f{i}.png", color=COLORS[i]) for i in (2, 0, 1)]
        loaded = frames.load_frames(paths, "frames", log=quiet)
        self.assertEqual([f.getpixel((0, 0)) for f in loaded], COLORS[:3])

    def test_animated_png(self):
        paths = [self.make_image(f"f{i}.png", color=COLORS[i]) for i in range(3)]
        _, saved = apng.make_apngs(paths, "frames", 1, 1, "row", 1, 50, log=quiet)
        self.assertEqual(len(frames.load_frames(saved, "frames", log=quiet)), 3)

    def test_animation_name_drops_frame_number(self):
        for name, expected in [("walk_000.png", "walk"), ("Run-12.png", "Run"), ("0001.png", "animation"),
                               ("idle 3.tga", "idle"), ("jump.png", "jump")]:
            with self.subTest(name=name):
                self.assertEqual(frames.animation_name([name]), expected)


class SheetTests(TempDirTestCase):

    def setUp(self):
        super().setUp()
        # 3 columns x 2 rows of 8x8 frames, colored COLORS in reading order
        self.sheet = self.make_sheet("hero.png", cols=3, rows=2, frame_size=8)

    def colors(self, loaded):
        return [f.getpixel((0, 0)) for f in loaded]

    def test_one_row(self):
        loaded = frames.load_frames([self.sheet], "sheet", 3, 2, "row", 2, log=quiet)
        self.assertEqual(self.colors(loaded), [COLORS[3], COLORS[0], COLORS[1]])

    def test_whole_sheet_in_reading_order(self):
        loaded = frames.load_frames([self.sheet], "sheet", 3, 2, "sheet", 1, log=quiet)
        self.assertEqual(len(loaded), 6)

    def test_every_row_previews_the_chosen_row(self):
        loaded = frames.load_frames([self.sheet], "sheet", 3, 2, "rows", 2, log=quiet)
        self.assertEqual(len(loaded), 3)
        self.assertEqual(loaded[0].getpixel((0, 0)), COLORS[3])

    def test_every_row_gives_one_clip_per_row(self):
        clips = frames.load_clips([self.sheet], "sheet", 3, 2, "rows")
        self.assertEqual([name for name, _ in clips], ["hero_row1", "hero_row2"])

    def test_non_square_frames(self):
        loaded = frames.load_frames([self.sheet], "sheet", 6, 1, "row", 1, log=quiet)
        self.assertEqual((len(loaded), loaded[0].size), (6, (4, 16)))

    def test_row_out_of_range(self):
        with self.assertRaisesRegex(ValueError, "the sheet has 2 rows"):
            frames.load_frames([self.sheet], "sheet", 3, 2, "row", 3, log=quiet)

    def test_more_columns_than_pixels(self):
        with self.assertRaisesRegex(ValueError, "doesn't fit"):
            frames.load_frames([self.sheet], "sheet", 100, 1, "row", 1, log=quiet)

    def test_empty_cells_are_skipped(self):
        paths = [self.make_image(f"f{i}.png", color=COLORS[i % 4]) for i in range(5)]
        grid = atlas.stitch(paths, "grid", columns=3, log=quiet)  # 3x2, one empty cell
        self.assertEqual(len(frames.load_frames([grid], "sheet", 3, 2, "sheet", 1, log=quiet)), 5)


class LayoutHelpersTests(unittest.TestCase):

    def test_guess_grid_for_strips_only(self):
        self.assertEqual(frames.guess_grid(512, 64), (8, 1))
        self.assertEqual(frames.guess_grid(64, 256), (1, 4))
        self.assertIsNone(frames.guess_grid(1024, 768))

    def test_sheet_info(self):
        self.assertEqual(frames.sheet_info(1024, 512, 8, 4), "1024x512 sheet → 8 × 4 frames of 128x128")
        self.assertIn("doesn't divide evenly", frames.sheet_info(1001, 512, 8, 4))


if __name__ == "__main__":
    unittest.main()
