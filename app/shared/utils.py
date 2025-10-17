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

def get_app_version():
    """Return the app version from VERSION file"""
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text().strip()
    return "unknown"
