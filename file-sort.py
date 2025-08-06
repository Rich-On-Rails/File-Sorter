import ffmpeg, os, shutil, json, subprocess
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ExifTags

VIDEO_EXTENSIONS = [".mp4", ".mov", ".m4v", ".avi", ".mkv"]
IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic"]
DEFAULT_INBOX = r"E:\Inbox"
DRIVE_ROOT = os.path.splitdrive(DEFAULT_INBOX)[0] + os.sep
VIDEO_BASE_DIR, PHOTO_BASE_DIR = os.path.join(DRIVE_ROOT, "Videos"), os.path.join(
    DRIVE_ROOT, "Photography"
)
ffmpeg_exe = r"C:\ffmpeg\bin\ffmpeg.exe"
DATA_FILE = os.path.join(os.path.dirname(__file__), "video_sorter_data.json")
if not os.path.exists(DRIVE_ROOT):
    raise RuntimeError(f"Drive {DRIVE_ROOT} does not exist")
def load_data():
    return (
        json.load(open(DATA_FILE, "r", encoding="utf-8"))
        if os.path.exists(DATA_FILE)
        else {"locos": [], "locations": []}
    )

def save_data(data):
    json.dump(data, open(DATA_FILE, "w", encoding="utf-8"), indent=4)


data_store = load_data()


