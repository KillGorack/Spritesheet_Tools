import os
import shutil
import tempfile
import unittest

from PIL import Image

COLORS = [(255, 0, 0, 255), (0, 255, 0, 128), (0, 0, 255, 255), (255, 255, 0, 255)]


class TempDirTestCase(unittest.TestCase):
    """Gives each test a fresh temporary folder in self.dir."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="spritetools_test_")
        self.addCleanup(shutil.rmtree, self.dir)

    def path(self, *parts):
        return os.path.join(self.dir, *parts)

    def make_image(self, name, size=(16, 16), color=(255, 0, 0, 255), mode="RGBA"):
        path = self.path(name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        Image.new(mode, size, color).save(path)
        return path

    def make_sheet(self, name, cols, rows, frame_size):
        """A sheet where every frame is filled with a different color from COLORS."""
        sheet = Image.new("RGBA", (cols * frame_size, rows * frame_size))
        for i in range(cols * rows):
            x, y = (i % cols) * frame_size, (i // cols) * frame_size
            sheet.paste(COLORS[i % len(COLORS)], (x, y, x + frame_size, y + frame_size))
        path = self.path(name)
        sheet.save(path)
        return path


def quiet(*args):
    """A log callback that discards messages."""
