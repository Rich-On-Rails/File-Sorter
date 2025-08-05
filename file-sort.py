import ffmpeg
import os
import shutil
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

# --- CONFIG ---
ffmpeg_path = r"C:\ffmpeg\bin\ffprobe.exe"  
VIDEO_EXTENSIONS = ['.mp4', '.mov', '.m4v', '.avi', '.mkv']
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic']
DEFAULT_INBOX = r"E:\Inbox"
DRIVE_ROOT = os.path.splitdrive(DEFAULT_INBOX)[0] + os.sep

if not os.path.exists(DRIVE_ROOT):
    raise RuntimeError(f"Drive {DRIVE_ROOT} does not exist")

VIDEO_BASE_DIR = os.path.join(DRIVE_ROOT, "Videos", "Raw Videos")
PHOTO_BASE_DIR = os.path.join(DRIVE_ROOT, "Photography")

# --- Orientation Detection ---
def get_video_orientation(path):
    try:
        probe = ffmpeg.probe(path)
        video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
        width = int(video_stream['width'])
        height = int(video_stream['height'])

        rotation = 0
        if 'tags' in video_stream and 'rotate' in video_stream['tags']:
            rotation = int(video_stream['tags']['rotate'])

        side_data = video_stream.get("side_data_list", [])
        for item in side_data:
            if "rotation" in item:
                rotation = int(item["rotation"])

        if rotation in [90, 270, -90, -270]:
            width, height = height, width

        if width > height:
            return "Landscape"
        elif height > width:
            return "Portrait"
        else:
            return "Square"
    except Exception as e:
        return f"Error: {e}"

# --- File Sorting Logic ---
def sort_files(inbox_path, project_name, dry_run, output_box):
    now = datetime.now()
    year = now.year
    month = now.strftime('%m')  # 01 to 12

    # Video directories
    project_path = os.path.join(VIDEO_BASE_DIR, str(year), project_name)
    shorts_path = os.path.join(project_path, "Shorts")
    youtube_path = os.path.join(project_path, "YouTube")
    uploaded_path = os.path.join(project_path, "Uploaded")

    # Image directory
    photo_path = os.path.join(PHOTO_BASE_DIR, str(year), month, project_name)

    if not os.path.isdir(inbox_path):
        output_box.insert(tk.END, f"[Error] Inbox path doesn't exist: {inbox_path}\n")
        return
    
    files = [f for f in os.listdir(inbox_path) if os.path.isfile(os.path.join(inbox_path, f))]
    if not files:
        output_box.insert(tk.END, "[Info] Inbox is empty. Nothing to sort.\n")
        output_box.see(tk.END)
        return

    for filename in os.listdir(inbox_path):
        
        file_path = os.path.join(inbox_path, filename)
        ext = os.path.splitext(filename)[1].lower()

        if not os.path.isfile(file_path):
            continue

        if ext in VIDEO_EXTENSIONS:
            orientation = get_video_orientation(file_path)

            if isinstance(orientation, str) and orientation.startswith("Error"):
                output_box.insert(tk.END, f"[Error] {filename} → {orientation}\n")
                continue

            if orientation == "Portrait":
                os.makedirs(shorts_path, exist_ok=True)
                dest = os.path.join(shorts_path, filename)
                msg = f"[Portrait]   {filename} → {'Would move' if dry_run else 'Moving'} to {dest}"
            else:
                os.makedirs(youtube_path, exist_ok=True)
                dest = os.path.join(youtube_path, filename)
                msg = f"[{orientation}] {filename} → {'Would move' if dry_run else 'Moving'} to {dest}"

        elif ext in IMAGE_EXTENSIONS:
            os.makedirs(photo_path, exist_ok=True)
            dest = os.path.join(photo_path, filename)
            msg = f"[Image] {filename} → {'Would move' if dry_run else 'Moving'} to {dest}"

        else:
            continue  # Skip unknown files

        output_box.insert(tk.END, msg + "\n")
        output_box.see(tk.END)

        if not dry_run:
            try:
                shutil.move(file_path, dest)
            except Exception as e:
                output_box.insert(tk.END, f"[Move Error] {filename} → {e}\n")

# --- GUI Setup ---
def browse_folder():
    selected = filedialog.askdirectory()
    if selected:
        inbox_var.set(selected)

def on_sort():
    inbox = inbox_var.get()
    project = project_var.get().strip()
    dry_run = dry_var.get()

    output_box.delete(1.0, tk.END)
    if not project:
        messagebox.showerror("Missing Info", "Please enter a project name.")
        return

    sort_files(inbox, project, dry_run, output_box)

# --- GUI Build ---
root = tk.Tk()
root.title("Video Orientation Sorter")

inbox_var = tk.StringVar(value=DEFAULT_INBOX)
project_var = tk.StringVar()
dry_var = tk.BooleanVar(value=True)

tk.Label(root, text="Inbox Folder:").grid(row=0, column=0, sticky='w')
tk.Entry(root, textvariable=inbox_var, width=60).grid(row=0, column=1, padx=5)
tk.Button(root, text="Browse", command=browse_folder).grid(row=0, column=2)

tk.Label(root, text="Project Name:").grid(row=1, column=0, sticky='w')
tk.Entry(root, textvariable=project_var, width=40).grid(row=1, column=1, padx=5, sticky='w')

tk.Checkbutton(root, text="Dry Run (Don't move files)", variable=dry_var).grid(row=2, column=1, sticky='w')

tk.Button(root, text="Sort Files", command=on_sort).grid(row=3, column=1, pady=10, sticky='w')

output_box = scrolledtext.ScrolledText(root, width=100, height=20)
output_box.grid(row=4, column=0, columnspan=3, padx=5, pady=5)

root.mainloop()