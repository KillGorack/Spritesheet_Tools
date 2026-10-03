"""Open and color dialogs: the desktop's own (kdialog or zenity) when available, else Tk's basic one."""
import re
import shutil
import subprocess
import threading
from tkinter import colorchooser, filedialog


def _desktop_command(mode, title, start, label, patterns):
    """Command line for kdialog or zenity, or None if neither is installed.

    mode is "file", "files" or "folder".
    """
    pattern = " ".join(patterns)
    if shutil.which("kdialog"):
        if mode == "folder":
            return ["kdialog", "--title", title, "--getexistingdirectory", start]
        cmd = ["kdialog", "--title", title, "--getopenfilename", start, f"{label} ({pattern})"]
        if mode == "files":
            cmd += ["--multiple", "--separate-output"]
        return cmd
    if shutil.which("zenity"):
        cmd = ["zenity", "--file-selection", f"--title={title}", f"--filename={start.rstrip('/')}/"]
        if mode == "folder":
            return cmd + ["--directory"]
        cmd.append(f"--file-filter={label} | {pattern}")
        if mode == "files":
            cmd += ["--multiple", "--separator=\n"]
        return cmd
    return None


def ask_open(root, mode, title, start, label, patterns, then):
    """Ask for a file, several files or a folder, then call then(paths) ([] if cancelled)."""
    cmd = _desktop_command(mode, title, start, label, patterns)
    if cmd is None:
        if mode == "folder":
            folder = filedialog.askdirectory(parent=root, title=title, initialdir=start)
            then([folder] if folder else [])
        elif mode == "files":
            then(list(filedialog.askopenfilenames(parent=root, title=title, initialdir=start,
                                                  filetypes=[(label, " ".join(patterns))])))
        else:
            path = filedialog.askopenfilename(parent=root, title=title, initialdir=start,
                                              filetypes=[(label, " ".join(patterns))])
            then([path] if path else [])
        return

    _run_in_thread(root, cmd, lambda out: then([p for p in out.splitlines() if p]))


def ask_color(root, title, initial, then):
    """Ask for a color, then call then("#rrggbb"), or then(None) if cancelled. initial is "#rrggbb"."""
    if shutil.which("kdialog"):
        cmd = ["kdialog", "--title", title, "--getcolor", "--default", initial]
    elif shutil.which("zenity"):
        cmd = ["zenity", "--color-selection", f"--title={title}", f"--color={initial}"]
    else:
        rgb, hex_color = colorchooser.askcolor(color=initial, parent=root, title=title)
        then(hex_color.lower() if hex_color else None)
        return
    _run_in_thread(root, cmd, lambda out: then(_parse_color(out)))


def _parse_color(text):
    """kdialog prints #rrggbb, zenity rgb(r,g,b) or rgba(r,g,b,a). None if it's neither (cancelled)."""
    text = text.strip().lower()
    if re.fullmatch(r"#[0-9a-f]{6}", text):
        return text
    numbers = re.fullmatch(r"rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,.*)?\)", text)
    if numbers:
        return "#" + "".join(f"{min(255, int(n)):02x}" for n in numbers.groups())
    return None


def _run_in_thread(root, cmd, then):
    """Run a dialog command in a thread, so the window keeps drawing (and a running task
    keeps logging) meanwhile; then call then(its output) on the main thread."""
    result = []

    def target():
        result.append(subprocess.run(cmd, capture_output=True, text=True).stdout)

    thread = threading.Thread(target=target, daemon=True)
    thread.start()

    def wait():
        if thread.is_alive():
            root.after(100, wait)
        else:
            then(result[0] if result else "")

    wait()
