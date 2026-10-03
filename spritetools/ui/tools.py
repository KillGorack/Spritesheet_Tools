"""The tools listed in the sidebar.

Each Tool says what input it takes, which config settings it shows, and how to run.
The app builds the sidebar entry and the settings panel from this, so adding a tool
means writing its processing function in ops/ and adding a Tool to TOOLS.

Nothing here touches the GUI toolkit, so it can be tested on its own.
"""
import os
from dataclasses import dataclass, field
from typing import Callable

from PIL import Image

from ..ops import alpha, apng, atlas, convert, frames


@dataclass(eq=False)  # compared by identity, so options can be dict keys
class Option:
    """One setting shown in a tool's panel, stored in the Config field `key`."""
    key: str
    label: str
    kind: str                                    # "int", "int_list", "bool" or "choice"
    choices: dict = field(default_factory=dict)  # choice: label shown -> value stored
    minimum: int = 1
    maximum: int = None
    enabled_when: dict = None                    # {setting: values} it only applies with

    def parse(self, raw):
        """Value to store from what's in the widget. Raises ValueError with a message for the user."""
        if self.kind == "bool":
            return bool(raw)
        if self.kind == "choice":
            return self.choices[raw]
        if self.kind == "int":
            return self._check(raw)
        numbers = [self._check(part) for part in str(raw).replace(",", " ").split()]
        if not numbers:
            raise ValueError(f"{self.label}: enter at least one number")
        return numbers

    def format(self, value):
        """What the widget shows for a stored value."""
        if self.kind == "choice":
            return next((label for label, v in self.choices.items() if v == value), next(iter(self.choices)))
        if self.kind == "int_list":
            return ", ".join(str(v) for v in value)
        if self.kind == "int":
            return str(value)
        return value

    def _check(self, raw):
        try:
            value = int(str(raw).strip())
        except ValueError:
            raise ValueError(f"{self.label}: '{str(raw).strip()}' is not a whole number") from None
        if value < self.minimum or (self.maximum is not None and value > self.maximum):
            limit = f"{self.minimum}–{self.maximum}" if self.maximum is not None else f"at least {self.minimum}"
            raise ValueError(f"{self.label}: must be {limit}")
        return value


@dataclass
class Tool:
    key: str
    name: str
    category: str
    description: str
    inputs: str          # "file", "files", "files_or_folder" or "frames_or_sheet"
    options: list
    run: Callable        # run(config, paths, log) -> result; runs in the background
    done: Callable       # done(result, paths) -> (note for the toolbar, output folder)
    run_label: str = "Run"
    preview: bool = False   # run returns frames, which play in the preview instead of the log
    save: Callable = None   # a second action next to run, same signature as run
    save_done: Callable = None
    save_label: str = "Save"
    input_info: Callable = None  # input_info(config, paths) -> line shown under the input, or None
    prepare: Callable = None     # prepare(config, paths) after an input is chosen, e.g. to guess settings

    def search_text(self):
        """Everything the sidebar search looks in: name, category, description, settings."""
        parts = [self.name, self.category, self.description]
        for option in self.options:
            parts += [option.label, *option.choices]
        return " ".join(parts).lower()


# Settings used by more than one tool
FRAME_SIZE = Option("frame_size", "Frame size (px)", "int")
DELAY = Option("delay_ms", "Delay per frame (ms)", "int")
FIX_HALOS = Option("fix_halos", "Fix edge halos", "bool")
PINGPONG = Option("apng_pingpong", "Ping-pong", "bool")

RESAMPLE_CHOICES = {
    "Lanczos (smooth)": "LANCZOS",
    "Bicubic": "BICUBIC",
    "Bilinear": "BILINEAR",
    "Box": "BOX",
    "Hamming": "HAMMING",
    "Nearest (pixel art)": "NEAREST",
}


SHEET = {"apng_source": ("sheet",)}


def _layout(cfg):
    """The APNG maker's input settings, in the order frames.load_clips takes them."""
    return cfg.apng_source, cfg.sheet_columns, cfg.sheet_rows, cfg.apng_mode, cfg.preview_row


def _sheet_info(cfg, paths):
    if cfg.apng_source != "sheet":
        return None
    with Image.open(paths[0]) as img:
        return frames.sheet_info(img.width, img.height, cfg.sheet_columns, cfg.sheet_rows)


def _guess_sheet_layout(cfg, paths):
    """A newly chosen sheet that the current columns and rows don't fit: guess a strip of square frames."""
    if cfg.apng_source != "sheet":
        return
    with Image.open(paths[0]) as img:
        width, height = img.size
    fits = not (width % cfg.sheet_columns or height % cfg.sheet_rows) and (cfg.sheet_columns, cfg.sheet_rows) != (1, 1)
    guess = frames.guess_grid(width, height)
    if guess and not fits:
        cfg.sheet_columns, cfg.sheet_rows = guess
        if cfg.preview_row > cfg.sheet_rows:
            cfg.preview_row = 1


def _folder_of(path):
    return path if os.path.isdir(path) else os.path.dirname(path)


def _expand_folder(paths, recursive):
    """A chosen folder becomes the images in it."""
    if len(paths) == 1 and os.path.isdir(paths[0]):
        return convert.find_images(paths[0], recursive)
    return paths


def _convert(cfg, paths, log):
    return convert.convert_images(_expand_folder(paths, cfg.convert_recursive), cfg.convert_to, cfg.quality,
                                  cfg.overwrite, cfg.delete_original, cfg.fix_halos, log=log)


