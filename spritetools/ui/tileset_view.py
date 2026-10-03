import tkinter as tk

import customtkinter as ctk

from ..ops import tileset
from .imaging import fit_scale, on_checkerboard, scaled

GRAB_PX = 6  # how close to a guide line the mouse has to be to drag it


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
        self.photos = {}      # keep references so Tk doesn't drop the images
        self.border_geom = None  # (scale, x offset, y offset) of the border image on its canvas
        self.result_geom = None
        self.dragging = None  # the guide being dragged: "left", "right", "top" or "bottom"

        self.grid_columnconfigure(0, weight=2, uniform="views")
        self.grid_columnconfigure(1, weight=5, uniform="views")
        self.grid_rowconfigure(1, weight=1)
        self.border_caption = ctk.CTkLabel(self, text="", anchor="w")
        self.border_caption.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 0))
        self.result_caption = ctk.CTkLabel(self, text="", anchor="w")
        self.result_caption.grid(row=0, column=1, sticky="ew", padx=12, pady=(8, 0))
        self.border_canvas = tk.Canvas(self, highlightthickness=0, bd=0)
        self.border_canvas.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=(4, 10))
        self.result_canvas = tk.Canvas(self, highlightthickness=0, bd=0)
        self.result_canvas.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=(4, 10))
        for canvas in (self.border_canvas, self.result_canvas):
            canvas.bind("<Configure>", lambda e: self.redraw())

        self.border_canvas.bind("<Motion>", self._hover_border)
        self.border_canvas.bind("<Button-1>", self._grab)
        self.border_canvas.bind("<B1-Motion>", self._drag)
        self.border_canvas.bind("<ButtonRelease-1>", lambda e: setattr(self, "dragging", None))
        self.result_canvas.bind("<Motion>", self._hover_result)
        self.result_canvas.bind("<Leave>", lambda e: self._caption_result())

    def apply_theme(self, t):
        self.colors = t
        self.configure(fg_color=t["surface"])
        for canvas in (self.border_canvas, self.result_canvas):
            canvas.configure(bg=t["surface"])
        self.border_caption.configure(text_color=t["muted"])
        self.result_caption.configure(text_color=t["muted"])
        self.redraw()

    def show(self, data):
        self.data = data
        self.redraw()

    # ----- drawing --------------------------------------------------------

    def redraw(self):
        if not self.colors:
            return
        self._draw_border()
        self._draw_result()

    def _place(self, canvas, img):
        """Draw img centered and fitted on canvas; returns (scale, x, y) or None if it has no room yet."""
        cw, ch = canvas.winfo_width(), canvas.winfo_height()
        if cw < 10 or ch < 10:
            return None
        scale = fit_scale(img.size, (cw - 8, ch - 8))
        shown = scaled(img, scale)
        t = self.colors
        photo = on_checkerboard(shown, t["list_hover"], t["window"])
        self.photos[canvas] = photo
        x, y = (cw - shown.width) // 2, (ch - shown.height) // 2
        canvas.create_image(x, y, image=photo, anchor="nw")
        return scale, x, y

    def _draw_border(self):
        canvas, t = self.border_canvas, self.colors
        canvas.delete("all")
        self.border_geom = None
        border = self.data.get("border")
        self.border_caption.configure(text="Border · drag the red lines" if border else "")
        if border is None:
            return
        self.border_geom = self._place(canvas, border)
        if not self.border_geom:
            return
        for side, pos in self._guides().items():
            x0, y0, x1, y1 = self._guide_line(side, pos)
            canvas.create_line(x0, y0, x1, y1, fill=t["error"], width=2 if side == self.dragging else 1)

    def _guides(self):
        """The guide positions in image pixels, by side. 4-block has only the middle lines."""
        border, size = self.data["border"], self.data.get("border_size", 0)
        w, h = border.size
        if not 0 < size * 2 <= min(w, h):
            return {}
        if tileset.mode_for(w, h, size) == "4-block":
            return {"left": size, "top": size}
        return {"left": size, "right": w - size, "top": size, "bottom": h - size}

    def _guide_line(self, side, pos):
        scale, ox, oy = self.border_geom
        w, h = self.data["border"].size
        if side in ("left", "right"):
            x = ox + pos * scale
            return x, oy, x, oy + h * scale
        y = oy + pos * scale
        return ox, y, ox + w * scale, y

    def _draw_result(self):
        canvas, t = self.result_canvas, self.colors
        canvas.delete("all")
        self.result_geom = None
        result, message = self.data.get("result"), self.data.get("message")
        if result is None:
            self.result_caption.configure(text="Tileset")
            if message:
                canvas.create_text(canvas.winfo_width() // 2, canvas.winfo_height() // 2, text=message,
                                   fill=t["muted"], width=max(200, canvas.winfo_width() - 40),
                                   font=("TkDefaultFont", 12))
            return
        self.result_geom = self._place(canvas, result)
        if not self.result_geom:
            return
        scale, ox, oy = self.result_geom
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

    # ----- mouse ----------------------------------------------------------

    def _guide_near(self, x, y):
        if not self.border_geom or self.data.get("border") is None:
            return None
        best = None
        for side, pos in self._guides().items():
            x0, y0, x1, y1 = self._guide_line(side, pos)
            if side in ("left", "right"):
                distance = abs(x - x0) if y0 - GRAB_PX <= y <= y1 + GRAB_PX else None
            else:
                distance = abs(y - y0) if x0 - GRAB_PX <= x <= x1 + GRAB_PX else None
            if distance is not None and distance <= GRAB_PX and (best is None or distance < best[0]):
                best = (distance, side)
        return best[1] if best else None

    def _hover_border(self, event):
        side = self.dragging or self._guide_near(event.x, event.y)
        cursor = {"left": "sb_h_double_arrow", "right": "sb_h_double_arrow",
                  "top": "sb_v_double_arrow", "bottom": "sb_v_double_arrow"}.get(side, "")
        self.border_canvas.configure(cursor=cursor)

    def _grab(self, event):
        self.dragging = self._guide_near(event.x, event.y)
        if self.dragging:
            self._draw_border()

    def _drag(self, event):
        if not self.dragging or not self.border_geom:
            return
        scale, ox, oy = self.border_geom
        w, h = self.data["border"].size
        x, y = (event.x - ox) / scale, (event.y - oy) / scale
        size = {"left": x, "right": w - x, "top": y, "bottom": h - y}[self.dragging]
        size = max(1, min(round(size), min(w, h) // 2))
        if size != self.data.get("border_size"):
            self.on_border_size(size)

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
