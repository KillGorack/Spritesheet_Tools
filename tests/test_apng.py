import os
import unittest

from apng import APNG
from PIL import Image

from spritetools.ops import apng
from tests.helpers import COLORS, TempDirTestCase, quiet


def frame_count(path):
    return len(APNG.open(path).frames)


class SaveApngTests(TempDirTestCase):

    def frames(self, n):
        return [Image.new("RGBA", (8, 8), COLORS[i % 4]) for i in range(n)]

    def test_delay_and_loop(self):
        out = self.path("a.png")
        apng.save_apng(self.frames(3), out, 50)
        anim = APNG.open(out)
        self.assertEqual(len(anim.frames), 3)
        self.assertEqual(anim.frames[0][1].delay, 50)
        self.assertEqual(anim.num_plays, 0)

    def test_pingpong_plays_back_without_repeating_ends(self):
        out = self.path("a.png")
        apng.save_apng(self.frames(4), out, 50, pingpong=True)  # 0 1 2 3 2 1
        self.assertEqual(frame_count(out), 6)

    def test_pingpong_with_two_frames_is_unchanged(self):
        out = self.path("a.png")
        apng.save_apng(self.frames(2), out, 50, pingpong=True)
        self.assertEqual(frame_count(out), 2)

    def test_different_sizes_are_centered(self):
        out = self.path("a.png")
        apng.save_apng([Image.new("RGBA", (8, 8), COLORS[0]), Image.new("RGBA", (4, 4), COLORS[1])], out, 50)
        with Image.open(out) as img:
            self.assertEqual(img.size, (8, 8))
            img.seek(1)
            self.assertEqual(img.convert("RGBA").getpixel((4, 4)), COLORS[1])
            self.assertEqual(img.convert("RGBA").getpixel((0, 0))[3], 0)


class MakeApngsTests(TempDirTestCase):

    def test_frame_files_give_one_named_animation(self):
        paths = [self.make_image(f"walk_{i:03}.png", color=COLORS[i]) for i in range(3)]
        folder, saved = apng.make_apngs(paths, "frames", 1, 1, "row", 1, 70, log=quiet)
        self.assertEqual((folder, saved), (self.dir, [self.path("walk_anim.png")]))
        self.assertEqual(frame_count(saved[0]), 3)

    def test_never_overwrites(self):
        paths = [self.make_image(f"walk_{i}.png") for i in range(2)]
        apng.make_apngs(paths, "frames", 1, 1, "row", 1, 70, log=quiet)
        _, saved = apng.make_apngs(paths, "frames", 1, 1, "row", 1, 70, log=quiet)
        self.assertEqual(os.path.basename(saved[0]), "walk_anim_1.png")

    def test_sheet_one_row(self):
        sheet = self.make_sheet("hero.png", cols=4, rows=2, frame_size=8)
        _, saved = apng.make_apngs([sheet], "sheet", 4, 2, "row", 2, 70, pingpong=True, log=quiet)
        self.assertEqual([os.path.basename(p) for p in saved], ["hero_row2_anim.png"])
        self.assertEqual(frame_count(saved[0]), 6)  # 4 frames, ping-pong

    def test_sheet_every_row(self):
        sheet = self.make_sheet("hero.png", cols=4, rows=2, frame_size=8)
        _, saved = apng.make_apngs([sheet], "sheet", 4, 2, "rows", 1, 70, log=quiet)
        self.assertEqual([os.path.basename(p) for p in saved], ["hero_row1_anim.png", "hero_row2_anim.png"])

    def test_whole_sheet(self):
        sheet = self.make_sheet("hero.png", cols=4, rows=2, frame_size=8)
        _, saved = apng.make_apngs([sheet], "sheet", 4, 2, "sheet", 1, 70, log=quiet)
        self.assertEqual([os.path.basename(p) for p in saved], ["hero_anim.png"])
        self.assertEqual(frame_count(saved[0]), 8)


if __name__ == "__main__":
    unittest.main()
