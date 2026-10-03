import json
import unittest

from PIL import Image

from spritetools.config import Config
from tests.helpers import TempDirTestCase


class ConfigTests(TempDirTestCase):

    def test_missing_file_gives_defaults(self):
        self.assertEqual(Config.load(self.path("nope.json")), Config())

    def test_save_and_load_round_trip(self):
        path = self.path("sub", "config.json")
        cfg = Config(last_dir=self.dir, frame_size=64, target_sizes=[32], convert_to="QOI", overwrite=True)
        cfg.save(path)
        self.assertEqual(Config.load(path), cfg)

    def test_reads_uppercase_keys(self):
        path = self.path("config.json")
        with open(path, "w") as f:
            json.dump({"FRAME_SIZE": 32, "DELAY_MS": 40}, f)
        cfg = Config.load(path)
        self.assertEqual((cfg.frame_size, cfg.delay_ms), (32, 40))

    def test_invalid_values_fall_back_to_defaults(self):
        path = self.path("config.json")
        with open(path, "w") as f:
            json.dump({"frame_size": "big", "last_dir": "/does/not/exist",
                       "resample": "MAGIC", "convert_to": "GIF89"}, f)
        cfg = Config.load(path)
        self.assertEqual((cfg.frame_size, cfg.last_dir, cfg.resample, cfg.convert_to),
                         (128, ".", "LANCZOS", "PNG"))

    def test_corrupt_file_gives_defaults(self):
        path = self.path("config.json")
        with open(path, "w") as f:
            f.write("{not json")
        self.assertEqual(Config.load(path), Config())

    def test_resample_filter(self):
        self.assertEqual(Config(resample="NEAREST").resample_filter, Image.Resampling.NEAREST)


if __name__ == "__main__":
    unittest.main()
