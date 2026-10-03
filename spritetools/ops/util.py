import os


def unique_path(path):
    """Return path, or path with a _1, _2, ... suffix if it already exists."""
    base, ext = os.path.splitext(path)
    n = 1
    while os.path.exists(path):
        path = f"{base}_{n}{ext}"
        n += 1
    return path


def base_name(path):
    """File name without directory or extension."""
    return os.path.splitext(os.path.basename(path))[0]
