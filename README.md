# Video & Image Sorter (with Orientation Detection)

A Python desktop utility with a Tkinter GUI for automatically sorting videos and images into structured folders based on their type and orientation.  
It uses **FFmpeg** (`ffprobe`) to detect video orientation, allowing portrait videos to be separated (e.g., for shorts) from landscape videos (e.g., for YouTube content).

---

## Features

- **Automatic File Sorting**  
  Sorts videos and images into pre-defined folder structures for projects.
  
- **Video Orientation Detection**  
  Uses `ffprobe` from the FFmpeg suite to identify **Portrait**, **Landscape**, and **Square** videos.

- **Dry Run Mode**  
  Preview file moves before actually performing them.

- **Custom Project Naming**  
  Files are sorted into directories named after the selected project.

- **User-Friendly GUI**  
  Built with Tkinter for easy folder selection, configuration, and progress viewing.

---

## Requirements

- **Python** 3.7+
- **FFmpeg** installed locally and accessible via `ffprobe`
- `pip` packages:
  - `ffmpeg-python`
  - Standard library modules (`os`, `shutil`, `tkinter`, `datetime`)

---

## Installation

1. **Clone this repository**

```bash
   git clone https://github.com/yourusername/video-image-sorter.git
   cd video-image-sorter
```

2. Install dependencies

```bash
pip install ffmpeg-python
```

3. Install FFmpeg
- Download FFmpeg from: https://ffmpeg.org/download.html
- Extract it and update the ffmpeg_path variable in the script to match your system.

## Configuration

Edit the script’s CONFIG section to suit your environment:

```python
ffmpeg_path = r"C:\ffmpeg\bin\ffprobe.exe"  # Path to ffprobe
VIDEO_EXTENSIONS = ['.mp4', '.mov', '.m4v', '.avi', '.mkv']
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic']
DEFAULT_INBOX = r"E:\Inbox"                 # Default folder to scan
```

The folder structure is generated automatically:

```bash
Videos/
  Raw Videos/
    <Year>/
      <Project Name>/
        Shorts/
        YouTube/
        Uploaded/

Photography/
  <Year>/<Month>/<Project Name>/
```

## Usage 

1. Run the script

```bash
python sorter.py
```

2. In the GUI:

- Inbox Folder: Choose the folder containing your unsorted videos and images.

- Project Name: Enter the name for the current batch/project.

- Dry Run: Enable to preview moves without changing files.

- Click Sort Files.

3. The output log will display:

- File name

- Detected orientation/type

- Destination path

- Whether the move was performed

## Example Output

```bash
[Portrait]   clip1.mp4 → Would move to E:\Videos\Raw Videos\2025\ProjectX\Shorts\clip1.mp4
[Landscape] clip2.mp4 → Would move to E:\Videos\Raw Videos\2025\ProjectX\YouTube\clip2.mp4
[Image]     photo1.jpg → Would move to E:\Photography\2025\08\ProjectX\photo1.jpg
```

## Known Limitations

- Only supports file extensions listed in `VIDEO_EXTENSIONS` and `IMAGE_EXTENSIONS`.

- Requires FFmpeg to be installed locally.

- Designed for Windows paths — Linux/Mac users will need to adjust directory defaults.