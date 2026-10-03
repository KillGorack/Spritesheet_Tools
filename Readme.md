# Spritesheet Tools

A lightweight desktop toolkit for working with spritesheets, animation frames, and APNGs.  
Built with Python, [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter), Pillow, and apng, this tool provides fast utilities for common 2D asset workflows.

## Features

### Spritesheets
- **APNG maker** — Make a looping APNG from **frame files** or a **spritesheet**, watching it play while you tune it.
  - **Choose frames…**: pick the frame files (they play in file-name order), or one animated PNG/GIF/WEBP.
  - **Choose sheet…**: pick a spritesheet and tell it the sheet's **Columns** and **Rows**. The line under the input shows how it's cut (e.g. `1024x512 sheet → 8 × 4 frames of 128x128`) and warns if it doesn't divide evenly. A single-row or single-column strip of square frames is worked out automatically.
  - **Animate** (sheets): **One row** (choose which), **Whole sheet** (left to right, top to bottom, e.g. a grid from the Frame stitcher), or **Every row, saved separately** (one APNG per row; the preview shows the chosen row).
  - Delay, **Ping-pong** (forward then back), zoom and background change while it plays. **Reload** re-reads the files, e.g. after a new render.
  - **Save APNG** saves what's playing next to the input: `walk_000.png` ... gives `walk_anim.png`, row 2 of `hero.png` gives `hero_row2_anim.png`.
- **Atlas dissector** — Cuts a spritesheet into individual frames based on a fixed frame size.
- **Orthogonal resizer** — Rescales a spritesheet built from 512 px frames into several target resolutions (256, 128, 64, 32, 16 by default).
- **Frame stitcher** — Combines multiple frames into a single tilesheet: a horizontal strip, a vertical strip, or a grid with a set number of columns (or automatically about square).

### Tools
- **Image converter** — Batch converts selected files, or a whole folder (optionally including subfolders), between common game asset formats.
  - Reads any image format your Pillow install can open (PNG, BMP, TGA, JPG, WEBP, GIF, TIFF, DDS, PSD, QOI, ICO, PCX and more). With a folder, non-image files are skipped automatically.
  - Writes: PNG, TGA (raw / RLE), WEBP (lossless / lossy), JPG, BMP, TIFF, DDS (uncompressed / DXT1 / DXT5), QOI, ICO
- **Fix edge halos** — Removes the dark outline engines draw around sprites (see below) from images you already have. Results go in a `halo_fixed` folder next to them, or over the originals if you choose.

The stitcher, resizer, dissector and converter have a **Fix edge halos** setting too (on by default), so what they write is already fixed.

## Using it

    python3 sprite_sheet_tools.py

Pick a tool in the sidebar. Its panel shows what it does, the input you've chosen, and its settings. Choose an input, adjust the settings and press **Run**. Afterwards, **Open output folder** shows the results.

The input and settings stay put, so you can change a setting and run again. Settings are saved as soon as you run, and are remembered between sessions. Jobs run in the background, so the window stays responsive. Progress appears in the log at the bottom, and a short result message appears in the toolbar.

| Shortcut | Action |
|---|---|
| Ctrl+O | Choose an input for the current tool |
| Ctrl+Enter | Run (in the APNG maker: save). Enter in a number field runs too (in the APNG maker: reloads) |
| Ctrl+F | Search tools (Enter opens the first match, Esc clears) |
| Ctrl+B | Show or hide the sidebar |

The button on the right of the toolbar switches between dark and light themes.

### Assumptions & Notes

- **Atlas dissector** — Assumes each frame is **128×128 pixels** by default. Change **Frame size** in the tool's panel.

- **Orthogonal resizer** — Assumes your spritesheet is built from **512×512 base frames** by default (**Base frame size**). Choose **Nearest (pixel art)** resampling for pixel art.

  **Important:**  
  This tool expects a *perfectly clean* spritesheet.  
  Any gutters, padding, spacing, or margins between frames will break the scaling math.  
  If your sheet has baked‑in spacing, resize manually using a calculator.

- **Frame stitcher** — All input images must be **exactly the same size**.  
  The tool does not attempt to normalize or resize mismatched frames.

- **Frame order** — The frame tools (APNG maker, Frame stitcher) use the frames in file-name order. Name them `frame_000.png`, `frame_001.png`, ... so they sort correctly.

- **Edge halos** — Fully transparent pixels usually store black. You can't see them, but when an engine filters, scales, rotates or mipmaps a texture it blends them into the visible edge, which leaves a dark outline. Fixing halos ("alpha bleeding") gives those pixels the color of the nearest visible ones. Nothing visible changes. Godot's texture import has a *Fix Alpha Border* option that does the same, on by default.

- **APNG maker** — Fit zooms in by whole steps (2×, 3×, ...) so pixel art stays sharp. Empty cells in a sheet, like the unused end of a grid, are skipped. Space plays and pauses, the arrow keys step through frames, and Ctrl+Enter saves.

- **Image converter** — Files already in the target format are skipped. If the target format can't store the source's color mode (for example alpha in JPG), the image is converted to RGB/RGBA first. JPG and BMP outputs have no alpha channel.

- **Output names** — `..._anim.png` and `tilesheet.png` are never overwritten. A `_1`, `_2`, ... suffix is added instead. The resizer names its outputs after the input file (`<name>_128.png`).

## Requirements

    pip install --user customtkinter pillow apng numpy

- Python with Tk. On Fedora, Tk is a separate package: `sudo dnf install python3-tkinter`
- Optional: `kdialog` or `zenity` for the desktop's own file picker (otherwise Tk's basic one is used)

Developed with Python 3.14, Pillow 12 and CustomTkinter 6. Older versions may work, but some output formats (DDS compression, QOI) need a recent Pillow.

## Configuration

Settings are stored in `~/.config/spritetools/config.json`, or `$XDG_CONFIG_HOME/spritetools/config.json` if that variable is set. Everything in it can be changed from the window, so you shouldn't need to edit it. If you do, edit it while the tool is closed.

## Project layout

    sprite_sheet_tools.py    entry point
    icons/                   toolbar icons (Lucide, ISC license: see icons/LICENSE)
    spritetools/
      config.py              settings: defaults, load, save
      ops/                   the image processing (no GUI code)
        alpha.py, apng.py, atlas.py, convert.py, frames.py, util.py
      ui/
        app.py               main window: sidebar, toolbar, tool panel, log
        tools.py             the tools: description, input, settings, how to run
        player.py            the animation preview player
        theme.py             colors and icons
        filedialogs.py       desktop file pickers
        worker.py            runs tools in the background
    tests/                   tests for ops/, config and the tool list

To add a tool, write the processing function in `ops/`. Then add a `Tool(...)` entry to `TOOLS` in `ui/tools.py`. Its sidebar entry and settings panel are built automatically. A new setting needs a field in `config.py` too.

## Tests

    python3 -m unittest

The tests use only the standard library. They create their test images in a temporary folder and delete them afterwards.

## License

MIT, do whatever you want.. no biggie.. Not responsible for any damage or data loss.

Icons in `icons/` are from [Lucide](https://lucide.dev) (ISC license).
