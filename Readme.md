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

## Requirements

Install dependencies:

pip install pillow apng

Requires Python 3.x.

## License

MIT, do whatever you want.. no biggie.. Not responsible for any damage or data loss.