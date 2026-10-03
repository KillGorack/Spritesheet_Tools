import tkinter as tk

from .imaging import fit_scale, on_checkerboard, scaled

GRAB_PX = 6  # how close to a guide line the mouse has to be to drag it
CURSORS = {"left": "sb_h_double_arrow", "right": "sb_h_double_arrow",
           "top": "sb_v_double_arrow", "bottom": "sb_v_double_arrow"}


class GuidedImage(tk.Canvas):
    """An image with draggable guide lines over it.

    Guides are {side: position in image pixels}: "left"/"right" are vertical lines at
    that x, "top"/"bottom" horizontal lines at that y. Dragging one calls
    on_drag(side, position) with the new (unrounded) position; the owner works out what
    that means and calls show() again.
    """

    def __init__(self, master, on_drag, **kwargs):
        super().__init__(master, highlightthickness=0, bd=0, **kwargs)
        self.on_drag = on_drag
        self.image = None
        self.guides = {}
        self.colors = {}
        self.photo = None
        self.geom = None      # (scale, x offset, y offset) of the image on the canvas
        self.dragging = None  # side of the guide being dragged
        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<Motion>", self._hover)
        self.bind("<Button-1>", self._grab)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<ButtonRelease-1>", self._release)

    def apply_theme(self, t):
        self.colors = t
        self.configure(bg=t["surface"])
        self.redraw()

    def show(self, image, guides):
        self.image, self.guides = image, guides
        self.redraw()

    def redraw(self):
        self.delete("all")
        self.geom = None
        cw, ch = self.winfo_width(), self.winfo_height()
        if self.image is None or not self.colors or cw < 10 or ch < 10:
            return
        t = self.colors
        scale = fit_scale(self.image.size, (cw - 8, ch - 8))
        shown = scaled(self.image, scale)
        self.photo = on_checkerboard(shown, t["list_hover"], t["window"])
        x, y = (cw - shown.width) // 2, (ch - shown.height) // 2
        self.create_image(x, y, image=self.photo, anchor="nw")
        self.geom = (scale, x, y)
        for side, pos in self.guides.items():
            self.create_line(*self._line(side, pos), fill=t["error"], width=2 if side == self.dragging else 1)

    def _line(self, side, pos):
        scale, ox, oy = self.geom
        w, h = self.image.size
        if side in ("left", "right"):
            x = ox + pos * scale
            return x, oy, x, oy + h * scale
        y = oy + pos * scale
        return ox, y, ox + w * scale, y

    def _guide_near(self, x, y):
        if not self.geom:
            return None
        best = None
        for side, pos in self.guides.items():
            x0, y0, x1, y1 = self._line(side, pos)
            if side in ("left", "right"):
                distance = abs(x - x0) if y0 - GRAB_PX <= y <= y1 + GRAB_PX else None
            else:
                distance = abs(y - y0) if x0 - GRAB_PX <= x <= x1 + GRAB_PX else None
            if distance is not None and distance <= GRAB_PX and (best is None or distance < best[0]):
                best = (distance, side)
        return best[1] if best else None

    def _hover(self, event):
        self.configure(cursor=CURSORS.get(self.dragging or self._guide_near(event.x, event.y), ""))

    def _grab(self, event):
        self.dragging = self._guide_near(event.x, event.y)
        if self.dragging:
            self.redraw()

    def _drag(self, event):
        if not self.dragging or not self.geom:
            return
        scale, ox, oy = self.geom
        if self.dragging in ("left", "right"):
            self.on_drag(self.dragging, (event.x - ox) / scale)
        else:
            self.on_drag(self.dragging, (event.y - oy) / scale)

    def _release(self, event):
        self.dragging = None
        self.redraw()
