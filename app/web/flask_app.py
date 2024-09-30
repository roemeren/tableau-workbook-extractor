"""
app.py

Flask web application for uploading and processing CSV files.

This application allows users to upload CSV files, which are then processed 
in the background. The progress of the processing is tracked and can be 
queried via a dedicated endpoint.

Key Features:
- Tableau workbook upload via a web form.
- Background processing of Tableau workbook using the `process_twb` function.
- Progress tracking for ongoing processing tasks.
- Progress information is accessible through the `/progress` endpoint.

Configuration:
- Uploads are saved in the `static/uploads` directory, which is created 
  if it does not exist.

Usage:
Run this module to start the Flask development server.
"""

from flask import Flask, render_template, request, jsonify
from shared.processing import process_twb
from shared.common import os, progress_data
import threading

app = Flask(__name__)

# Ensure the upload directory exists
UPLOAD_FOLDER = os.path.join('web', 'static', 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if 'file' not in request.files:
            return "No file part"
        
        file = request.files['file']
        
        if file.filename == '':
            return "No selected file"

        if file and file.filename.endswith(('.twb', '.twbx')):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            
            # Reset progress and filename before processing
            progress_data['progress'] = 0
            progress_data['filename'] = None

            # Start a new thread to run the processing function in the background
            # This allows the Flask app to remain responsive
            thread = threading.Thread(target=run_processing, args=(filepath,))
            thread.start()

    return render_template("index.html")

@app.route("/progress", methods=["GET"])
def progress():
    return jsonify(progress=progress_data['progress'], filename=progress_data['filename'])

def run_processing(filepath):
    """
    Processes a Tableau workbook file in the background.

    This function calls the `process_twb` function to handle the 
    processing of the specified Tableau workbook file. The processing 
    is done using the filepath provided as an argument, with a 
    predefined upload folder and a flag indicating the executable state.

    Args:
        filepath (str): The path to the Tableau workbook file to be processed.

    Returns:
        None
    """
    process_twb(filepath=filepath, uploadfolder=app.config['UPLOAD_FOLDER'], 
                is_executable=False)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')