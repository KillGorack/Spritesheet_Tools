import os
import unittest

from PIL import Image

from spritetools.ops import convert
from tests.helpers import TempDirTestCase, quiet


class ReadableExtensionsTests(unittest.TestCase):

    def test_includes_common_game_formats(self):
        exts = convert.readable_extensions()
        for ext in (".png", ".tga", ".bmp", ".dds", ".psd", ".webp", ".qoi"):
            self.assertIn(ext, exts)

    def test_excludes_formats_pillow_cannot_decode(self):
        self.assertNotIn(".h5", convert.readable_extensions())


class FindImagesTests(TempDirTestCase):

    def setUp(self):
        super().setUp()
        self.make_image("a.tga")
        self.make_image("sub/b.png")
        with open(self.path("notes.txt"), "w") as f:
            f.write("not an image")

    def test_recursive_skips_non_images(self):
        found = convert.find_images(self.dir, recursive=True)
        self.assertEqual(found, [self.path("a.tga"), self.path("sub", "b.png")])

    def test_non_recursive(self):
        self.assertEqual(convert.find_images(self.dir, recursive=False), [self.path("a.tga")])


class ConvertImagesTests(TempDirTestCase):

    def test_every_output_format_writes_a_readable_file(self):
        for target, (ext, fmt, _) in convert.OUTPUT_FORMATS.items():
            with self.subTest(target=target):
                # The source must be in a different format, or it's skipped
                src = self.make_image("a.png" if ext == ".tga" else "a.tga", color=(255, 0, 0, 128))
                counts = convert.convert_images([src], target, overwrite=True, log=quiet)
                self.assertEqual(counts["converted"], 1)
                with Image.open(self.path("a" + ext)) as img:
                    self.assertEqual(img.format, fmt)

    def test_alpha_to_jpg_falls_back_to_rgb(self):
        src = self.make_image("a.png", color=(255, 0, 0, 128))
        convert.convert_images([src], "JPG", log=quiet)
        with Image.open(self.path("a.jpg")) as img:
            self.assertEqual(img.mode, "RGB")

    def test_skips_files_already_in_target_format(self):
        src = self.make_image("a.png")
        counts = convert.convert_images([src], "PNG", log=quiet)
        self.assertEqual(counts, {"converted": 0, "skipped": 1, "failed": 0})

    def test_skips_existing_output_unless_overwrite(self):
        src = self.make_image("a.tga", color=(0, 255, 0, 255))
        existing = self.make_image("a.png", color=(255, 0, 0, 255))
        self.assertEqual(convert.convert_images([src], "PNG", log=quiet)["skipped"], 1)
        with Image.open(existing) as img:
            self.assertEqual(img.getpixel((0, 0)), (255, 0, 0, 255))

        self.assertEqual(convert.convert_images([src], "PNG", overwrite=True, log=quiet)["converted"], 1)
        with Image.open(existing) as img:
            self.assertEqual(img.getpixel((0, 0)), (0, 255, 0, 255))

    def test_delete_original(self):
        src = self.make_image("a.tga")
        convert.convert_images([src], "PNG", delete_original=True, log=quiet)
        self.assertFalse(os.path.exists(src))
        self.assertTrue(os.path.exists(self.path("a.png")))

    def test_corrupt_file_is_counted_as_failed_and_kept(self):
        src = self.path("broken.tga")
        with open(src, "wb") as f:
            f.write(b"not really a tga")
        counts = convert.convert_images([src], "PNG", delete_original=True, log=quiet)
        self.assertEqual(counts["failed"], 1)
        self.assertTrue(os.path.exists(src))
        self.assertFalse(os.path.exists(self.path("broken.png")))


if __name__ == "__main__":
    unittest.main()
