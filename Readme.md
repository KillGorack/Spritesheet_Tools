# Spritesheet Tools

A lightweight desktop toolkit for 2D game assets: spritesheets and animations, autotile tilesets, and batch image jobs like format conversion and recoloring.  
Built with Python, [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter), Pillow and apng. Runs on Linux (developed on Fedora/KDE).

<!-- Screenshot goes here -->

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

### Tilesets
- **Tileset maker** — Builds an autotile tileset from a **border image** and a **fill tile** of the same size (ported from TileMapCreator).
  - The border image is cut at **Border size** pixels from each edge. A 3×3 cut (9-slice) gives all 47 tiles of a "blob" set in a 12 × 4 sheet (the last cell is empty); a border of exactly half the image (4-block) gives 16 tiles in a 4 × 4 sheet. Each tile is the fill tile with some of the border pieces drawn over it.
  - The border image is shown with red guide lines where it's cut: drag one to change the border size. The tileset updates as you go; hover a tile to see which pieces it uses.
  - **Save tileset** writes `<border image>_tileset.png` next to the border image.

### Tools
- **Image converter** — Batch converts selected files, or a whole folder (optionally including subfolders), between common game asset formats.
  - Reads any image format your Pillow install can open (PNG, BMP, TGA, JPG, WEBP, GIF, TIFF, DDS, PSD, QOI, ICO, PCX and more). With a folder, non-image files are skipped automatically.
  - Writes: PNG, TGA (raw / RLE), WEBP (lossless / lossy), JPG, BMP, TIFF, DDS (uncompressed / DXT1 / DXT5), QOI, ICO
- **Recolor** — Makes color variants of sprites (enemy, team or day/night colors) for single images or whole folders of frames. A before/after preview shows the first image.
  - **Shift a color range** (shaded art, like renders): click the color to change in the before image, then set the **New color**, how wide a **Range** of hues to catch, and **Saturation**/**Brightness**. Shading is kept, the range blends out softly at its edges, and greys and whites are left alone. Two hue bars show which colors change and what they become.
  - **Swap exact colors** (pixel art): the image's colors are shown as swatches. Click a swatch (or a color in the image) and pick its replacement; right-click to undo it. Swapped swatches are split diagonally, old color and new.
  - **Save recolored** writes into the folder named in **Save into folder** next to the images, keeping file names and formats, so frame sets stay frame sets. Use a different folder per variant (`enemy_blue`, `enemy_green`, ...).
- **Fix edge halos** — Removes the dark outline engines draw around sprites (see below) from images you already have. Results go in a `halo_fixed` folder next to them, or over the originals if you choose.

The stitcher, resizer, dissector and converter have a **Fix edge halos** setting too (on by default), so what they write is already fixed.

## Install

```bash
git clone https://github.com/KillGorack/Spritesheet_Tools.git
cd Spritesheet_Tools
pip install --user -r requirements.txt
python3 sprite_sheet_tools.py
```

On Fedora, Tk is a separate package: `sudo dnf install python3-tkinter`

## Using it

Pick a tool in the sidebar. Its panel shows what it does, the input you've chosen, and its settings. Choose an input, adjust the settings and press the tool's button (**Run**, **Save APNG**, **Save tileset**, ...). Afterwards, **Open output folder** shows the results.

The input and settings stay put, so you can change a setting and run again. Settings are remembered between sessions. Jobs run in the background, so the window stays responsive. A short result message appears in the toolbar, and the details in the log at the bottom. The APNG maker, Tileset maker and Recolor show a live preview in the log's place instead.

| Shortcut | Action |
|---|---|
| Ctrl+O | Choose an input for the current tool |
| Ctrl+Enter | The tool's main button (Run, Save APNG, ...). Enter in a number field does the same (in the APNG maker it reloads the preview) |
| Space, ← → | APNG maker: play/pause, step through frames |
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

- **Output names** — `..._anim.png`, `..._tileset.png` and `tilesheet.png` are never overwritten: a `_1`, `_2`, ... suffix is added instead. Tools that write into a folder (`sources`, `halo_fixed`, Recolor's folder) and the resizer's `<name>_128.png` files do replace what's already there from an earlier run.

## Requirements

- Python 3 with Tk
- The packages in `requirements.txt`: customtkinter, pillow, apng, numpy
- Optional: `kdialog` or `zenity` for the desktop's own file and color pickers (otherwise Tk's basic ones are used)

Developed with Python 3.14, Pillow 12 and CustomTkinter 6. Older versions may work, but some output formats (DDS compression, QOI) need a recent Pillow.

## Configuration

Settings are stored in `~/.config/spritetools/config.json`, or `$XDG_CONFIG_HOME/spritetools/config.json` if that variable is set. Everything in it can be changed from the window, so you shouldn't need to edit it. If you do, edit it while the tool is closed.

## Project layout

    sprite_sheet_tools.py    entry point
    icons/                   toolbar icons (Lucide, ISC license: see icons/LICENSE)
    spritetools/
      config.py              settings: defaults, load, save
      ops/                   the image processing (no GUI code)
        alpha.py, apng.py, atlas.py, convert.py, frames.py, recolor.py, tileset.py, util.py
      ui/
        app.py               main window: sidebar, toolbar, tool panel, log
        tools.py             the tools: description, input, settings, how to run
        player.py            the animation preview player
        tileset_view.py      the tileset maker's border and tileset view
        recolor_view.py      the recolor tool's before/after, swatches and hue bars
        guides.py            an image with draggable guide lines
        imaging.py           showing images on canvases (scaling, checkerboard)
        theme.py             colors and icons
        filedialogs.py       desktop file and color pickers
        worker.py            runs tools in the background
    tests/                   tests for ops/, config and the tool list
      test_images/           a border image, fill tile and the tilesets made from them (reference output)

To add a tool, write the processing function in `ops/`. Then add a `Tool(...)` entry to `TOOLS` in `ui/tools.py`. Its sidebar entry and settings panel are built automatically. A new setting needs a field in `config.py` too.

## Tests

    python3 -m unittest

The tests use Python's built-in unittest, so they need nothing beyond the app's own packages. Most create their test images in a temporary folder and delete them afterwards; the tileset tests also rebuild the reference tilesets in `tests/test_images` and check they come out pixel for pixel the same.

## License

MIT, do whatever you want.. no biggie.. Not responsible for any damage or data loss.

Icons in `icons/` are from [Lucide](https://lucide.dev) (ISC license).
