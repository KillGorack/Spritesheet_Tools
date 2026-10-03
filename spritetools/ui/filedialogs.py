"""Open dialogs: the desktop's own (kdialog or zenity) when available, else Tk's basic one."""
import shutil
import subprocess
import threading
from tkinter import filedialog


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
    """Ask for a file, several files or a folder, then call then(paths) ([] if cancelled).

    The desktop dialog runs in a thread so the window keeps drawing (and a running
    task keeps logging) meanwhile.
    """
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

    result = []

    def target():
        r = subprocess.run(cmd, capture_output=True, text=True)
        result.extend(p for p in r.stdout.splitlines() if p)

    thread = threading.Thread(target=target, daemon=True)
    thread.start()

    def wait():
        if thread.is_alive():
            root.after(100, wait)
        else:
            then(result)

    wait()
