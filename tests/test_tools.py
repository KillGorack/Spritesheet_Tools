import os
import unittest

from PIL import Image

from spritetools.config import Config
from spritetools.ui.tools import TOOLS, TOOLS_BY_KEY, Option
from tests.helpers import TempDirTestCase, quiet


class OptionTests(unittest.TestCase):

    def test_int(self):
        option = Option("frame_size", "Frame size", "int")
        self.assertEqual(option.parse(" 64 "), 64)
        self.assertEqual(option.format(64), "64")
        with self.assertRaisesRegex(ValueError, "not a whole number"):
            option.parse("12px")
        with self.assertRaisesRegex(ValueError, "at least 1"):
            option.parse("0")

    def test_int_range(self):
        option = Option("quality", "Quality", "int", maximum=100)
        self.assertEqual(option.parse("100"), 100)
        with self.assertRaisesRegex(ValueError, "1–100"):
            option.parse("101")

    def test_int_list_accepts_commas_or_spaces(self):
        option = Option("target_sizes", "Sizes", "int_list")
        self.assertEqual(option.parse("256, 128 64,32"), [256, 128, 64, 32])
        self.assertEqual(option.format([256, 128]), "256, 128")
        with self.assertRaisesRegex(ValueError, "at least one"):
            option.parse(" , ")

    def test_choice_maps_labels_to_values(self):
        option = Option("stitch_direction", "Direction", "choice", {"Horizontal": "right", "Vertical": "down"})
        self.assertEqual(option.parse("Vertical"), "down")
        self.assertEqual(option.format("down"), "Vertical")
        self.assertEqual(option.format("unknown"), "Horizontal")

    def test_bool(self):
        self.assertIs(Option("overwrite", "Overwrite", "bool").parse(1), True)


class ToolListTests(unittest.TestCase):

    def test_every_option_is_a_config_setting(self):
        cfg = Config()
        for tool in TOOLS:
            for option in tool.options:
                with self.subTest(tool=tool.key, option=option.key):
                    self.assertTrue(hasattr(cfg, option.key))
                    # the default must be something the panel can show and read back
                    if option.kind != "bool":
                        self.assertEqual(option.parse(option.format(getattr(cfg, option.key))),
                                         getattr(cfg, option.key))

    def test_keys_are_unique(self):
        self.assertEqual(len(TOOLS_BY_KEY), len(TOOLS))

    def test_search_includes_setting_names(self):
        self.assertIn("ping-pong", TOOLS_BY_KEY["apng"].search_text())


class RunToolTests(TempDirTestCase):

    def test_stitch_uses_direction_setting(self):
        tool = TOOLS_BY_KEY["stitch"]
        frames = [self.make_image(f"f{i}.png") for i in range(2)]
        out = tool.run(Config(stitch_direction="down"), frames, quiet)
        with Image.open(out) as img:
            self.assertEqual(img.size, (16, 32))
        self.assertEqual(tool.done(out, frames), ("Saved tilesheet.png", self.dir))

    def test_converter_accepts_a_folder(self):
        tool = TOOLS_BY_KEY["convert"]
        self.make_image("a.tga")
        self.make_image("sub/b.bmp", mode="RGB", color=(0, 0, 0))
        cfg = Config(convert_to="PNG", convert_recursive=False)
        counts = tool.run(cfg, [self.dir], quiet)
        self.assertEqual(counts["converted"], 1)
        self.assertFalse(os.path.exists(self.path("sub", "b.png")))
        self.assertEqual(tool.done(counts, [self.dir]), ("Converted 1, skipped 0, failed 0", self.dir))


if __name__ == "__main__":
    unittest.main()
