import tkinter as tk

import customtkinter as ctk
from PIL import Image

from .imaging import checkerboard, fit_scale, scaled, to_photo


class Player(ctk.CTkFrame):
    """Plays a list of frames: a canvas with play/pause, step buttons and a frame counter.

    delay_ms, pingpong, zoom (0 = fit) and background can be changed while it plays.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.frames = []
        self.order = []        # frame indices in play order (ping-pong repeats some)
        self.position = 0      # index into order
        self.playing = False
        self.job = None
        self.cache = {}        # frame index -> PhotoImage at the current size and background
        self.delay_ms = 70
        self.pingpong = False
        self.zoom = 0
        self.background = "checker"
        self.colors = {}
        self.backdrops = {}    # (size, background) -> backdrop image

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))
        self.canvas.bind("<Configure>", lambda e: self.redraw(clear=True))

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=10, pady=8)
        self.play_btn = ctk.CTkButton(bar, text="Play", width=80, command=self.toggle)
        self.play_btn.pack(side="left")
        self.prev_btn = ctk.CTkButton(bar, text="‹", width=36, command=lambda: self.step(-1))
        self.prev_btn.pack(side="left", padx=(8, 0))
        self.next_btn = ctk.CTkButton(bar, text="›", width=36, command=lambda: self.step(1))
        self.next_btn.pack(side="left", padx=(4, 0))
        self.counter = ctk.CTkLabel(bar, text="")
        self.counter.pack(side="left", padx=12)
        self.info = ctk.CTkLabel(bar, text="")
        self.info.pack(side="right")

    # ----- setup ------------------------------------------------------------

    def apply_theme(self, t):
        self.colors = t
        self.backdrops = {}
        self.configure(fg_color=t["surface"])
        self.canvas.configure(bg=t["surface"])
        style = dict(fg_color=t["button"], hover_color=t["button_hover"], text_color=t["text"])
        for btn in (self.play_btn, self.prev_btn, self.next_btn):
            btn.configure(**style)
        self.counter.configure(text_color=t["text"])
        self.info.configure(text_color=t["muted"])
        self.redraw(clear=True)

    def set_frames(self, frames):
        self.frames = frames
        self.cache = {}
        self.position = 0
        self._update_order()
        w = max(f.width for f in frames)
        h = max(f.height for f in frames)
        self.info.configure(text=f"{len(frames)} frames · {w}x{h}")
        self.play()

    def set_playback(self, delay_ms=None, pingpong=None, zoom=None, background=None):
        if delay_ms is not None:
            self.delay_ms = delay_ms
        if pingpong is not None and pingpong != self.pingpong:
            frame = self.order[self.position] if self.order else 0
            self.pingpong = pingpong
            self._update_order()
            self.position = self.order.index(frame) if frame in self.order else 0
        redraw = False
        if zoom is not None and zoom != self.zoom:
            self.zoom, redraw = zoom, True
        if background is not None and background != self.background:
            self.background, redraw = background, True
        if redraw:
            self.redraw(clear=True)

    def _update_order(self):
        n = len(self.frames)
        self.order = list(range(n)) + (list(range(n - 2, 0, -1)) if self.pingpong and n > 2 else [])

    # ----- playback ---------------------------------------------------------

    def play(self):
        if not self.frames:
            return
        self.playing = True
        self.play_btn.configure(text="Pause")
        self._schedule()
        self.redraw()

    def pause(self):
        self.playing = False
        self.play_btn.configure(text="Play")
        if self.job:
            self.after_cancel(self.job)
            self.job = None

    def toggle(self):
        self.pause() if self.playing else self.play()

    def step(self, delta):
        """Show the next/previous frame (in file order, not the ping-pong order) and pause."""
        if not self.frames:
            return
        self.pause()
        frame = (self.order[self.position] + delta) % len(self.frames)
        self.position = self.order.index(frame)
        self.redraw()

    def _schedule(self):
        if self.job:
            self.after_cancel(self.job)
        self.job = self.after(self.delay_ms, self._tick)

    def _tick(self):
        self.job = None
        if not self.playing or not self.order:
            return
        self.position = (self.position + 1) % len(self.order)
        self.redraw()
        self._schedule()

    # ----- drawing ----------------------------------------------------------

    def scale(self):
        """Display scale: zoom (shrunk if it doesn't fit), or for fit the largest whole
        number that fits (sharp pixels), or below 1 if even 1x doesn't fit."""
        size = (max(f.width for f in self.frames), max(f.height for f in self.frames))
        return fit_scale(size, (self.canvas.winfo_width(), self.canvas.winfo_height()), self.zoom)

    def redraw(self, clear=False):
        if clear:
            self.cache = {}
        self.canvas.delete("all")
        if not self.frames or self.canvas.winfo_width() < 2:
            self.counter.configure(text="")
            return
        index = self.order[self.position]
        if index not in self.cache:
            self.cache[index] = self._render(self.frames[index])
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        self.canvas.create_image(cw // 2, ch // 2, image=self.cache[index])
        self.counter.configure(text=f"Frame {index + 1} / {len(self.frames)}")

    def _render(self, frame):
        frame = scaled(frame, self.scale())
        backdrop = self._backdrop(frame.size)
        backdrop.alpha_composite(frame)
        return to_photo(backdrop.convert("RGB"))

    def _backdrop(self, size):
        key = (size, self.background)
        if key not in self.backdrops:
            self.backdrops[key] = self._make_backdrop(size)
        return self.backdrops[key].copy()

    def _make_backdrop(self, size):
        t = self.colors
        if self.background == "dark":
            return Image.new("RGBA", size, (30, 30, 30, 255))
        if self.background == "light":
            return Image.new("RGBA", size, (230, 230, 230, 255))
        # checkerboard in two shades of the theme
        return checkerboard(size, t.get("list_hover", "#333333"), t.get("surface", "#171717"))