def get_video_duration(path):
    try:
        r = subprocess.run(
            [
                ffmpeg_exe.replace("ffmpeg.exe", "ffprobe.exe"),
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return float(r.stdout.strip())
    except:
        return 0.0


def get_recorded_date(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext in VIDEO_EXTENSIONS:
        try:
            tags = ffmpeg.probe(file_path)["format"].get("tags", {})
            if "creation_time" in tags:
                dt = datetime.fromisoformat(
                    tags["creation_time"].replace("Z", "+00:00")
                )
                return dt.year, dt.month, dt.day, True, "Metadata"
        except:
            pass
    elif ext in IMAGE_EXTENSIONS:
        try:
            img = Image.open(file_path)
            exif = img._getexif()
            if exif:
                for t, v in exif.items():
                    if ExifTags.TAGS.get(t) == "DateTimeOriginal":
                        dt = datetime.strptime(v, "%Y:%m:%d %H:%M:%S")
                        return dt.year, dt.month, dt.day, True, "Metadata"
        except:
            pass
    try:
        dt = datetime.fromtimestamp(os.path.getmtime(file_path))
        return dt.year, dt.month, dt.day, False, "Modified Date"
    except:
        return None


def probe_video_orientation(path):
    try:
        vs = next(
            (s for s in ffmpeg.probe(path)["streams"] if s["codec_type"] == "video"),
            None,
        )
        w, h = int(vs["width"]), int(vs["height"])
        r = 0
        if "tags" in vs and "rotate" in vs["tags"]:
            r = int(vs["tags"]["rotate"])
        for d in vs.get("side_data_list", []):
            if "rotation" in d:
                r = int(d["rotation"])
        if r in [90, 270, -90, -270]:
            w, h = h, w
        return "Landscape" if w > h else "Portrait" if h > w else "Square"
    except:
        return "Unknown"


def get_preview_image(file_path, percent):
    try:
        ext = os.path.splitext(file_path)[1].lower()
        ts_str = None
        if ext in VIDEO_EXTENSIONS:
            dur = get_video_duration(file_path)
            ts = max(0, dur * (percent / 100)) if dur > 0 else 1.0
            ts_str = f"{int(ts//3600):02d}:{int((ts%3600)//60):02d}:{ts%60:06.3f}"
            prev = os.path.join(os.path.dirname(file_path), "_preview.jpg")
            subprocess.run(
                [
                    ffmpeg_exe,
                    "-y",
                    "-ss",
                    ts_str,
                    "-i",
                    file_path,
                    "-vframes",
                    "1",
                    prev,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            img = Image.open(prev).copy()
            os.remove(prev)
        elif ext in IMAGE_EXTENSIONS:
            img = Image.open(file_path)
            ts_str = "Image file"
        else:
            return None, None
        img.thumbnail((400, 400))
        return ImageTk.PhotoImage(img), ts_str
    except:
        return None, None


def build_dest_path(
    loco_name, loco_number, location, year, month, day, orientation, is_photo
):
    loco_folder = f"{loco_name}_{loco_number}".replace(" ", "")
    date_str = f"{year:04d}-{month:02d}-{day:02d}"
    if is_photo:
        base = PHOTO_BASE_DIR
        sub = os.path.join(
            loco_folder, "Raw Stills", f"{date_str}_{location.replace(' ','')}"
        )
    else:
        base = VIDEO_BASE_DIR
        t_folder = "Shorts" if orientation == "Portrait" else "Landscape"
    return os.path.join(
        base,
        (
            sub
            if is_photo
            else os.path.join(
                loco_folder,
                "Raw Footage",
                t_folder,
                f"{date_str}_{location.replace(' ','')}",
            )
        ),
    )

QUARANTINE_DIR = os.path.join(DRIVE_ROOT, "FileSorter_Quarantine")
os.makedirs(QUARANTINE_DIR, exist_ok=True)

def move_and_rename(file_path, dest_dir, loco_number, year, location, short_desc, dry_run):
    ext = os.path.splitext(file_path)[1].lower()
    safe_loc = location.replace(" ", "")
    safe_desc = short_desc.replace(" ", "") if short_desc else "Clip"

    base_name = f"{loco_number}-{year}-{safe_loc}-{safe_desc}{ext}"
    dest_file = os.path.join(dest_dir, base_name)

    counter = 1
    while os.path.exists(dest_file):
        dest_file = os.path.join(
            dest_dir,
            f"{loco_number}-{year}-{safe_loc}-{safe_desc}_{counter}{ext}"
        )
        counter += 1

    if dry_run:
        print(f"[DryRun] Would move: {file_path} -> {dest_file}")
        return

    os.makedirs(dest_dir, exist_ok=True)

    try:
        print(f"[INFO] Copying: {file_path} -> {dest_file}")
        shutil.copy2(file_path, dest_file)

        if os.path.exists(dest_file):
            src_size = os.path.getsize(file_path)
            dst_size = os.path.getsize(dest_file)
            if src_size == dst_size:
                os.remove(file_path)
                print(f"[OK] Moved successfully to {dest_file}")
            else:
                print(f"[WARNING] Size mismatch! Moving original to quarantine.")
                shutil.move(file_path, os.path.join(QUARANTINE_DIR, os.path.basename(file_path)))
        else:
            print(f"[ERROR] Destination file missing after copy! Moving original to quarantine.")
            shutil.move(file_path, os.path.join(QUARANTINE_DIR, os.path.basename(file_path)))

    except Exception as e:
        print(f"[MOVE ERROR] {e}")
        print(f"[ACTION] Moving original to quarantine.")
        shutil.move(file_path, os.path.join(QUARANTINE_DIR, os.path.basename(file_path)))

class GalaSorter:
    def __init__(self, master):
        self.master = master
        master.title("Gala Mode Video Sorter")
        self.file_list = []
        self.file_index = 0
        self.inbox_var = tk.StringVar(value=DEFAULT_INBOX)
        self.loco_name_var = tk.StringVar()
        self.loco_number_var = tk.StringVar()
        self.location_var = tk.StringVar()
        self.short_desc_var = tk.StringVar()
        self.year_var = tk.IntVar()
        self.month_var = tk.IntVar()
        self.day_var = tk.IntVar()
        self.same_loco_var = tk.BooleanVar(value=False)
        self.apply_next_var = tk.IntVar(value=1)
        self.dry_run_var = tk.BooleanVar(value=True)
        self.preview_percent_var = tk.IntVar(value=70)
        tk.Label(master, text="Inbox Folder:").grid(row=0, column=0, sticky="w")
        tk.Entry(master, textvariable=self.inbox_var, width=60).grid(row=0, column=1)
        tk.Button(master, text="Browse", command=self.browse_folder).grid(
            row=0, column=2
        )
        tk.Label(master, text="Loco Name:").grid(row=1, column=0, sticky="w")
        self.loco_name_cb = ttk.Combobox(
            master,
            textvariable=self.loco_name_var,
            values=[l["name"] for l in data_store["locos"]],
        )
        self.loco_name_cb.grid(row=1, column=1, sticky="w")
        tk.Label(master, text="Loco Number:").grid(row=2, column=0, sticky="w")
        self.loco_number_cb = ttk.Combobox(
            master,
            textvariable=self.loco_number_var,
            values=[l["number"] for l in data_store["locos"]],
        )
        self.loco_number_cb.grid(row=2, column=1, sticky="w")
        tk.Label(master, text="Location/Event:").grid(row=3, column=0, sticky="w")
        self.location_cb = ttk.Combobox(
            master, textvariable=self.location_var, values=data_store["locations"]
        )
        self.location_cb.grid(row=3, column=1, sticky="w")
        tk.Label(master, text="Short Description:").grid(row=4, column=0, sticky="w")
        tk.Entry(master, textvariable=self.short_desc_var, width=40).grid(
            row=4, column=1, sticky="w"
        )
        tk.Label(master, text="Year:").grid(row=5, column=0, sticky="w")
        self.year_entry = tk.Entry(master, textvariable=self.year_var, width=6)
        self.year_entry.grid(row=5, column=1, sticky="w")
        tk.Label(master, text="Month:").grid(row=6, column=0, sticky="w")
        self.month_entry = tk.Entry(master, textvariable=self.month_var, width=4)
        self.month_entry.grid(row=6, column=1, sticky="w")
        tk.Label(master, text="Day:").grid(row=7, column=0, sticky="w")
        self.day_entry = tk.Entry(master, textvariable=self.day_var, width=4)
        self.day_entry.grid(row=7, column=1, sticky="w")
        tk.Checkbutton(
            master, text="All files same loco/location", variable=self.same_loco_var
        ).grid(row=8, column=1, sticky="w")
        tk.Label(master, text="Apply to next N files:").grid(
            row=9, column=0, sticky="w"
        )
        tk.Entry(master, textvariable=self.apply_next_var, width=5).grid(
            row=9, column=1, sticky="w"
        )
        tk.Checkbutton(master, text="Dry Run", variable=self.dry_run_var).grid(
            row=10, column=1, sticky="w"
        )
        self.preview_label = tk.Label(master)
        self.preview_label.grid(row=0, column=3, rowspan=8, padx=10, pady=10)
        self.timestamp_label = tk.Label(master, text="")
        self.timestamp_label.grid(row=8, column=3, pady=(0, 5))
        tk.Label(master, text="Preview %:").grid(row=9, column=3, sticky="w")
        tk.Spinbox(
            master,
            from_=1,
            to=99,
            textvariable=self.preview_percent_var,
            width=5,
            command=self.update_meta_info,
        ).grid(row=9, column=3, sticky="e")
        tk.Button(
            master,
            text="Regenerate Preview",
            command=lambda: self.show_current_file(regen=True),
        ).grid(row=10, column=3)
        tk.Button(master, text="Load Files", command=self.load_files).grid(
            row=11, column=0
        )
        tk.Button(master, text="Process Next", command=self.process_next).grid(
            row=11, column=1
        )
        tk.Button(master, text="Skip", command=self.skip_file).grid(row=11, column=2)
        self.progress_label = tk.Label(master, text="No files loaded")
        self.progress_label.grid(row=12, column=0, columnspan=4)
        self.meta_text = tk.Text(
            master, height=8, wrap="none", state="disabled", font=("Courier New", 9)
        )
        self.meta_text.grid(row=13, column=0, columnspan=4, sticky="nsew")
        self.copy_path_btn = tk.Button(
            master, text="Copy Destination Path", command=self.copy_dest_path
        )
        self.copy_path_btn.grid(row=14, column=0)
        self.copy_file_btn = tk.Button(
            master, text="Copy Destination File", command=self.copy_dest_file
        )
        self.copy_file_btn.grid(row=14, column=1)
        for v in [
            self.loco_name_var,
            self.loco_number_var,
            self.location_var,
            self.short_desc_var,
            self.year_var,
            self.month_var,
            self.day_var,
        ]:
            v.trace_add("write", lambda *a: self.update_meta_info())

    def browse_folder(self):
        s = filedialog.askdirectory()
        self.inbox_var.set(s) if s else None

    def clear_fields(self):
        self.loco_name_var.set("")
        self.loco_number_var.set("")
        self.location_var.set("")
        self.short_desc_var.set("")
        self.year_var.set(0)
        self.month_var.set(0)
        self.day_var.set(0)

    def load_files(self):
        p = self.inbox_var.get()
        if not os.path.isdir(p):
            return messagebox.showerror("Error", f"Inbox not found: {p}")
        self.file_list = [
            os.path.join(p, f)
            for f in os.listdir(p)
            if os.path.splitext(f)[1].lower() in VIDEO_EXTENSIONS + IMAGE_EXTENSIONS
        ]
        self.file_index = 0
        if not self.file_list:
            return messagebox.showinfo("Info", "No supported files found.")
        self.clear_fields()
        self.show_current_file()

    def show_current_file(self, regen=False):
        if self.file_index >= len(self.file_list):
            return messagebox.showinfo("Done", "All files processed.")
        f = self.file_list[self.file_index]
        rd = get_recorded_date(f)
        if rd:
            y, m, d, locked, src = rd
            self.year_var.set(y)
            self.month_var.set(m)
            self.day_var.set(d)
            st = "disabled" if locked else "normal"
        else:
            self.year_var.set("")
            self.month_var.set("")
            self.day_var.set("")
            st = "normal"
            src = "Manual"
        self.year_entry.config(state=st)
        self.month_entry.config(state=st)
        self.day_entry.config(state=st)
        p, ts = get_preview_image(f, self.preview_percent_var.get())
        (
            self.preview_label.configure(image=p)
            if p
            else self.preview_label.configure(image="", text="No preview")
        )
        self.preview_label.image = p
        self.timestamp_label.config(text=f"Preview at: {ts}" if ts else "")
        if not regen:
            self.progress_label.config(
                text=f"File {self.file_index+1} of {len(self.file_list)}\n{os.path.basename(f)}"
            )
        self.update_meta_info(src)

    def skip_file(self):
        self.file_index += 1
        self.clear_fields()
        self.show_current_file()

    def process_next(self):
        if self.file_index >= len(self.file_list):
            return
        f = self.file_list[self.file_index]
        ext = os.path.splitext(f)[1].lower()
        year = self.year_var.get()        
        ori = None
        is_photo = False
        if ext in VIDEO_EXTENSIONS:
            ori = probe_video_orientation(f)
        elif ext in IMAGE_EXTENSIONS:
            is_photo = True
        dest = build_dest_path(
            self.loco_name_var.get(),
            self.loco_number_var.get(),
            self.location_var.get(),
            year,
            self.month_var.get(),
            self.day_var.get(),
            ori,
            is_photo,
        )
        le = {"name": self.loco_name_var.get(), "number": self.loco_number_var.get()}
        if le not in data_store["locos"]:
            data_store["locos"].append(le)
        if self.location_var.get() not in data_store["locations"]:
            data_store["locations"].append(self.location_var.get())
        save_data(data_store)
        self.loco_name_cb.config(values=[l["name"] for l in data_store["locos"]])
        self.loco_number_cb.config(values=[l["number"] for l in data_store["locos"]])
        self.location_cb.config(values=data_store["locations"])        
        move_and_rename(
            f,
            dest,
            self.loco_number_var.get(),
            year,
            self.location_var.get(),
            self.short_desc_var.get(),
            self.dry_run_var.get(),
        )
        n = (
            self.apply_next_var.get()
            if not self.same_loco_var.get()
            else len(self.file_list) - self.file_index
        )
        self.file_index += 1
        n -= 1
        while n > 0 and self.file_index < len(self.file_list):
            f = self.file_list[self.file_index]
            ext = os.path.splitext(f)[1].lower()
            is_photo = ext in IMAGE_EXTENSIONS
            ori = probe_video_orientation(f) if not is_photo else None
            dest = build_dest_path(
                self.loco_name_var.get(),
                self.loco_number_var.get(),
                self.location_var.get(),
                year,
                self.month_var.get(),
                self.day_var.get(),
                ori,
                is_photo,
            )
            le = {"name": self.loco_name_var.get(), "number": self.loco_number_var.get()}
            if le not in data_store["locos"]:
                data_store["locos"].append(le)
            if self.location_var.get() not in data_store["locations"]:
                data_store["locations"].append(self.location_var.get())
            save_data(data_store)
            self.loco_name_cb.config(values=[l["name"] for l in data_store["locos"]])
            self.loco_number_cb.config(values=[l["number"] for l in data_store["locos"]])
            self.location_cb.config(values=data_store["locations"]) 
            move_and_rename(
                f,
                dest,
                self.loco_number_var.get(),
                year,
                self.location_var.get(),
                self.short_desc_var.get(),
                self.dry_run_var.get(),
            )
            self.file_index += 1
            n -= 1
        self.show_current_file()

    def update_meta_info(self, date_source="Manual"):
        if not self.file_list or self.file_index >= len(self.file_list):
            return

        f = self.file_list[self.file_index]

        dest_dir = build_dest_path(
            self.loco_name_var.get(),
            self.loco_number_var.get(),
            self.location_var.get(),
            self.year_var.get(),
            self.month_var.get(),
            self.day_var.get(),
            probe_video_orientation(f) if os.path.splitext(f)[1].lower() in VIDEO_EXTENSIONS else None,
            os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS
        )

        ext = os.path.splitext(f)[1].lower()
        safe_loc = self.location_var.get().replace(" ", "")
        safe_desc = (self.short_desc_var.get() or "Clip").replace(" ", "")
        base_name = f"{self.loco_number_var.get()}-{self.year_var.get()}-{safe_loc}-{safe_desc}{ext}"
        dest_file = os.path.join(dest_dir, base_name)

        counter = 1
        while os.path.exists(dest_file):
            dest_file = os.path.join(
                dest_dir,
                f"{self.loco_number_var.get()}-{self.year_var.get()}-{safe_loc}-{safe_desc}_{counter}{ext}"
            )
            counter += 1

        ctime = datetime.fromtimestamp(os.path.getctime(f)).strftime("%Y-%m-%d %H:%M:%S")
        mtime = datetime.fromtimestamp(os.path.getmtime(f)).strftime("%Y-%m-%d %H:%M:%S")

        self.meta_text.config(state="normal")
        self.meta_text.delete("1.0", "end")
        self.meta_text.insert("end", f"File Path: {f}\n")
        self.meta_text.insert("end", f"File Name: {os.path.basename(f)}\n")
        self.meta_text.insert("end", f"Create Date: {ctime}\n")
        self.meta_text.insert("end", f"Modified Date: {mtime}\n")

        if date_source == "Metadata":
            self.meta_text.insert("end", f"Date Source: {date_source}\n", "meta_source")
        elif date_source == "Modified Date":
            self.meta_text.insert("end", f"Date Source: {date_source}\n", "modified_source")
        else:
            self.meta_text.insert("end", f"Date Source: {date_source}\n", "manual_source")

        if os.path.exists(dest_dir):
            self.meta_text.insert("end", f"Destination Folder (exists): {dest_dir}\n", "folder_exists")
        else:
            self.meta_text.insert("end", f"Destination Folder (will be created): {dest_dir}\n", "folder_missing")

        if os.path.exists(dest_file):
            self.meta_text.insert("end", f"Destination File (conflict): {dest_file}", "file_conflict")
        else:
            self.meta_text.insert("end", f"Destination File (no conflicts): {dest_file}", "file_ok")

        self.meta_text.tag_config("folder_exists", foreground="green")
        self.meta_text.tag_config("folder_missing", foreground="red")
        self.meta_text.tag_config("file_ok", foreground="green")
        self.meta_text.tag_config("file_conflict", foreground="orange", font=("Courier New", 9, "bold"))
        self.meta_text.tag_config("meta_source", foreground="green")
        self.meta_text.tag_config("modified_source", foreground="orange")
        self.meta_text.tag_config("manual_source", foreground="grey")

        self.meta_text.config(state="disabled")


    def copy_dest_path(self):
        if not self.file_list or self.file_index >= len(self.file_list):
            return
        f = self.file_list[self.file_index]
        dest = build_dest_path(
            self.loco_name_var.get(),
            self.loco_number_var.get(),
            self.location_var.get(),
            self.year_var.get(),
            self.month_var.get(),
            self.day_var.get(),
            (
                probe_video_orientation(f)
                if os.path.splitext(f)[1].lower() in VIDEO_EXTENSIONS
                else None
            ),
            os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS,
        )
        self.master.clipboard_clear()
        self.master.clipboard_append(dest)

    def copy_dest_file(self):
        if not self.file_list or self.file_index >= len(self.file_list):
            return

        f = self.file_list[self.file_index]
        ext = os.path.splitext(f)[1].lower()

        dest_dir = build_dest_path(
            self.loco_name_var.get(),
            self.loco_number_var.get(),
            self.location_var.get(),
            self.year_var.get(),
            self.month_var.get(),
            self.day_var.get(),
            probe_video_orientation(f) if ext in VIDEO_EXTENSIONS else None,
            ext in IMAGE_EXTENSIONS
        )

        safe_loc = self.location_var.get().replace(" ", "")
        safe_desc = (self.short_desc_var.get() or "Clip").replace(" ", "")
        base_name = f"{self.loco_number_var.get()}-{self.year_var.get()}-{safe_loc}-{safe_desc}{ext}"
        dest_file = os.path.join(dest_dir, base_name)

        counter = 1
        while os.path.exists(dest_file):
            dest_file = os.path.join(
                dest_dir,
                f"{self.loco_number_var.get()}-{self.year_var.get()}-{safe_loc}-{safe_desc}_{counter}{ext}"
            )
            counter += 1

        self.master.clipboard_clear()
        self.master.clipboard_append(dest_file)



root = tk.Tk()
app = GalaSorter(root)
root.mainloop()
