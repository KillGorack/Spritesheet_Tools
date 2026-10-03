import base64
import io
import tkinter as tk
from pathlib import Path

from PIL import Image

ICON_DIR = Path(__file__).resolve().parents[2] / "icons"  # Lucide icons (ISC), see icons/LICENSE

# Same palettes as LULIM
THEMES = {
    "dark": {
        "window": "#262626",
        "surface": "#171717",
        "text": "#b1b1b1",
        "muted": "#8f8f8f",
        "error": "#f87171",
        "button": "#525252",
        "button_hover": "#737373",
        "list_hover": "#333333",
        "scrollbar": "#404040",
        "scrollbar_hover": "#525252",
    },
    "light": {
        "window": "#bdb5a3",
        "surface": "#ded6c3",
        "text": "#332d24",
        "muted": "#6b6252",
        "error": "#a33a2a",
        "button": "#8c806b",
        "button_hover": "#756a58",
        "list_hover": "#cbc2ae",
        "scrollbar": "#a89e8a",
        "scrollbar_hover": "#8c806b",
    },
}

FONT = ("TkDefaultFont", 13)
TITLE_FONT = ("TkDefaultFont", 15, "bold")
HEADING_FONT = ("TkDefaultFont", 11, "bold")
LOG_FONT = ("Monospace", 11)


def load_icon(name, color, size=18):
    """Load a Lucide icon from icons/ as a Tk image, tinted to the given color.

    The PNGs are white masks; only their alpha is used. Built as PNG data for
    tk.PhotoImage so it doesn't need PIL.ImageTk (a separate distro package on Fedora).
    """
    mask = Image.open(ICON_DIR / f"{name}.png").convert("RGBA").getchannel("A")
    mask = mask.resize((size, size), Image.Resampling.LANCZOS)
    img = Image.new("RGBA", (size, size), color)
    img.putalpha(mask)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return tk.PhotoImage(data=base64.b64encode(buf.getvalue()))
