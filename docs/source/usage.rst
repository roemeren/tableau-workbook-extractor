Usage
=====

Running Locally (Windows)
-------------------------

Install Graphviz
^^^^^^^^^^^^^^^^
(to do)

Run the tool from the terminal
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Open a new terminal
- Set the working directory to the repo's root directory
- Create a virtual environment called `.venv` (if not present yet): `python -m venv .venv``
- If needed temporarily override PowerShell's execution policy: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
- Activate the virtual environment: `.\.venv\Scripts\activate`
- Install dependencies: `pip install -r app/requirements.txt`
- Change the working directory to the `app` subfolder: `cd app`
- Run the tool: `python cli_main.py`

### Running in Docker
- Build the Docker container: `docker build -t tableau-extractor .`
- Run the container: `docker run -p 5000:5000 tableau-extractor`

### Using the Pre-built Executable
- Download the executable from the [GitHub Releases page](https://github.com/yourusername/yourrepo/releases).