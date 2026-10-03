import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from PIL import Image

from .ops.convert import OUTPUT_FORMATS

CONFIG_PATH = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "spritetools" / "config.json"


@dataclass
class Config:
    last_dir: str = "."
    frame_size: int = 128
    start_index: int = 0
    delay_ms: int = 70
    target_sizes: list = field(default_factory=lambda: [256, 128, 64, 32, 16])
    base_frame_size: int = 512
    resample: str = "LANCZOS"
    delete_original: bool = False
    overwrite: bool = False
    convert_to: str = "PNG"
    convert_recursive: bool = True
    quality: int = 90
    apng_pingpong: bool = False
    stitch_direction: str = "right"
    stitch_columns: int = 0
    fix_halos: bool = True
    apng_source: str = "frames"
    sheet_columns: int = 1
    sheet_rows: int = 1
    apng_mode: str = "row"
    preview_row: int = 1
    preview_zoom: int = 0
    border_size: int = 16
    preview_background: str = "checker"
    halo_overwrite: bool = False
    theme: str = "dark"
    sidebar_hidden: bool = False
    last_tool: str = ""

    @property
    def resample_filter(self):
        return Image.Resampling[self.resample]

    @classmethod
    def load(cls, path=CONFIG_PATH):
        """Load settings from path. Missing or invalid values fall back to the defaults."""
        cfg = cls()
        try:
            data = json.loads(Path(path).read_text())
        except (OSError, ValueError):
            return cfg
        # Keys are matched case-insensitively (older configs used FRAME_SIZE etc.)
        data = {str(k).lower(): v for k, v in data.items()}
        for f in fields(cls):
            if f.name in data:
                default = getattr(cfg, f.name)
                try:
                    setattr(cfg, f.name, type(default)(data[f.name]))
                except (TypeError, ValueError):
                    pass
        if not os.path.isdir(cfg.last_dir):
            cfg.last_dir = "."
        if cfg.resample not in Image.Resampling.__members__:
            cfg.resample = "LANCZOS"
        if cfg.convert_to not in OUTPUT_FORMATS:
            cfg.convert_to = "PNG"
        if cfg.stitch_direction not in ("right", "down", "grid"):
            cfg.stitch_direction = "right"
        if cfg.apng_source not in ("frames", "sheet"):
            cfg.apng_source = "frames"
        if cfg.apng_mode not in ("row", "sheet", "rows"):
            cfg.apng_mode = "row"
        cfg.preview_row = max(cfg.preview_row, 1)
        if cfg.theme not in ("dark", "light"):
            cfg.theme = "dark"
        return cfg

    def save(self, path=CONFIG_PATH):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2))
