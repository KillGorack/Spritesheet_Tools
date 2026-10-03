import copy
import math
import os
import subprocess
import tkinter as tk
import warnings
from pathlib import Path

import customtkinter as ctk

from ..config import Config
from ..ops.convert import readable_extensions
from . import filedialogs
from .theme import FONT, HEADING_FONT, LOG_FONT, THEMES, TITLE_FONT, load_icon
from .player import Player
from .tileset_view import TilesetView
from .tools import TOOLS, TOOLS_BY_KEY
from .worker import Worker

WINDOW_ICON = Path(__file__).resolve().parents[2] / "icon.png"
INPUT_BUTTONS = {  # input mode: (button text, file dialog mode)
    "file": ("Choose file…", "file"),
    "files": ("Choose files…", "files"),
    "folder": ("Choose folder…", "folder"),
    "frames": ("Choose frames…", "files"),
    "sheet": ("Choose sheet…", "file"),
}
RELOAD_SETTINGS = ("sheet_columns", "sheet_rows", "apng_mode", "preview_row")  # change what the preview loads


def short_path(path):
    """Path with the home folder shown as ~."""
    home = str(Path.home())
    return "~" + path[len(home):] if path == home or path.startswith(home + os.sep) else path


class App(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.config_data = Config.load()
        self.theme_name = self.config_data.theme
        self.tool = TOOLS_BY_KEY.get(self.config_data.last_tool, TOOLS[0])
        patterns = ["*" + ext for ext in readable_extensions()]
        self.patterns = patterns + [p.upper() for p in patterns]
        self.inputs = {}       # tool key -> {slot key: chosen paths} (a folder is a one-item list)
        self.output_dirs = {}  # tool key -> folder its last run wrote to
        self.fields = {}       # option -> (variable, widget) for the panel on show
        self.running = None    # (tool key, "run" or "save") of the task that's running
        self.reload_job = None
        self.view_job = None
        self.dialog_open = False
        self.close_armed = False
        self.note = self.note_job = None

        self.geometry("960x680")
        self.minsize(940, 560)
        self.title("Sprite tools")
        try:
            self.icon = tk.PhotoImage(file=str(WINDOW_ICON))
            self.iconphoto(True, self.icon)
        except tk.TclError:
            pass

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # toolbar: sidebar toggle and tool name on the left, notes and theme on the right
        self.toolbar = ctk.CTkFrame(self)
        self.toolbar.grid(row=0, column=1, sticky="ew", padx=10, pady=10)
        self.toolbar.grid_columnconfigure(2, weight=1)
        self.sidebar_btn = ctk.CTkButton(self.toolbar, text="", width=32, command=self.toggle_sidebar)
        self.sidebar_btn.grid(row=0, column=0, padx=(6, 2), pady=6)
        self.title_label = ctk.CTkLabel(self.toolbar, text="", font=TITLE_FONT, anchor="w")
        self.title_label.grid(row=0, column=1, padx=8)
        self.status = ctk.CTkLabel(self.toolbar, text="", anchor="e")
        self.status.grid(row=0, column=2, sticky="e", padx=8)
        self.theme_btn = ctk.CTkButton(self.toolbar, text="", width=32, command=self.toggle_theme)
        self.theme_btn.grid(row=0, column=3, padx=(0, 6), pady=6)

        # the selected tool: description, input, settings and Run
        self.panel = ctk.CTkFrame(self)
        self.panel.grid(row=1, column=1, sticky="ew", padx=10, pady=(0, 10))
        # columns: label, widget, label, widget (settings in two columns), stretch, input buttons
        self.panel.grid_columnconfigure(4, weight=1)
        self.panel.bind("<Configure>", lambda e: self.wrap_description())

        self.log_box = ctk.CTkTextbox(self, wrap="word", state="disabled", font=LOG_FONT)
        self.log_box.grid(row=2, column=1, sticky="nsew", padx=10, pady=(0, 10))
        self.log_box._textbox.configure(padx=8, pady=6)
        # views that take the log's place for some tools (Tool.view_name)
        self.player = Player(self)
        self.tileset_view = TilesetView(self, on_border_size=self.set_border_size)
        self.views = {"log": self.log_box, "player": self.player, "tileset": self.tileset_view}
        for view in (self.player, self.tileset_view):
            view.grid(row=2, column=1, sticky="nsew", padx=10, pady=(0, 10))
            view.grid_remove()

        # sidebar: search and the tool list
        self.sidebar = ctk.CTkFrame(self, width=230, corner_radius=0, fg_color="transparent")
        self.sidebar.grid(row=0, column=0, rowspan=3, sticky="ns")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(0, weight=1)
        self.sidebar.grid_columnconfigure(0, weight=1)
        self.container = ctk.CTkFrame(self.sidebar)
        self.container.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=10)
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(1, weight=1)
        self.search = ctk.CTkEntry(self.container, placeholder_text="Search tools", border_width=0)
        self.search.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        self.search.bind("<KeyRelease>", lambda e: self.refresh_list())
        self.search.bind("<Return>", lambda e: self.open_first_match())
        self.search.bind("<Escape>", lambda e: self.clear_search())
        self.tool_list = ctk.CTkScrollableFrame(self.container, fg_color="transparent")
        self.tool_list.grid(row=1, column=0, sticky="nsew", padx=5, pady=(4, 10))
        self.tool_list.grid_columnconfigure(0, weight=1)
        self.tool_list._parent_canvas.bind(
            "<Configure>", lambda e: self.after_idle(self.update_scrollbar), add="+")
        if self.config_data.sidebar_hidden:
            self.sidebar.grid_remove()

        self.bind("<Control-b>", lambda e: self.toggle_sidebar())
        self.bind("<Control-f>", lambda e: self.focus_search())
        self.bind("<Control-o>", lambda e: self.choose_input(self.tool.input_slots()[0].modes[0]))
        self.bind("<Control-Return>", lambda e: self.run_tool("save" if self.tool.save else "run"))
        self.bind("<space>", lambda e: self.player_key(self.player.toggle))
        self.bind("<Left>", lambda e: self.player_key(lambda: self.player.step(-1)))
        self.bind("<Right>", lambda e: self.player_key(lambda: self.player.step(1)))
        self.protocol("WM_DELETE_WINDOW", self.close)

        self.worker = Worker(self, self.log)
        self.apply_theme()

    # ----- settings -------------------------------------------------------

    def save_config(self):
        try:
            self.config_data.save()
        except OSError as e:
            self.log(f"Warning: Could not save config: {e}")

    def collect_options(self):
        """Copy the panel's settings into the config. Returns messages for invalid ones,
        which are marked red and keep their old value."""
        errors = []
        t = self.t
        for option, (var, widget) in self.fields.items():
            if not widget.winfo_exists() or not self.option_enabled(option):
                continue
            try:
                value = option.parse(var.get())
            except ValueError as e:
                errors.append(str(e))
                widget.configure(border_width=1, border_color=t["error"])
                continue
            if option.kind in ("int", "int_list"):
                widget.configure(border_width=0)
            setattr(self.config_data, option.key, value)
        return errors

    def current_settings(self):
        """A copy of the config with the panel's valid values applied (nothing is saved or marked)."""
        cfg = copy.deepcopy(self.config_data)
        for option, (var, widget) in self.fields.items():
            try:
                setattr(cfg, option.key, option.parse(var.get()))
            except (ValueError, tk.TclError):
                pass
        return cfg

    def option_enabled(self, option):
        """False for a setting that doesn't apply with the current value of another (enabled_when)."""
        cfg = self.current_settings() if option.enabled_when else None
        return all(getattr(cfg, key) in allowed for key, allowed in (option.enabled_when or {}).items())

    def update_field_states(self, *_):
        t = self.t
        for option, (var, widget) in self.fields.items():
            if option.enabled_when:
                on = self.option_enabled(option)
                widget.configure(state="normal" if on else "disabled", text_color=t["text"] if on else t["muted"])
                if option in self.field_labels:
                    self.field_labels[option].configure(text_color=t["text"] if on else t["muted"])

    # ----- look -----------------------------------------------------------

    def toggle_theme(self):
        self.theme_name = "light" if self.theme_name == "dark" else "dark"
        self.config_data.theme = self.theme_name
        self.save_config()
        self.apply_theme()

    def apply_theme(self):
        t = self.t = THEMES[self.theme_name]
        self.collect_options()  # the panel is rebuilt below; keep what was typed
        ctk.set_appearance_mode(self.theme_name)
        self.configure(fg_color=t["window"])
        for frame in (self.toolbar, self.panel, self.container):
            frame.configure(fg_color=t["surface"])
        self.title_label.configure(text_color=t["text"])
        self.log_box.configure(fg_color=t["surface"], text_color=t["text"],
                               scrollbar_button_color=t["scrollbar"],
                               scrollbar_button_hover_color=t["scrollbar_hover"])
        self.search.configure(fg_color=t["list_hover"], text_color=t["text"],
                              placeholder_text_color=t["muted"])
        self.tool_list.configure(fg_color=t["surface"], scrollbar_button_color=t["scrollbar"],
                                 scrollbar_button_hover_color=t["scrollbar_hover"])
        # flat icon buttons on the bar: just the icon, highlighted on hover
        size = round(18 * self.theme_btn._get_widget_scaling())
        self._icons = {}  # keep references so Tk doesn't drop the images
        # the theme button shows the theme you'd switch to: sun while dark, moon while light
        theme_icon = "sun" if self.theme_name == "dark" else "moon"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # plain Tk images: we scale them ourselves
            for btn, name in ((self.sidebar_btn, "panel-left"), (self.theme_btn, theme_icon)):
                self._icons[name] = load_icon(name, t["text"], size)
                btn.configure(image=self._icons[name], fg_color="transparent", hover_color=t["list_hover"])
        self.player.apply_theme(t)
        self.tileset_view.apply_theme(t)
        self.update_status()
        self.show_tool(self.tool.key)

    def button_style(self):
        t = self.t
        return dict(fg_color=t["button"], hover_color=t["button_hover"], text_color=t["text"],
                    text_color_disabled=t["muted"])

    # ----- sidebar --------------------------------------------------------

    def toggle_sidebar(self):
        hidden = self.sidebar.winfo_manager() == ""
        if hidden:
            self.sidebar.grid()
        else:
            self.sidebar.grid_remove()
        self.config_data.sidebar_hidden = not hidden
        self.save_config()

    def focus_search(self):
        if self.sidebar.winfo_manager() == "":
            self.toggle_sidebar()
        self.search.focus()
        self.search.select_range(0, "end")

    def clear_search(self):
        self.search.delete(0, "end")
        self.refresh_list()
        self.focus()

    def matching_tools(self):
        words = self.search.get().lower().split()
        return [tool for tool in TOOLS if all(w in tool.search_text() for w in words)]

    def open_first_match(self):
        tools = self.matching_tools()
        if tools:
            self.show_tool(tools[0].key)

    def refresh_list(self):
        for w in self.tool_list.winfo_children():
            w.destroy()
        t = self.t
        tools = self.matching_tools()
        if not tools:
            ctk.CTkLabel(self.tool_list, text="No tools match", text_color=t["muted"]).grid(
                row=0, column=0, sticky="w", padx=10, pady=4)
        category = None
        for row, tool in enumerate(tools):
            if tool.category != category:
                category = tool.category
                ctk.CTkLabel(self.tool_list, text=category.upper(), font=HEADING_FONT, anchor="w",
                             text_color=t["muted"]).grid(row=2 * row, column=0, sticky="ew",
                                                         padx=10, pady=(10 if row else 2, 0))
            ctk.CTkButton(
                self.tool_list, text=tool.name, anchor="w",
                fg_color=t["list_hover"] if tool is self.tool else "transparent",
                hover_color=t["list_hover"], text_color=t["text"],
                command=lambda k=tool.key: self.show_tool(k),
            ).grid(row=2 * row + 1, column=0, sticky="ew", pady=1)
        self.after_idle(self.update_scrollbar)

    def update_scrollbar(self):
        """Show the list's scrollbar only when the list doesn't fit."""
        canvas = self.tool_list._parent_canvas
        bbox = canvas.bbox("all")
        if bbox and bbox[3] > canvas.winfo_height():
            self.tool_list._scrollbar.grid()
        else:
            self.tool_list._scrollbar.grid_remove()

    # ----- tool panel -----------------------------------------------------

    def show_tool(self, key):
        self.collect_options()
        self.tool = TOOLS_BY_KEY[key]
        if self.config_data.last_tool != key:
            self.config_data.last_tool = key
            self.save_config()
        self.title_label.configure(text=self.tool.name)
        self.build_panel()
        shown = self.tool.view_name()
        for name, view in self.views.items():
            if name == shown:
                view.grid()
            else:
                view.grid_remove()
        if shown == "player":
            self.sync_player()
            self.player.play()
        else:
            self.player.pause()
        self.refresh_view()
        self.refresh_list()

    def tool_inputs(self, tool=None):
        """{slot key: paths} chosen for a tool."""
        return self.inputs.setdefault((tool or self.tool).key, {})

    def tool_args(self, tool=None):
        """What a tool's run, input_info and prepare get: the paths, or {slot key: paths} with slots."""
        tool = tool or self.tool
        chosen = self.tool_inputs(tool)
        return dict(chosen) if tool.slots else chosen.get("input")

    def build_panel(self):
        for w in self.panel.winfo_children():
            w.destroy()
        self.fields = {}
        t, tool, cfg = self.t, self.tool, self.config_data
        pad = 14

        self.description = ctk.CTkLabel(self.panel, text=tool.description, text_color=t["muted"],
                                        anchor="w", justify="left")
        self.description.grid(row=0, column=0, columnspan=6, sticky="ew", padx=pad, pady=(12, 10))
        self.wrap_description()

        # inputs get their own grid, so paths can use whatever width the settings below leave
        input_rows = ctk.CTkFrame(self.panel, fg_color="transparent")
        input_rows.grid(row=1, column=0, columnspan=6, sticky="ew", padx=pad, pady=4)
        input_rows.grid_columnconfigure(1, weight=1)
        self.input_labels = {}
        slots = tool.input_slots()
        for r, slot in enumerate(slots):
            top = 0 if r == 0 else 6
            ctk.CTkLabel(input_rows, text=slot.label, text_color=t["text"], anchor="w").grid(
                row=r, column=0, sticky="w", padx=(0, 16), pady=(top, 0))
            label = ctk.CTkLabel(input_rows, text="", anchor="w")
            label.grid(row=r, column=1, sticky="ew", pady=(top, 0))
            label.bind("<Configure>", lambda e, k=slot.key: self.fit_input_label(k))
            self.input_labels[slot.key] = label
            for i, mode in enumerate(slot.modes):
                ctk.CTkButton(input_rows, text=INPUT_BUTTONS[mode][0], width=120,
                              command=lambda m=mode, k=slot.key: self.choose_input(m, k),
                              **self.button_style()).grid(row=r, column=2 + i, padx=(6, 0), pady=(top, 0))
        # e.g. how a sheet is cut into frames; hidden when the tool has nothing to say
        self.input_info = ctk.CTkLabel(input_rows, text="", anchor="w", text_color=t["muted"])
        self.input_info.grid(row=len(slots), column=1, columnspan=3, sticky="w")
        self.update_input_label()

        self.field_labels = {}
        per_row = 2 if len(tool.options) > 4 else 1  # many settings: two columns, so the log keeps room
        for i, option in enumerate(tool.options):
            row, col = 2 + i // per_row, (i % per_row) * 2
            left = pad if col == 0 else 24
            value = getattr(cfg, option.key)
            if option.kind == "bool":
                var = tk.BooleanVar(value=value)
                widget = ctk.CTkCheckBox(self.panel, text=option.label, variable=var, text_color=t["text"],
                                         fg_color=t["button"], hover_color=t["button_hover"],
                                         border_color=t["button"], checkmark_color=t["surface"],
                                         command=self.update_field_states)
                widget.grid(row=row, column=col, columnspan=2, sticky="w", padx=(left, 0), pady=4)
            else:
                label = ctk.CTkLabel(self.panel, text=option.label, text_color=t["text"], anchor="w")
                label.grid(row=row, column=col, sticky="w", padx=(left, 16), pady=4)
                self.field_labels[option] = label
                var = tk.StringVar(value=option.format(value))
                if option.kind == "choice":
                    widget = ctk.CTkOptionMenu(
                        self.panel, values=list(option.choices), variable=var, width=200,
                        command=self.update_field_states,
                        fg_color=t["list_hover"], button_color=t["list_hover"],
                        button_hover_color=t["scrollbar"], text_color=t["text"],
                        dropdown_fg_color=t["surface"], dropdown_hover_color=t["list_hover"],
                        dropdown_text_color=t["text"])
                else:
                    widget = ctk.CTkEntry(self.panel, textvariable=var, border_width=0,
                                          width=200 if option.kind == "int_list" else 100,
                                          fg_color=t["list_hover"], text_color=t["text"])
                    widget.bind("<Return>", lambda e: self.run_tool())  # with a preview, this reloads
                widget.grid(row=row, column=col + 1, sticky="w", pady=4)
            self.fields[option] = (var, widget)
        row = 2 + math.ceil(len(tool.options) / per_row)
        self.update_field_states()
        self.update_input_info()
        for option, (var, widget) in self.fields.items():
            if tool.input_info:
                var.trace_add("write", lambda *_: self.update_input_info())
            if tool.render:
                var.trace_add("write", lambda *_: self.schedule_view_refresh())
            if tool.preview:  # playback settings apply while it plays; what to load, after a pause in typing
                if option.key in RELOAD_SETTINGS:
                    var.trace_add("write", lambda *_: self.schedule_reload())
                else:
                    var.trace_add("write", lambda *_: self.sync_player())

        actions = ctk.CTkFrame(self.panel, fg_color="transparent")
        actions.grid(row=row, column=0, columnspan=6, sticky="ew", padx=pad, pady=(10, 14))
        self.save_btn = None
        if tool.save:
            self.save_btn = ctk.CTkButton(actions, text=tool.save_label, width=120,
                                          command=lambda: self.run_tool("save"), **self.button_style())
            self.save_btn.pack(side="left", padx=(0, 8))
            run_style = dict(fg_color=t["list_hover"], hover_color=t["scrollbar"], text_color=t["text"],
                             text_color_disabled=t["muted"])
        else:
            run_style = self.button_style()
        self.run_btn = ctk.CTkButton(actions, text=tool.run_label, width=120, command=self.run_tool, **run_style)
        self.run_btn.pack(side="left")
        self.open_btn = ctk.CTkButton(actions, text="Open output folder", width=150, command=self.open_output,
                                      fg_color="transparent", hover_color=t["list_hover"], text_color=t["text"])
        self.update_actions()

    def wrap_description(self):
        if getattr(self, "description", None) and self.description.winfo_exists():
            width = self.panel.winfo_width() / self.panel._get_widget_scaling()
            self.description.configure(wraplength=max(300, int(width) - 40))

    def update_input_info(self):
        text = None
        if self.tool.input_info and any(self.tool_inputs().values()):
            try:
                text = self.tool.input_info(self.current_settings(), self.tool_args())
            except (OSError, ValueError) as e:
                text = f"Can't read the input: {e}"
        if text:
            self.input_info.configure(text=text)
            self.input_info.grid()
        else:
            self.input_info.grid_remove()

    def input_text(self, slot_key):
        paths = self.tool_inputs().get(slot_key)
        if not paths:
            return "Nothing chosen yet"
        if len(paths) == 1:
            if os.path.isdir(paths[0]):
                return "Folder: " + short_path(paths[0])
            if self.tool.inputs == "frames_or_sheet" and self.config_data.apng_source == "sheet":
                return "Sheet: " + short_path(paths[0])
            return short_path(paths[0])
        return f"{len(paths)} files in {short_path(os.path.dirname(paths[0]))}"

    def update_input_label(self):
        for key, label in self.input_labels.items():
            has_input = bool(self.tool_inputs().get(key))
            label.configure(text_color=self.t["text"] if has_input else self.t["muted"])
            self.fit_input_label(key)

    def fit_input_label(self, slot_key):
        """Show the input, with "…" in the middle if it doesn't fit (the file name at the end stays)."""
        label = self.input_labels.get(slot_key)
        if not label or not label.winfo_exists():
            return
        full = self.input_text(slot_key)
        room = label.winfo_width()
        font = label.cget("font")
        text = full
        if room > 1 and font.measure(full) > room:
            # longest text of the form start…end that fits
            shown = lambda n: full[:n // 2] + "…" + full[len(full) - (n - n // 2):]
            lo, hi = 0, len(full)
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if font.measure(shown(mid)) <= room:
                    lo = mid
                else:
                    hi = mid - 1
            text = shown(lo)
        if label.cget("text") != text:
            label.configure(text=text)

    def update_actions(self):
        """The buttons are disabled while any task runs; Open output folder shows after this tool saved something."""
        if not self.run_btn.winfo_exists():
            return
        buttons = {"run": (self.run_btn, self.tool.run_label, "Loading…" if self.tool.preview else "Running…")}
        if self.save_btn:
            buttons["save"] = (self.save_btn, self.tool.save_label, "Saving…")
        for action, (button, label, busy) in buttons.items():
            if self.running:
                text = busy if self.running == (self.tool.key, action) else label
                button.configure(text=text, state="disabled")
            else:
                button.configure(text=label, state="normal")
        if self.output_dirs.get(self.tool.key):
            self.open_btn.pack(side="left", padx=(8, 0))
        else:
            self.open_btn.pack_forget()

    # ----- input ----------------------------------------------------------

    def start_dir(self):
        last = self.config_data.last_dir
        return last if last != "." and os.path.isdir(last) else str(Path.home())

    def choose_input(self, mode, slot_key=None):
        if self.dialog_open:
            return
        slot_key = slot_key or self.tool.input_slots()[0].key
        self.dialog_open = True
        tool = self.tool
        titles = {"file": "Choose an image", "files": "Choose images", "folder": "Choose a folder",
                  "frames": "Choose the frames", "sheet": "Choose a spritesheet"}
        if tool.slots:
            titles["file"] = f"Choose the {next(s.label for s in tool.slots if s.key == slot_key).lower()}"
        dialog_mode = INPUT_BUTTONS[mode][1]

        def then(paths):
            self.dialog_open = False
            if not paths:
                return
            self.tool_inputs(tool)[slot_key] = sorted(paths)
            self.config_data.last_dir = paths[0] if mode == "folder" else os.path.dirname(paths[0])
            if self.tool is not tool:
                self.save_config()
                return
            self.collect_options()  # keep what was typed; the panel is rebuilt with any guessed settings
            if mode in ("frames", "sheet"):
                self.config_data.apng_source = mode
            if tool.prepare:
                try:
                    tool.prepare(self.config_data, self.tool_args(tool))
                except (OSError, ValueError) as e:
                    self.show_note(f"Can't read the input: {e}", 5000, error=True)
                    return
            self.save_config()
            self.build_panel()
            self.refresh_view()
            if tool.preview:
                self.run_tool()

        filedialogs.ask_open(self, dialog_mode, titles[mode], self.start_dir(), "Images", self.patterns, then)

    # ----- running --------------------------------------------------------

    def run_tool(self, action="run"):
        """Run the current tool's run action, or its save action."""
        if self.running:
            return
        tool = self.tool
        fn, finished = (tool.save, tool.save_done) if action == "save" else (tool.run, tool.done)
        errors = self.collect_options()
        if errors:
            self.show_note(errors[0], 4000, error=True)
            return
        chosen = self.tool_inputs(tool)
        for slot in tool.input_slots():
            if not chosen.get(slot.key):
                what = "an input" if not tool.slots else f"the {slot.label.lower()}"
                self.show_note(f"Choose {what} first", error=True)
                return
        missing = [p for paths in chosen.values() for p in paths if not os.path.exists(p)]
        if missing:
            self.show_note(f"Not found: {os.path.basename(missing[0])}", error=True)
            return
        self.save_config()
        self.running = (tool.key, action)
        self.update_actions()
        self.log(f"── {tool.name} ──")

        paths = self.tool_args(tool)

        def done(result):
            if tool.preview and action == "run":
                self.player.set_frames(result)
                if self.tool is not tool:
                    self.player.pause()
            note, folder = finished(result, paths)
            if folder:
                self.output_dirs[tool.key] = folder
            self.finish_run()
            self.show_note(note, 4000)

        def failed(error):
            self.finish_run()
            message = f"Failed: {error}"
            self.show_note(message if len(message) <= 90 else message[:89] + "…", 6000, error=True)

        # a copy, so changing settings while it runs doesn't affect it
        self.worker.run(fn, copy.deepcopy(self.config_data), copy.deepcopy(paths), on_done=done, on_error=failed)

    def schedule_reload(self):
        """Reload the preview half a second after the frame size or row stops changing."""
        if self.reload_job:
            self.after_cancel(self.reload_job)
        self.reload_job = self.after(500, self.auto_reload)

    def auto_reload(self):
        self.reload_job = None
        paths = self.tool_inputs().get("input")
        # only a sheet uses these settings; and don't complain about a half-typed number
        if not self.tool.preview or self.running or not paths or self.config_data.apng_source != "sheet":
            return
        for option, (var, widget) in self.fields.items():
            if option.key in RELOAD_SETTINGS and self.option_enabled(option):
                try:
                    option.parse(var.get())
                except (ValueError, tk.TclError):
                    return
        self.run_tool()

    def schedule_view_refresh(self):
        """Redraw the tool's view soon; several setting changes in a row (e.g. dragging) redraw once."""
        if not self.view_job:
            self.view_job = self.after(30, self.refresh_view)

    def refresh_view(self):
        self.view_job = None
        tool = self.tool
        if not tool.render:
            return
        try:
            data = tool.render(self.current_settings(), self.tool_args())
        except OSError as e:
            data = {"message": f"Can't read the input: {e}"}
        self.views[tool.view_name()].show(data)

    def set_border_size(self, size):
        """The tileset view's guides were dragged: put the new size in the Border size field."""
        for option, (var, widget) in self.fields.items():
            if option.key == "border_size":
                var.set(str(size))

    def sync_player(self):
        """Pass the panel's playback settings to the player (invalid ones are ignored)."""
        values = {}
        for option, (var, widget) in self.fields.items():
            try:
                values[option.key] = option.parse(var.get())
            except (ValueError, tk.TclError):
                pass
        self.player.set_playback(delay_ms=values.get("delay_ms"), pingpong=values.get("apng_pingpong"),
                                 zoom=values.get("preview_zoom"), background=values.get("preview_background"))

    def player_key(self, action):
        """Space and arrow keys control the preview, except while typing in a field."""
        if not self.tool.preview or isinstance(self.focus_get(), (tk.Entry, tk.Text)):
            return None
        action()
        return "break"

    def finish_run(self):
        self.running = None
        self.close_armed = False
        self.update_actions()

    def open_output(self):
        folder = self.output_dirs.get(self.tool.key)
        if folder and os.path.isdir(folder):
            subprocess.Popen(["xdg-open", folder])
        else:
            self.show_note("That folder no longer exists", error=True)

    # ----- log and notes --------------------------------------------------

    def log(self, message):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def update_status(self):
        text, error = self.note or ("", False)
        self.status.configure(text=text, text_color=self.t["error"] if error else self.t["muted"])

    def show_note(self, text, ms=2500, error=False):
        """A brief message in the toolbar."""
        if self.note_job:
            self.after_cancel(self.note_job)
        self.note = (text, error)
        self.update_status()

        def clear():
            self.note = self.note_job = None
            self.update_status()

        self.note_job = self.after(ms, clear)

    # ----- closing --------------------------------------------------------

    def close(self):
        """Quit. While a task runs, the first close only warns: quitting then can leave a half-written file."""
        if self.running and not self.close_armed:
            self.close_armed = True
            self.show_note("A task is still running: close again to quit anyway", 4000, error=True)
            self.after(4000, lambda: setattr(self, "close_armed", False))
            return
        self.collect_options()
        self.save_config()
        self.destroy()

    def run(self):
        self.mainloop()
