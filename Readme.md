# Spritesheet Tools

A lightweight GUI toolkit for working with spritesheets, animation frames, and APNGs.  
Built with Python, Tkinter, Pillow, and apng, this tool provides fast utilities for common 2D asset workflows.

## Features

### APNG Tools
- **APNG from Atlas** — Slice a spritesheet into rows and generate looping APNG previews.
- **APNG from Frames** — Build an APNG from a sequence of image files.
- **APNG from Frames (Ping‑Pong)** — Creates a forward‑and‑reverse looping animation.

### Spritesheet Utilities
- **Atlas Dissector** — Cuts a spritesheet into individual frames based on a fixed frame size.
- **Orthogonal Resizer** — Rescales a 512‑based spritesheet into multiple target resolutions (256, 128, 64, 32, 16).
- **Frame Stitcher (Horizontal / Vertical)** — Combines multiple frames into a single tilesheet.

### Format Conversion
- **BMP → PNG Converter** — Recursively converts `.bmp` files inside a folder to `.png`, with optional overwrite and delete‑original behavior.


### Assumptions & Notes

- **APNG Tools (all three)** — These assume each frame is **128×128 pixels**.  
  You can change this in the config: `FRAME_SIZE`.

- **Atlas Dissector** — Also assumes **128×128** frames.  
  Controlled by the same `FRAME_SIZE` setting.

- **Orthogonal Resizer** — Assumes your spritesheet is built from **512×512 base frames**.  
  This is controlled by `BASE_FRAME_SIZE`.

  **Important:**  
  This tool expects a *perfectly clean* spritesheet.  
  Any gutters, padding, spacing, or margins between frames will break the scaling math.  
  If your sheet has baked‑in spacing, resize manually using a calculator.

- **Frame Stitcher** — All input images must be **exactly the same size**.  
  The tool does not attempt to normalize or resize mismatched frames.

- **BMP → PNG Converter** — A simple utility added mainly for convenience after moving from Windows to Linux. If i needed more I would have built this a little more procedural. (maybe later)


## Requirements
Install dependencies:
pip install pillow apng

Requires Python 3.x.

## License

MIT, do whatever you want.. no biggie.. Not responsible for any damage or data loss.