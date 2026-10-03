import tkinter as tk

import customtkinter as ctk

from ..ops import tileset
from .guides import GuidedImage
from .imaging import fit_scale, on_checkerboard, scaled


class TilesetView(ctk.CTkFrame):
    """The border image with draggable guide lines, next to the tileset it makes.

    show() takes what the tool's render() returns: {"border": image or None,
    "border_size": int, "result": tileset image or None, "layout": (mode, columns, rows)
    or None, "message": text to show instead of the tileset, or None}.
    Dragging a guide calls on_border_size(new size).
    """

    def __init__(self, master, on_border_size, **kwargs):
        super().__init__(master, **kwargs)
        self.on_border_size = on_border_size
        self.data = {}
        self.colors = {}
        self.photo = None
        self.result_geom = None  # (scale, x offset, y offset) of the tileset on its canvas

        self.grid_columnconfigure(0, weight=2, uniform="views")
        self.grid_columnconfigure(1, weight=5, uniform="views")
        self.grid_rowconfigure(1, weight=1)
        self.border_caption = ctk.CTkLabel(self, text="", anchor="w")
        self.border_caption.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 0))
        self.result_caption = ctk.CTkLabel(self, text="", anchor="w")
        self.result_caption.grid(row=0, column=1, sticky="ew", padx=12, pady=(8, 0))
        self.border_view = GuidedImage(self, on_drag=self._dragged)
        self.border_view.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=(4, 10))
        self.result_canvas = tk.Canvas(self, highlightthickness=0, bd=0)
        self.result_canvas.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=(4, 10))
        self.result_canvas.bind("<Configure>", lambda e: self._draw_result())
        self.result_canvas.bind("<Motion>", self._hover_result)
        self.result_canvas.bind("<Leave>", lambda e: self._caption_result())

    def apply_theme(self, t):
        self.colors = t
        self.configure(fg_color=t["surface"])
        self.result_canvas.configure(bg=t["surface"])
        self.border_caption.configure(text_color=t["muted"])
        self.result_caption.configure(text_color=t["muted"])
        self.border_view.apply_theme(t)
        self._draw_result()

    def show(self, data):
        self.data = data
        border = data.get("border")
        self.border_caption.configure(text="Border · drag the red lines" if border else "")
        self.border_view.show(border, self._guides())
        self._draw_result()

    # ----- border ---------------------------------------------------------

    def _guides(self):
        """Guide positions in image pixels. 4-block has only the middle lines."""
        border, size = self.data.get("border"), self.data.get("border_size", 0)
        if border is None:
            return {}
        w, h = border.size
        if not 0 < size * 2 <= min(w, h):
            return {}
        if tileset.mode_for(w, h, size) == "4-block":
            return {"left": size, "top": size}
        return {"left": size, "right": w - size, "top": size, "bottom": h - size}

    def _dragged(self, side, pos):
        w, h = self.data["border"].size
        size = {"left": pos, "right": w - pos, "top": pos, "bottom": h - pos}[side]
        size = max(1, min(round(size), min(w, h) // 2))
        if size != self.data.get("border_size"):
            self.on_border_size(size)

    # ----- tileset --------------------------------------------------------

    def _draw_result(self):
        canvas, t = self.result_canvas, self.colors
        canvas.delete("all")
        self.result_geom = None
        cw, ch = canvas.winfo_width(), canvas.winfo_height()
        if not t or cw < 10 or ch < 10:
            return
        result, message = self.data.get("result"), self.data.get("message")
        if result is None:
            self.result_caption.configure(text="Tileset")
            if message:
                canvas.create_text(cw // 2, ch // 2, text=message, fill=t["muted"],
                                   width=max(200, cw - 40), font=("TkDefaultFont", 12))
            return
        scale = fit_scale(result.size, (cw - 8, ch - 8))
        shown = scaled(result, scale)
        self.photo = on_checkerboard(shown, t["list_hover"], t["window"])
        ox, oy = (cw - shown.width) // 2, (ch - shown.height) // 2
        canvas.create_image(ox, oy, image=self.photo, anchor="nw")
        self.result_geom = (scale, ox, oy)
        mode, cols, rows = self.data["layout"]
        tw, th = result.width / cols * scale, result.height / rows * scale
        for c in range(1, cols):
            canvas.create_line(ox + c * tw, oy, ox + c * tw, oy + rows * th, fill=t["scrollbar"])
        for r in range(1, rows):
            canvas.create_line(ox, oy + r * th, ox + cols * tw, oy + r * th, fill=t["scrollbar"])
        self._caption_result()

    def _caption_result(self, tile=None):
        layout = self.data.get("layout")
        if not layout:
            return
        mode, cols, rows = layout
        text = f"Tileset · {mode}, {cols} × {rows} tiles"
        if tile is not None:
            recipes = tileset.LAYOUTS[mode][0]
            pieces = " ".join(str(n) for n in recipes[tile]) or "none (fill only)"
            text += f"   ·   tile {tile + 1}: pieces {pieces}"
        self.result_caption.configure(text=text)

    def _hover_result(self, event):
        if not self.result_geom:
            return
        scale, ox, oy = self.result_geom
        mode, cols, rows = self.data["layout"]
        result = self.data["result"]
        col = int((event.x - ox) / (result.width / cols * scale))
        row = int((event.y - oy) / (result.height / rows * scale))
        inside = 0 <= col < cols and 0 <= row < rows and event.x >= ox and event.y >= oy
        index = row * cols + col
        self._caption_result(index if inside and index < len(tileset.LAYOUTS[mode][0]) else None)
