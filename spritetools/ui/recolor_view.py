import tkinter as tk

import customtkinter as ctk
import numpy as np
from PIL import Image

from ..ops import recolor
from .imaging import fit_scale, on_checkerboard, scaled, to_photo

SWATCH_PX = 24
SWATCH_GAP = 4
STRIP_PX = 64  # height of the swatch / hue bar strip


class RecolorView(ctk.CTkFrame):
    """Before and after images, and under them the palette swatches (swap mode) or two
    hue bars (shift mode).

    show() takes what the tool's render() returns: {"mode": "shift" or "swap", "before",
    "after": images or None, "palette": [((r, g, b), count)], "mapping": {"#from": "#to"},
    "hue", "range", "new_hue": numbers, "message": text or None}.

    pick(rgb) is called when the before image is clicked, swatch(rgb) when a swatch is
    clicked, unswatch(rgb) when one is right-clicked.
    """

    def __init__(self, master, pick, swatch, unswatch, **kwargs):
        super().__init__(master, **kwargs)
        self.pick, self.swatch, self.unswatch = pick, swatch, unswatch
        self.data = {}
        self.colors = {}
        self.photos = {}
        self.before_geom = None    # (scale, x, y) of the before image on its canvas
        self.swatch_boxes = []     # ((x0, y0, x1, y1), rgb) of the drawn swatches

        self.grid_columnconfigure((0, 1), weight=1, uniform="views")
        self.grid_rowconfigure(1, weight=1)
        self.before_caption = ctk.CTkLabel(self, text="", anchor="w")
        self.before_caption.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 0))
        self.after_caption = ctk.CTkLabel(self, text="", anchor="w")
        self.after_caption.grid(row=0, column=1, sticky="ew", padx=12, pady=(8, 0))
        self.before_canvas = tk.Canvas(self, highlightthickness=0, bd=0, cursor="crosshair")
        self.before_canvas.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=(4, 4))
        self.after_canvas = tk.Canvas(self, highlightthickness=0, bd=0)
        self.after_canvas.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=(4, 4))
        self.strip_caption = ctk.CTkLabel(self, text="", anchor="w")
        self.strip_caption.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12)
        self.strip = tk.Canvas(self, highlightthickness=0, bd=0, height=STRIP_PX)
        self.strip.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))
        for canvas in (self.before_canvas, self.after_canvas, self.strip):
            canvas.bind("<Configure>", lambda e: self.redraw())
        self.before_canvas.bind("<Button-1>", self._clicked_image)
        self.strip.bind("<Button-1>", lambda e: self._clicked_swatch(e, self.swatch))
        self.strip.bind("<Button-3>", lambda e: self._clicked_swatch(e, self.unswatch))
        self.strip.bind("<Motion>", self._hover_strip)
        self.strip.bind("<Leave>", lambda e: self._caption_strip())

    def apply_theme(self, t):
        self.colors = t
        self.configure(fg_color=t["surface"])
        for canvas in (self.before_canvas, self.after_canvas, self.strip):
            canvas.configure(bg=t["surface"])
        for label in (self.before_caption, self.after_caption, self.strip_caption):
            label.configure(text_color=t["muted"])
        self.redraw()

    def show(self, data):
        self.data = data
        self.redraw()

    # ----- drawing --------------------------------------------------------

    def redraw(self):
        if not self.colors:
            return
        before, after = self.data.get("before"), self.data.get("after")
        swap = self.data.get("mode") == "swap"
        self.before_caption.configure(text=("Before · click a color to " + ("change it" if swap else "pick it"))
                                      if before else "")
        self.after_caption.configure(text="After" if after else "")
        self.before_geom = self._draw_image(self.before_canvas, before, self.data.get("message"))
        self._draw_image(self.after_canvas, after)
        self._draw_strip()

    def _draw_image(self, canvas, img, message=None):
        canvas.delete("all")
        cw, ch = canvas.winfo_width(), canvas.winfo_height()
        if cw < 10 or ch < 10:
            return None
        if img is None:
            if message:
                canvas.create_text(cw // 2, ch // 2, text=message, fill=self.colors["muted"],
                                   width=max(200, cw - 40), font=("TkDefaultFont", 12))
            return None
        scale = fit_scale(img.size, (cw - 8, ch - 8))
        shown = scaled(img, scale)
        self.photos[canvas] = on_checkerboard(shown, self.colors["list_hover"], self.colors["window"])
        x, y = (cw - shown.width) // 2, (ch - shown.height) // 2
        canvas.create_image(x, y, image=self.photos[canvas], anchor="nw")
        return scale, x, y

    def _draw_strip(self):
        self.strip.delete("all")
        self.swatch_boxes = []
        if self.data.get("before") is None:
            self.strip_caption.configure(text="")
            return
        if self.data.get("mode") == "swap":
            self._draw_swatches()
        else:
            self._draw_hue_bars()
        self._caption_strip()

    def _draw_swatches(self):
        t, palette = self.colors, self.data.get("palette", [])
        mapping = self.data.get("mapping", {})
        width = self.strip.winfo_width()
        per_row = max(1, (width + SWATCH_GAP) // (SWATCH_PX + SWATCH_GAP))
        fits = per_row * (STRIP_PX // (SWATCH_PX + SWATCH_GAP))
        for i, (rgb, count) in enumerate(palette[:fits]):
            x = (i % per_row) * (SWATCH_PX + SWATCH_GAP)
            y = (i // per_row) * (SWATCH_PX + SWATCH_GAP) + 2
            box = (x, y, x + SWATCH_PX, y + SWATCH_PX)
            src = recolor.rgb_to_hex(rgb)
            self.strip.create_rectangle(*box, fill=src, outline=t["scrollbar"])
            if src in mapping:
                # the new color fills the bottom-right half, and the swatch gets a bright outline
                self.strip.create_polygon(box[2], box[1], box[2], box[3], box[0], box[3],
                                          fill=mapping[src], outline="")
                self.strip.create_rectangle(*box, outline=t["text"], width=2)
            self.swatch_boxes.append((box, rgb))

    def _draw_hue_bars(self):
        width = self.strip.winfo_width() - 2
        if width < 10:
            return
        hue, spread, new_hue = self.data["hue"], self.data["range"], self.data["new_hue"]
        hues = np.linspace(0, 360, width, endpoint=False)
        # the weight shift_hue gives each hue, at full saturation
        weight = np.clip((spread + recolor.FEATHER_DEG - recolor.hue_distance(hues, hue)) / recolor.FEATHER_DEG, 0, 1)
        before = recolor.hsv_to_rgb(hues, np.ones(width), 0.35 + 0.65 * weight)  # dim what's not caught
        after = recolor.hsv_to_rgb(hues, np.ones(width), np.ones(width))
        after = after + (recolor.hsv_to_rgb(hues + (new_hue - hue), np.ones(width), np.ones(width)) - after) * weight[:, None]
        bar_h = (STRIP_PX - 14) // 2
        for row, rgb in enumerate((before, after)):
            img = Image.fromarray(np.repeat((rgb * 255).astype(np.uint8)[None], bar_h, axis=0), "RGB")
            self.photos[f"bar{row}"] = to_photo(img)
            self.strip.create_image(1, 2 + row * (bar_h + 10), image=self.photos[f"bar{row}"], anchor="nw")

    def _caption_strip(self, hovered=None):
        if self.data.get("mode") == "swap":
            palette, mapping = self.data.get("palette", []), self.data.get("mapping", {})
            if hovered:
                src = recolor.rgb_to_hex(hovered)
                count = dict(palette).get(hovered, 0)
                text = f"{src} · {count} px" + (f" → {mapping[src]} (right-click to undo)" if src in mapping else "")
            else:
                text = f"{len(palette)} colors · click one to change it, right-click to undo"
                if len(palette) > len(self.swatch_boxes):
                    text += f" · showing the {len(self.swatch_boxes)} most used"
                if len(palette) > 256:
                    text += " · that's a lot: shaded art usually works better with Shift a color range"
        else:
            text = "Top: the colors that change (the rest dimmed) · bottom: what they become"
        self.strip_caption.configure(text=text)

    # ----- mouse ----------------------------------------------------------

    def _clicked_image(self, event):
        before = self.data.get("before")
        if not self.before_geom or before is None:
            return
        scale, ox, oy = self.before_geom
        x, y = int((event.x - ox) / scale), int((event.y - oy) / scale)
        if 0 <= x < before.width and 0 <= y < before.height:
            r, g, b, a = before.convert("RGBA").getpixel((x, y))
            if a:
                self.pick((r, g, b))

    def _swatch_at(self, x, y):
        return next((rgb for (x0, y0, x1, y1), rgb in self.swatch_boxes if x0 <= x < x1 and y0 <= y < y1), None)

    def _clicked_swatch(self, event, action):
        rgb = self._swatch_at(event.x, event.y)
        if rgb:
            action(rgb)

    def _hover_strip(self, event):
        if self.data.get("mode") == "swap":
            rgb = self._swatch_at(event.x, event.y)
            self.strip.configure(cursor="hand2" if rgb else "")
            self._caption_strip(rgb)
