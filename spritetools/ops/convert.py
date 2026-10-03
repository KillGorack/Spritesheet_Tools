import os

from PIL import Image

from .alpha import bleed, has_alpha

# Pillow formats that register an extension but can't actually decode pixels here
UNSUPPORTED_READ = {"BUFR", "GRIB", "HDF5", "MPEG", "WMF", "EPS"}

# label: (extension, Pillow format, save options)
OUTPUT_FORMATS = {
    "PNG": (".png", "PNG", {"optimize": True}),
    "TGA": (".tga", "TGA", {}),
    "TGA (RLE)": (".tga", "TGA", {"compression": "tga_rle"}),
    "WEBP (lossless)": (".webp", "WEBP", {"lossless": True}),
    "WEBP (lossy)": (".webp", "WEBP", {"quality": None}),
    "JPG": (".jpg", "JPEG", {"quality": None}),
    "BMP": (".bmp", "BMP", {}),
    "TIFF": (".tiff", "TIFF", {"compression": "tiff_lzw"}),
    "DDS (uncompressed)": (".dds", "DDS", {}),
    "DDS (DXT1 / BC1)": (".dds", "DDS", {"pixel_format": "DXT1"}),
    "DDS (DXT5 / BC3)": (".dds", "DDS", {"pixel_format": "DXT5"}),
    "QOI": (".qoi", "QOI", {}),
    "ICO": (".ico", "ICO", {}),
}


def readable_extensions():
    """Every file extension the installed Pillow can decode, e.g. ['.bmp', '.dds', ...]."""
    Image.init()
    return sorted(ext for ext, fmt in Image.registered_extensions().items()
                  if fmt in Image.OPEN and fmt not in UNSUPPORTED_READ)


def find_images(folder, recursive=True, extensions=None):
    """All readable image files in folder (and subfolders if recursive), in sorted order."""
    extensions = set(extensions or readable_extensions())
    paths = []
    for root, dirs, files in os.walk(folder):
        dirs.sort()
        paths.extend(os.path.join(root, f) for f in sorted(files)
                     if os.path.splitext(f)[1].lower() in extensions)
        if not recursive:
            break
    return paths


def convert_images(paths, target, quality=90, overwrite=False, delete_original=False, fix_halos=False, log=print):
    """Convert each file to the OUTPUT_FORMATS entry named target, next to the original.

    fix_halos bleeds images with transparency before saving (see alpha.py).
    Files already in the target format, or whose output exists (unless overwrite), are skipped.
    Returns {"converted": n, "skipped": n, "failed": n}.
    """
    ext, fmt, options = OUTPUT_FORMATS[target]
    options = dict(options)
    if "quality" in options:
        options["quality"] = quality
    counts = {"converted": 0, "skipped": 0, "failed": 0}
    log(f"Converting {len(paths)} file(s) to {target}...")
    for src in paths:
        dst = os.path.splitext(src)[0] + ext
        if os.path.splitext(src)[1].lower() == ext or (os.path.exists(dst) and not overwrite):
            counts["skipped"] += 1
            continue
        try:
            with Image.open(src) as img:
                img.load()
                if fix_halos and has_alpha(img) and fmt != "JPEG":
                    img = bleed(img)
                try:
                    img.save(dst, fmt, **options)
                except (OSError, ValueError, KeyError):
                    # Target can't store this mode (alpha in JPG, palette in DDS, 16-bit, ...)
                    fallback = "RGB" if fmt == "JPEG" else "RGBA"
                    img.convert(fallback).save(dst, fmt, **options)
            if delete_original:
                os.remove(src)
            counts["converted"] += 1
            log(f"✔ {src} → {dst}")
        except Exception as e:
            counts["failed"] += 1
            if os.path.exists(dst) and os.path.getsize(dst) == 0:
                os.remove(dst)
            log(f"✖ Failed: {src} ({e})")
    log("\n--- Done ---")
    log(f"Converted: {counts['converted']}")
    log(f"Skipped:   {counts['skipped']}")
    log(f"Failed:    {counts['failed']}")
    return counts