TOOLS = [
    Tool(
        "apng", "APNG maker", "Spritesheets",
        "Choose frame files or a spritesheet, tune the animation while it plays, then save it as a looping "
        "APNG next to the input. For a sheet, set its columns and rows and what to animate. "
        "Space plays and pauses, the arrow keys step.",
        "frames_or_sheet", [
            Option("sheet_columns", "Columns", "int", enabled_when=SHEET),
            Option("sheet_rows", "Rows", "int", enabled_when=SHEET),
            Option("apng_mode", "Animate", "choice",
                   {"One row": "row", "Whole sheet": "sheet", "Every row, saved separately": "rows"},
                   enabled_when=SHEET),
            Option("preview_row", "Row", "int", enabled_when={**SHEET, "apng_mode": ("row", "rows")}),
            DELAY,
            PINGPONG,
            Option("preview_zoom", "Zoom", "choice", {"Fit": 0, "100%": 1, "200%": 2, "400%": 4}),
            Option("preview_background", "Background", "choice",
                   {"Checkerboard": "checker", "Dark": "dark", "Light": "light"}),
        ],
        run=lambda cfg, paths, log: frames.load_frames(paths, *_layout(cfg), log=log),
        done=lambda loaded, paths: (f"Loaded {len(loaded)} frames", None),
        run_label="Reload", preview=True,
        save=lambda cfg, paths, log: apng.make_apngs(paths, *_layout(cfg), cfg.delay_ms, cfg.apng_pingpong, log=log),
        save_done=lambda r, paths: (f"Saved {os.path.basename(r[1][0])}" if len(r[1]) == 1
                                    else f"Saved {len(r[1])} APNGs", r[0]),
        save_label="Save APNG",
        input_info=_sheet_info, prepare=_guess_sheet_layout,
    ),
    Tool(
        "dissect", "Atlas dissector", "Spritesheets",
        "Cuts a spritesheet into frame_000.png, frame_001.png, ... in a sources folder next to it. "
        "Partial frames at the edges are skipped.",
        "file", [FRAME_SIZE, Option("start_index", "First frame number", "int", minimum=0), FIX_HALOS],
        run=lambda cfg, paths, log: atlas.dissect(paths[0], cfg.frame_size, cfg.start_index, cfg.fix_halos,
                                                  log=log),
        done=lambda r, paths: (f"Extracted {r[1]} frames", r[0]),
    ),
    Tool(
        "resize", "Orthogonal resizer", "Spritesheets",
        "Rescales a sheet built from base-size frames so each frame becomes each target size, "
        "saved as <name>_128.png etc. next to it. The sheet must have no gutters or padding.",
        "file", [
            Option("base_frame_size", "Base frame size (px)", "int"),
            Option("target_sizes", "Target sizes (px)", "int_list"),
            Option("resample", "Resampling", "choice", RESAMPLE_CHOICES),
            FIX_HALOS,
        ],
        run=lambda cfg, paths, log: atlas.resize(paths[0], cfg.base_frame_size, cfg.target_sizes,
                                                 cfg.resample_filter, cfg.fix_halos, log=log),
        done=lambda outs, paths: (f"Saved {len(outs)} sizes", os.path.dirname(paths[0])),
    ),
    Tool(
        "stitch", "Frame stitcher", "Spritesheets",
        "Combines frames of the same size, in file-name order, into one sheet saved as tilesheet.png. "
        "A grid fills left to right, then top to bottom.",
        "files", [
            Option("stitch_direction", "Layout", "choice",
                   {"Horizontal strip": "right", "Vertical strip": "down", "Grid": "grid"}),
            Option("stitch_columns", "Grid columns (0 = auto)", "int", minimum=0,
                   enabled_when={"stitch_direction": ("grid",)}),
            FIX_HALOS,
        ],
        run=lambda cfg, paths, log: atlas.stitch(paths, cfg.stitch_direction, cfg.stitch_columns,
                                                 cfg.fix_halos, log=log),
        done=lambda out, paths: (f"Saved {os.path.basename(out)}", os.path.dirname(out)),
    ),
    Tool(
        "convert", "Image converter", "Tools",
        "Converts images to another format, saved next to the originals. Takes any image Pillow can read; "
        "with a folder, every image in it. Files already in the target format are skipped.",
        "files_or_folder", [
            Option("convert_to", "Convert to", "choice", {name: name for name in convert.OUTPUT_FORMATS}),
            Option("quality", "Quality (JPG, lossy WEBP)", "int", maximum=100),
            Option("convert_recursive", "Include subfolders", "bool"),
            Option("overwrite", "Overwrite existing files", "bool"),
            Option("delete_original", "Delete originals", "bool"),
            FIX_HALOS,
        ],
        run=_convert,
        done=lambda c, paths: (f"Converted {c['converted']}, skipped {c['skipped']}, failed {c['failed']}",
                               _folder_of(paths[0])),
    ),
    Tool(
        "halos", "Fix edge halos", "Tools",
        "Removes the dark outline engines draw around sprites when they filter or scale them, "
        "by giving fully transparent pixels the color of the nearest visible ones. "
        "What you see in the image doesn't change. Results go in a halo_fixed folder next to the images.",
        "files_or_folder", [
            Option("convert_recursive", "Include subfolders", "bool"),
            Option("halo_overwrite", "Overwrite originals instead", "bool"),
        ],
        run=lambda cfg, paths, log: alpha.fix_halos(_expand_folder(paths, cfg.convert_recursive),
                                                    cfg.halo_overwrite, log=log),
        done=lambda c, paths: (f"Fixed {c['fixed']}, skipped {c['skipped']}, failed {c['failed']}",
                               paths[0] if os.path.isdir(paths[0]) else c["output_dir"] or _folder_of(paths[0])),
    ),
]

TOOLS_BY_KEY = {tool.key: tool for tool in TOOLS}
