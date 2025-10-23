# import fixes
import os
from pathlib import Path

STATIC_FOLDER = os.path.join('web', 'static')
UPLOAD_FOLDER = os.path.join(STATIC_FOLDER, 'uploads')
OUTPUT_FOLDER = os.path.join(STATIC_FOLDER, 'output')
OUTPUT_FOLDER_URL = os.path.relpath(OUTPUT_FOLDER, start="web")

# Keep SAMPLE_FOLDER as a Path object for easy file listing with glob() in app
SAMPLE_FOLDER = Path(STATIC_FOLDER) / 'sample'
COLOR_PROCESSING = '#343a40'
VERSION_FILE = Path("VERSION")
REPO_URL = "https://github.com/roemeren/tableau-workbook-extractor"
ICON_REPO = "assets/repo-icon.png"
APP_HEADER = "Tableau Workbook Extractor"
APP_DESCR = "Upload a Tableau workbook to analyze its dependencies."
DEBUG_MODE = True
SELECTED_NODE_PENWIDTH = 6
SELECTED_EDGE_PENWIDTH = 6
MESSAGE_NO_DATA = "(no data available)"

def get_app_version():
    """Return the app version from VERSION file"""
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text().strip()
    return "unknown"

def list_subfolders(base_dir):
    """Return all subfolders inside assets/<base_dir>."""
    if not os.path.exists(base_dir):
        return []

    return [
        f for f in os.listdir(base_dir)
        if os.path.isdir(os.path.join(base_dir, f))
    ]

def list_dot_files(base_dir, subfolder):
    """Return all .dot filenames (without extension) inside a subfolder."""
    subfolder_path = os.path.join(base_dir, subfolder)
    if not os.path.exists(subfolder_path):
        return []
    return [
        os.path.splitext(f)[0]
        for f in os.listdir(subfolder_path)
        if f.endswith(".dot")
    ]

def read_dot_file(base_dir, subfolder, filename):
    """Return the raw DOT source for the given folder + file."""
    path = os.path.join(base_dir, subfolder, f"{filename}.dot")
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
