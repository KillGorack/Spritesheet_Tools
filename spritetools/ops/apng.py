import io
import os

from apng import APNG, PNG
from PIL import Image

from .frames import load_clips
from .util import unique_path


def save_apng(frames, path, delay_ms, pingpong=False):
    """Save RGBA frames as a looping APNG. Frames of different sizes are centered on the largest.

    With pingpong, the frames play forward and then back without repeating the ends.
    """
    if pingpong and len(frames) > 2:
        frames = frames + frames[-2:0:-1]
    size = (max(f.width for f in frames), max(f.height for f in frames))
    apng = APNG()
    for frame in frames:
        if frame.size != size:
            canvas = Image.new("RGBA", size, (0, 0, 0, 0))
            canvas.paste(frame, ((size[0] - frame.width) // 2, (size[1] - frame.height) // 2))
            frame = canvas
        buffer = io.BytesIO()
        frame.save(buffer, format="PNG")
        apng.append(PNG.from_bytes(buffer.getvalue()), delay=delay_ms)
    apng.num_plays = 0
    apng.save(path)


def make_apngs(paths, source, columns, rows, mode, row, delay_ms, pingpong=False, log=print):
    """Save the input's animations (see frames.load_clips) as APNGs next to the input,
    named <name>_anim.png or <sheet>_rowN_anim.png and never overwritten.

    Returns (output folder, saved paths).
    """
    folder = os.path.dirname(sorted(paths)[0])
    saved = []
    for name, frames in load_clips(paths, source, columns, rows, mode, row):
        out = unique_path(os.path.join(folder, f"{name}_anim.png"))
        save_apng(frames, out, delay_ms, pingpong)
        log(f"Saved: {out} ({len(frames)} frames)")
        saved.append(out)
    return folder, saved
