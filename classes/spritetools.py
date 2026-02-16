import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox
import os
from PIL import Image
from apng import APNG, PNG
import io
import json


class spritetools:

    def __init__(self):

        self.FRAME_SIZE = 128
        self.START_INDEX = 0
        self.DELAY_MS = 70
        self.TARGET_SIZES = [256, 128, 64, 32, 16]
        self.BASE_FRAME_SIZE = 512
        self.RESAMPLE = Image.Resampling.LANCZOS
        self.DIRECTION = "down"
        self.DELETE_ORIGINAL = False
        self.OVERWRITE = False
        self.config_path = os.path.join(os.path.dirname(__file__), ".spritetools_config.json")
        self.last_dir = '.'
        self.last_dir = self.load_config()
        self.root = tk.Tk()
        self.root.geometry("800x400")
        self.root.resizable(False, False)
        self.root.title("Sprite tools")
        self.root.protocol("WM_DELETE_WINDOW", self.windowXCloser)
        try:
            icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'icon.png'))
            if os.path.exists(icon_path):
                icon = tk.PhotoImage(file=icon_path)
                self.root.iconphoto(True, icon)
        except Exception:
            pass
        self.button_texts = [
            "Apng from Atlas", 
            "Apng from frames", 
            "Apng from frames (ping pong)", 
            "Atlas disector",
            "Orthoginal resizer", 
            "Frame stitcher (horizontal)", 
            "Frame stitcher (vertical)", 
            "BMP to PNG convert"
        ]
        self.create_grid()
        self.root.mainloop()





    def windowXCloser(self):
        self.root.destroy()





    def load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                self.last_dir = data.get('last_dir', self.last_dir)
                if not os.path.isdir(self.last_dir):
                    self.last_dir = '.'
                self.FRAME_SIZE = int(data.get('FRAME_SIZE', self.FRAME_SIZE))
                self.START_INDEX = int(data.get('START_INDEX', self.START_INDEX))
                self.DELAY_MS = int(data.get('DELAY_MS', self.DELAY_MS))
                self.TARGET_SIZES = list(data.get('TARGET_SIZES', self.TARGET_SIZES))
                self.BASE_FRAME_SIZE = int(data.get('BASE_FRAME_SIZE', self.BASE_FRAME_SIZE))
                resample_name = data.get('RESAMPLE', self._resample_to_name(self.RESAMPLE))
                self.RESAMPLE = self._resample_from_name(resample_name)
                self.DIRECTION = data.get('DIRECTION', self.DIRECTION)
                self.DELETE_ORIGINAL = bool(data.get('DELETE_ORIGINAL', self.DELETE_ORIGINAL))
                self.OVERWRITE = bool(data.get('OVERWRITE', self.OVERWRITE))
                return self.last_dir
            except Exception:
                return self.last_dir
        return self.last_dir





    def save_config(self):
        try:
            data = {
                'last_dir': self.last_dir,
                'FRAME_SIZE': self.FRAME_SIZE,
                'START_INDEX': self.START_INDEX,
                'DELAY_MS': self.DELAY_MS,
                'TARGET_SIZES': self.TARGET_SIZES,
                'BASE_FRAME_SIZE': self.BASE_FRAME_SIZE,
                'RESAMPLE': self._resample_to_name(self.RESAMPLE),
                'DIRECTION': self.DIRECTION,
                'DELETE_ORIGINAL': self.DELETE_ORIGINAL,
                'OVERWRITE': self.OVERWRITE
            }
            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.log_message(f"Warning: Could not save config: {e}")






    def _resample_from_name(self, name):
        if not name:
            if hasattr(Image, 'Resampling'):
                return Image.Resampling.LANCZOS
            return getattr(Image, 'LANCZOS', Image.BICUBIC)
        try:
            if hasattr(Image, 'Resampling'):
                return Image.Resampling[name]
        except Exception:
            pass
        return getattr(Image, name, getattr(Image, 'LANCZOS', Image.BICUBIC))







    def _resample_to_name(self, resample):
        try:
            return resample.name
        except Exception:
            for n in ['NEAREST', 'BOX', 'BILINEAR', 'HAMMING', 'BICUBIC', 'LANCZOS']:
                try:
                    if hasattr(Image, 'Resampling'):
                        val = Image.Resampling[n]
                    else:
                        val = getattr(Image, n)
                except Exception:
                    val = None
                if val == resample:
                    return n
            return 'LANCZOS'
        




    def log_message(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update()




    def create_grid(self):
        button_actions = [
            self.apng_from_atlas, 
            self.apng_from_frames, 
            self.apng_from_frames_pingpong, 
            self.atlas_disector,
            self.atlas_resizer, 
            self.frame_stitcher_horizontal, 
            self.frame_stitcher_vertical, 
            self.bmp_to_png
        ]
        for row in range(4):
            for col in range(2):
                button_index = row * 2 + col
                button = tk.Button(self.root, text=self.button_texts[button_index], relief="solid", command=button_actions[button_index])
                button.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        for i in range(2):
            self.root.grid_columnconfigure(i, weight=1)
        for i in range(4):
            self.root.grid_rowconfigure(i, weight=1)
        self.log_text = tk.Text(self.root, height=8, width=100, bg="#f0f0f0", fg="#333", font=("Consolas", 8))
        self.log_text.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
        self.root.grid_rowconfigure(4, weight=1)







    def select_file(self, params):
        image_types = (
            ("Image files", "*.png *.jpg *.jpeg *.bmp *.gif *.tga"),
            ("All files", "*.*"),
        )
        if params:
            paths = filedialog.askopenfilenames(parent=self.root, title="Select image files", initialdir=self.last_dir, filetypes=image_types)
            if paths:
                self.last_dir = os.path.dirname(paths[0])
                self.save_config()
            return list(paths) if paths else []
        else:
            path = filedialog.askopenfilename(parent=self.root, title="Select image file", initialdir=self.last_dir, filetypes=image_types)
            if path:
                self.last_dir = os.path.dirname(path)
                self.save_config()
            return path if path else None
        



    def select_folder(self):
        folder = filedialog.askdirectory(parent=self.root, title="Select folder", initialdir=self.last_dir)
        if folder:
            self.last_dir = folder
            self.save_config()
        return folder if folder else None



    def apng_from_atlas(self):
        spritesheet_path = self.select_file(params=False)
        if not spritesheet_path:
            self.log_message("No file selected.")
            return
        img = Image.open(spritesheet_path)
        img_width, img_height = img.size
        base_dir = os.path.dirname(spritesheet_path)
        base_name = os.path.splitext(os.path.basename(spritesheet_path))[0]
        output_dir = os.path.join(base_dir, f"{base_name}_previews")
        os.makedirs(output_dir, exist_ok=True)
        frames_per_row = img_width // self.FRAME_SIZE
        rows = img_height // self.FRAME_SIZE 
        for row in range(rows):
            apng = APNG()
            for col in range(frames_per_row):
                x = col * self.FRAME_SIZE
                y = row * self.FRAME_SIZE
                frame = img.crop((x, y, x + self.FRAME_SIZE, y + self.FRAME_SIZE))
                buffer = io.BytesIO()
                frame.save(buffer, format="PNG")
                buffer.seek(0)
                png_frame = PNG.from_bytes(buffer.read())
                apng.append(png_frame, delay=self.DELAY_MS)
            output_apng = os.path.join(output_dir, f"{base_name}_row{row}.png")
            apng.num_plays = 0
            apng.save(output_apng)
            self.log_message(f"Saved: {output_apng}")
        messagebox.showinfo("Done", f"Saved {rows} APNG previews to:\n{output_dir}")






    def apng_from_frames(self):
        file_paths = self.select_file(params=True)
        if not file_paths:
            return
        file_paths = list(file_paths)
        file_paths.sort()
        folder = os.path.dirname(file_paths[0])
        output_file = os.path.join(folder, "preview.png")
        delay_ms = 35
        apng = APNG()
        for frame in file_paths:
            apng.append_file(frame, delay=delay_ms)
        apng.num_plays = 0
        apng.save(output_file)







    def apng_from_frames_pingpong(self):
        file_paths = self.select_file(params=True)
        if len(file_paths) > 2:
            pingpong_frames = (
                file_paths +
                file_paths[-2:0:-1]
            )
        else:
            pingpong_frames = file_paths
        folder = os.path.dirname(file_paths[0])
        output_file = os.path.join(folder, "preview.png")
        delay_ms = 70
        apng = APNG()
        for frame in pingpong_frames:
            apng.append_file(frame, delay=delay_ms)
        apng.num_plays = 0
        apng.save(output_file)
        messagebox.showinfo("Done", f"Ping-pong PNG saved:\n{output_file}")










    def atlas_disector(self):
        spritesheet_path = self.select_file(params=False)
        if not spritesheet_path:
            self.log_message("No file selected.")
            return
        self.log_message(spritesheet_path)
        img = Image.open(spritesheet_path)
        img_width, img_height = img.size
        base_dir = os.path.dirname(spritesheet_path)
        output_dir = os.path.join(base_dir, "sources")
        os.makedirs(output_dir, exist_ok=True)
        frame_index = self.START_INDEX
        for y in range(0, img_height, self.FRAME_SIZE):
            for x in range(0, img_width, self.FRAME_SIZE):
                if x + self.FRAME_SIZE > img_width or y + self.FRAME_SIZE > img_height:
                    continue
                frame = img.crop((x, y, x + self.FRAME_SIZE, y + self.FRAME_SIZE))
                frame_name = f"frame_{frame_index:03}.png"
                frame.save(os.path.join(output_dir, frame_name))
                frame_index += 1
        self.log_message(f"Extracted {frame_index - self.START_INDEX} frames to:")
        self.log_message(output_dir)









    def atlas_resizer(self):
        spritesheet_path = self.select_file(params=False)
        if not spritesheet_path:
            self.log_message("No file selected.")
            return
        directory = os.path.dirname(spritesheet_path)
        img = Image.open(spritesheet_path)
        width, height = img.size
        if width % self.BASE_FRAME_SIZE != 0 or height % self.BASE_FRAME_SIZE != 0:
            self.log_message("Warning: image dimensions are not cleanly divisible by 512.")
        for size in self.TARGET_SIZES:
            scale = size / self.BASE_FRAME_SIZE
            new_width = int(width * scale)
            new_height = int(height * scale)
            resized = img.resize((new_width, new_height), self.RESAMPLE)
            size_str = f"{size:03d}"
            out_name = f"{"sprite_sheet"}_{size_str}.png"
            out_path = os.path.join(directory, out_name)
            resized.save(out_path, format="PNG", optimize=True)
            self.log_message(f"Saved: {out_name} ({new_width}x{new_height})")







    def frame_stitcher_horizontal(self):
        self.DIRECTION = "right"
        self.frame_stitcher()

    def frame_stitcher_vertical(self):
        self.DIRECTION = "down"
        self.frame_stitcher()

    def frame_stitcher(self):
        file_paths = self.select_file(params=True)
        if not file_paths:
            return
        images = [Image.open(fp).convert("RGBA") for fp in file_paths]
        w, h = images[0].size
        count = len(images)
        if self.DIRECTION == "right":
            composite_size = (w * count, h)
            x, y = 0, 0
            dx, dy = w, 0
        elif self.DIRECTION == "down":
            composite_size = (w, h * count)
            x, y = 0, 0
            dx, dy = 0, h
        else:
            raise ValueError("DIRECTION must be 'right' or 'down'")
        composite = Image.new("RGBA", composite_size, (0, 0, 0, 0))
        for img in images:
            temp = Image.new("RGBA", composite_size, (0, 0, 0, 0))
            temp.paste(img, (x, y))
            composite = Image.alpha_composite(composite, temp)
            x += dx
            y += dy
        out_path = os.path.join(os.path.dirname(file_paths[0]), "tilesheet.png")
        composite.save(out_path)
        messagebox.showinfo("Done", f"Saved:\n{out_path}")







    def bmp_to_png(self):
        converted = 0
        skipped = 0
        root_dir = self.select_folder()
        if not root_dir:
            self.log_message("No folder selected.")
            return
        for root, _, files in os.walk(root_dir):
            for file in files:
                if not file.lower().endswith(".bmp"):
                    continue
                bmp_path = os.path.join(root, file)
                png_path = os.path.splitext(bmp_path)[0] + ".png"
                if os.path.exists(png_path) and not self.OVERWRITE:
                    skipped += 1
                    continue
                try:
                    with Image.open(bmp_path) as img:
                        img.save(png_path, "PNG")
                    if self.DELETE_ORIGINAL:
                        os.remove(bmp_path)
                    converted += 1
                    self.log_message(f"✔ {bmp_path} → {png_path}")
                except Exception as e:
                    self.log_message(f"✖ Failed: {bmp_path} ({e})")
        self.log_message("\n--- Done ---")
        self.log_message(f"Converted: {converted}")
        self.log_message(f"Skipped:   {skipped}")