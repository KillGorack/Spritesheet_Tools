import os
import unittest

from PIL import Image

from spritetools.ops import atlas
from tests.helpers import COLORS, TempDirTestCase, quiet


class DissectTests(TempDirTestCase):

    def test_cuts_every_frame_in_reading_order(self):
        sheet = self.make_sheet("sheet.png", cols=2, rows=2, frame_size=8)
        out_dir, count = atlas.dissect(sheet, 8, log=quiet)
        self.assertEqual(count, 4)
        self.assertEqual(out_dir, self.path("sources"))
        for i in range(4):
            with Image.open(self.path("sources", f"frame_{i:03}.png")) as frame:
                self.assertEqual(frame.size, (8, 8))
                self.assertEqual(frame.getpixel((0, 0)), COLORS[i])

    def test_start_index_offsets_names(self):
        sheet = self.make_sheet("sheet.png", cols=2, rows=1, frame_size=8)
        atlas.dissect(sheet, 8, start_index=10, log=quiet)
        self.assertEqual(sorted(os.listdir(self.path("sources"))), ["frame_010.png", "frame_011.png"])

    def test_skips_partial_frames_at_edges(self):
        sheet = self.make_image("sheet.png", size=(20, 12))
        _, count = atlas.dissect(sheet, 8, log=quiet)
        self.assertEqual(count, 2)


class ResizeTests(TempDirTestCase):

    def test_outputs_each_target_size_named_after_input(self):
        sheet = self.make_sheet("hero.png", cols=2, rows=1, frame_size=64)
        outputs = atlas.resize(sheet, 64, [32, 16], log=quiet)
        self.assertEqual(outputs, [self.path("hero_032.png"), self.path("hero_016.png")])
        with Image.open(outputs[0]) as img:
            self.assertEqual(img.size, (64, 32))
        with Image.open(outputs[1]) as img:
            self.assertEqual(img.size, (32, 16))

    def test_warns_when_not_divisible(self):
        sheet = self.make_image("odd.png", size=(100, 64))
        messages = []
        atlas.resize(sheet, 64, [32], log=messages.append)
        self.assertTrue(any("not cleanly divisible by 64" in m for m in messages))


class StitchTests(TempDirTestCase):

    def make_frames(self):
        # Created out of order to check that stitching sorts by name
        return [self.make_image(f"f{i}.png", color=COLORS[i]) for i in (2, 0, 1)]

    def test_horizontal_in_name_order(self):
        out = atlas.stitch(self.make_frames(), "right", log=quiet)
        with Image.open(out) as img:
            self.assertEqual(img.size, (48, 16))
            self.assertEqual([img.getpixel((x, 0)) for x in (0, 16, 32)], COLORS[:3])

    def test_vertical(self):
        out = atlas.stitch(self.make_frames(), "down", log=quiet)
        with Image.open(out) as img:
            self.assertEqual(img.size, (16, 48))
            self.assertEqual(img.getpixel((0, 32)), COLORS[2])

    def test_does_not_overwrite_previous_tilesheet(self):
        frames = self.make_frames()
        first = atlas.stitch(frames, "right", log=quiet)
        second = atlas.stitch(frames, "right", log=quiet)
        self.assertEqual(os.path.basename(first), "tilesheet.png")
        self.assertEqual(os.path.basename(second), "tilesheet_1.png")

    def test_rejects_mismatched_sizes(self):
        frames = self.make_frames() + [self.make_image("odd.png", size=(8, 8))]
        with self.assertRaisesRegex(ValueError, "odd.png"):
            atlas.stitch(frames, "right", log=quiet)

    def test_grid_fills_rows_and_leaves_rest_transparent(self):
        frames = [self.make_image(f"g{i}.png", color=COLORS[i % 4]) for i in range(5)]
        out = atlas.stitch(frames, "grid", columns=2, log=quiet)
        with Image.open(out) as img:
            self.assertEqual(img.size, (32, 48))
            self.assertEqual(img.getpixel((16, 0)), COLORS[1])   # 2nd frame: top right
            self.assertEqual(img.getpixel((0, 16)), COLORS[2])   # 3rd frame: next row
            self.assertEqual(img.getpixel((16, 32))[3], 0)       # 6th cell is empty

    def test_grid_auto_columns_is_roughly_square(self):
        self.assertEqual([atlas.grid_columns(n) for n in (1, 4, 5, 9, 10)], [1, 2, 3, 3, 4])
        self.assertEqual(atlas.grid_columns(3, columns=8), 3)  # never wider than the frames

    def test_fix_halos_fills_empty_space(self):
        frames = [self.make_image("a.png", size=(4, 4))]
        img = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        img.paste((10, 200, 30, 255), (2, 2, 6, 6))
        img.save(frames[0])
        with Image.open(atlas.stitch(frames, "right", fix_halos=True, log=quiet)) as out:
            self.assertEqual(out.getpixel((0, 0)), (10, 200, 30, 0))

    def test_rejects_unknown_direction(self):
        with self.assertRaises(ValueError):
            atlas.stitch(self.make_frames(), "left", log=quiet)


if __name__ == "__main__":
    unittest.main()
