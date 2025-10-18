import base64
import threading
import psutil
from dash import no_update, Dash, html, dcc, Output, Input, State, dash_table
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from dash import callback_context as ctx
import time
from shared.utils import *
from shared.processing import process_twb
from shared.common import progress_data
import shutil

# --- initialize folders ---
os.makedirs(STATIC_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# --- module-level state ---
_processing_thread = None

# --- initialize app ---
# Themes: see https://www.dash-bootstrap-components.com/docs/themes/explorer/
app = Dash(__name__, external_stylesheets=[dbc.themes.ZEPHYR])
server = app.server

# Check memory usage before processing
process = psutil.Process(os.getpid())
print(f"Memory usage after initializing application: {process.memory_info().rss / 1024**2:.2f} MB")

# ---------- Layout ----------
app.layout = dbc.Container(
    [
        dbc.Row([
            # Left panel
            dbc.Col(
                [
                    # =======================
                    # FILE SELECTION SECTION
                    # =======================
                    html.H5("Select Tableau Workbook", className="mb-3", style={"fontWeight": "600"}),

                    dbc.Tabs(
                        id="file-tabs",
                        active_tab="tab-sample",  # default tab
                        children=[
                            dbc.Tab(
                                label="Use Sample",
                                tab_id="tab-sample", # id within tabs container
                                id="tab-sample-content", # Dash component ID
                                children=[
                                    html.Div(
                                        [
                                            dbc.Label("Select a sample Tableau workbook"),
                                            dcc.Dropdown(
                                                id="sample-file-dropdown",
                                                options=[
                                                    {"label": f.name, "value": str(f)}
                                                    for f in SAMPLE_FOLDER.glob("*.twb*")
                                                ],
                                                placeholder="Choose sample workbook...",
                                                style={"width": "100%", "marginBottom": "33px"},
                                            ),
                                        ],
                                        className="p-2",
                                    ),
                                ],
                            ),
                            dbc.Tab(
                                label="Upload Your Own",
                                tab_id="tab-upload", # id within tabs container
                                id="tab-upload-content", # Dash component ID
                                children=[
                                    html.Div(
                                        [
                                            dcc.Upload(
                                                id="upload-zip",
                                                children=html.Div(["Drag & Drop or ", html.A("Browse for Workbook")]),
                                                accept=".twb,.twbx",
                                                multiple=False,
                                                style={
                                                    "width": "100%", "height": "60px", "lineHeight": "60px",
                                                    "borderWidth": "1px", "borderStyle": "dashed",
                                                    "borderRadius": "5px", "textAlign": "center",
                                                    "marginBottom": "10px",
                                                },
                                            ),
                                            html.Div(
                                                id="browse-info",
                                                style={"fontSize": "14px", "color": COLOR_PROCESSING, "marginBottom": "10px"},
                                            ),
                                        ],
                                        className="p-2",
                                    ),
                                ],
                            ),
                        ],
                        style={"marginBottom": "5px"},
                    ),

                    dbc.Button(
                        "Process Workbook", 
                        id="btn-process", 
                        color="primary",
                        className="mb-3"
                    ),

                    dbc.Progress(
                        id="progress",
                        value=0,
                        striped=True,
                        animated=True,
                        className="mb-3",
                    ),

                    html.Div(
                        id="processing-status",
                        style={
                            "padding": "2px 8px",
                            "fontFamily": "monospace",
                            "color": COLOR_PROCESSING,
                            "fontSize": "0.85rem",
                            "minHeight": "2em",  # ensures one-line height
                        },
                        className="mb-1",
                    ),

                    dbc.Button(
                        "Download Results",
                        id="btn-download",
                        color="success",
                        className="mt-1",
                        external_link=True,
                        style={"visibility": "hidden"}  # keeps layout space
                    ),

                    html.Hr(className="my-4", style={"borderTop": "2px solid #ccc"}),

                    # =======================
                    # META INFO
                    # =======================
                    html.Div([
                        html.Div(f"App version: {get_app_version()}"),
                        html.Div([
                            "Project page: ",
                            html.A("GitHub", href=REPO_URL, target="_blank"),
                        ]),
                    ], style={"fontSize": "12px", "color": "#666", "marginTop": "10px", "lineHeight": "1.4"}),

                    # =======================
                    # HIDDEN ELEMENTS
                    # =======================
                    # hidden polling interval
                    dcc.Interval(id="progress-poller", interval=2000, disabled=True),
                    # stores for some of the callback outputs
                    dcc.Store(id="file-ready"),
                    dcc.Store(id="processing-started"),
                    # store selected sample file
                    dcc.Store(id="sample-file-store", data={}),
                ],
                # left panel width: around 2.5/12 (22%)
                width = "auto",
                className="p-3 rounded",
                style={"flex": "0 0 22%", "backgroundColor": "#f0f0f0"},
            ),
            # Right panel
            dbc.Col(
                [
                    # Header row
                    html.Div([
                        dbc.Row([
                            dbc.Col([
                                html.Div([
                                    html.Img(
                                        src=ICON_REPO,
                                        height="110px",
                                        style={"marginRight": "15px"}
                                    ),
                                    html.Div([
                                        html.H1(APP_HEADER, className="my-2 display-4 mb-0"),
                                        html.P(APP_DESCR, className="text-muted mb-4"),
                                    ], style={"textAlign": "center"}
                                    ),
                                ], style={
                                    "display": "flex",
                                    "alignItems": "center",
                                    "justifyContent": "center"
                                }),
                            ])
                        ], 
                        className="align-items-center justify-content-center g-0",
                        style={
                            "backgroundColor": "#E6F7FF",
                            "marginBottom": "10px",     # spacing below header
                            "borderRadius": "8px"
                        },
                        ),
                    ]),

                    # KPI row
                    dbc.Row([
                        dbc.Col(
                            dbc.Card(
                                dbc.CardBody([
                                    html.H5("KPI 1", className="text-center mb-2"),

                                    # KPI row: icon + number
                                    html.Div([
                                        html.Img(
                                            src="https://img.icons8.com/ios/50/marker--v1.png",
                                            width="36",
                                            height="36",
                                            style={"marginRight": "8px"}
                                        ),
                                        html.H2(id="kpi-totnodes", children="–", className="mb-0"),
                                    ],
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "justifyContent": "center"
                                    }),

                                    html.Div(
                                        f"out of ...",
                                        className="text-center text-muted",
                                        style={"fontSize": "12px", "marginTop": "4px"}
                                    ),
                                ])
                            ),
                            width=3
                        ),
                        dbc.Col(
                            dbc.Card(
                                dbc.CardBody([
                                    html.H5("KPI 2", className="text-center mb-2"),

                                    # KPI row: icon + number
                                    html.Div([
                                        html.Img(
                                            src="https://img.icons8.com/material-rounded/48/journey.png",
                                            width="36",
                                            height="36",
                                            style={"marginRight": "8px"}
                                        ),
                                        html.H2(id="kpi-totsegments", children="–", className="mb-0"),
                                    ],
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "justifyContent": "center"
                                    }),

                                    html.Div(
                                        f"out of ...",
                                        className="text-center text-muted",
                                        style={"fontSize": "12px", "marginTop": "4px"}
                                    ),
                                ])
                            ),
                            width=3
                        ),
                        dbc.Col(
                            dbc.Card(
                                dbc.CardBody([
                                    html.H5("KPI 3", className="text-center mb-2"),

                                    # KPI row: icon + number
                                    html.Div([
                                        html.Img(
                                            src="https://img.icons8.com/ios/50/length.png",
                                            width="36",
                                            height="36",
                                            style={"marginRight": "8px"}
                                        ),
                                        html.H2(id="kpi-totlength", children="–", className="mb-0"),
                                    ],
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "justifyContent": "center"
                                    }),

                                    html.Div(
                                        f"out of ...",
                                        className="text-center text-muted",
                                        style={"fontSize": "12px", "marginTop": "4px"}
                                    ),
                                ])
                            ),
                            width=3
                        ),
                        dbc.Col(
                            dbc.Card(
                                dbc.CardBody([
                                    html.H5("KPI 4", className="text-center mb-2"),

                                    # KPI row: icon + value
                                    html.Div([
                                        html.Img(
                                            src="https://img.icons8.com/ios/50/checked--v1.png",
                                            width="36",
                                            height="36",
                                            style={"marginRight": "8px"}
                                        ),
                                        html.H2(id="kpi-tottracks", children="–", className="mb-0"),
                                    ],
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "justifyContent": "center"
                                    }),

                                    html.Div(
                                        f"out of ...",
                                        className="text-center text-muted",
                                        style={"fontSize": "12px", "marginTop": "4px"}
                                    ),
                                ])
                            ),
                            width=3
                        ),
                    ], className="mb-3"),
                ],
                # right panel width: fill up leftover space
                style={"flex": "1"}
            )
        ])
    ],
    fluid=True
)

# ---------- Callbacks ----------
@app.callback(
    Output("file-ready", "data"),
    Output("upload-zip", "filename"),
    Output("sample-file-store", "data"),
    Input("file-tabs", "active_tab"),
    Input("upload-zip", "contents"),
    State("upload-zip", "filename"),
    Input("sample-file-dropdown", "value"),
    State("sample-file-store", "data"),
    prevent_initial_call=True
)
def handle_file_selection(active_tab, upload_contents, upload_filename, sample_path, sample_filename):
    """
    Handle both sample selection and user uploads depending on the active tab.
    No file copying is needed for samples since they are served directly
    from the static/sample folder.
    """
    # sample tab: simply register the selected sample file
    if active_tab == "tab-sample":
        if sample_path:
            sample_basename = os.path.basename(sample_path)
            return True, upload_filename, sample_basename
        return upload_filename is not None, upload_filename, None

    # upload tab: decode uploaded file if provided
    if active_tab == "tab-upload" and upload_contents and upload_filename:
        dest_path = os.path.join(UPLOAD_FOLDER, upload_filename)
        if not os.path.exists(dest_path):
            _, content_string = upload_contents.split(",", 1)
            with open(dest_path, "wb") as f:
                f.write(base64.b64decode(content_string))
        return True, upload_filename, sample_filename

    raise PreventUpdate

@app.callback(
    Output("browse-info", "children"),
    Input("upload-zip", "contents"),
    State('upload-zip', 'filename')
)
def show_info(_, f):
    """Display selected filename from upload component (if available)"""
    if f is None:
        return "No file selected"
    return f"Selected file: {f}"

@app.callback(
    Output("processing-started", "data"),
    Input("btn-process", "n_clicks"),
    State("upload-zip", "filename"),
    State("sample-file-store", "data"),
    State("file-ready", "data"),
    State("file-tabs", "active_tab"),
    prevent_initial_call=True
)
def start_processing(_, upload_filename, sample_filename, file_ready, active_tab):
    """
    Triggered by the 'Process ZIP' button.
    Decides which file (uploaded or sample) to process based on the active tab.
    """
    # guard clause: proceed only if a file has been fully saved to disk
    if not file_ready:
        raise PreventUpdate
    
    # get file name based on active tab
    if active_tab == "tab-upload":
        if not upload_filename:
            raise PreventUpdate
        filename = upload_filename
        input_folder = UPLOAD_FOLDER
    elif active_tab == "tab-sample":
        if not sample_filename:
            raise PreventUpdate
        filename = sample_filename
        input_folder = str(SAMPLE_FOLDER)

    # initialize additional progress data
    progress_data["progress"] = 0 # ensures correct progress bar behavior
    progress_data["current-task"] = f"Preparing to process {filename}"
    progress_data["show-dots"] = True

    # calculate file path and relative path used in download links (public URL)
    filepath = os.path.join(input_folder, filename)

    def worker():
        progress_data["status"] = "running"

        error_msg = process_twb(
            filepath=filepath, 
            output_folder=OUTPUT_FOLDER, 
            is_executable=False,
            fPNG=True
        )

        progress_data["show-dots"] = False

        # early exit if an error was returned
        if error_msg:
            progress_data['output_file'] = None
            progress_data["current-task"] = f"Processing failed for {filename}: {error_msg}"
            progress_data["status"] = "exited"
            progress_data["progress"] = 100
            return

        progress_data["current-task"] = f"Finished processing {filename}"
        # store timestamp for deactivation of polling
        progress_data["status"] = "finished"
        progress_data["finished_at"] = time.time()
        progress_data["progress"] = 100

    # assign to the module-level variable, not a new local variable
    global _processing_thread
    _processing_thread = threading.Thread(target=worker)
    _processing_thread.start()

    # no data returned but store write action will trigger update_progress
    return True

@app.callback(
    Output("progress", "value"),
    Output("progress", "label"),
    Output("progress-poller", "disabled"),
    Output("processing-status", "children"),
    Output("btn-process", "disabled"),
    Output("btn-download", "disabled"),
    Output("btn-download", "href"),
    Output("btn-download", "style"),
    Output("upload-zip", "disabled"),
    Output("sample-file-dropdown", "disabled"),
    Output("tab-upload-content", "disabled"),
    Output("tab-sample-content", "disabled"),
    Input("progress-poller", "n_intervals"), # initially None
    Input("processing-started", "data"), # will (re)activate the poller
    State("file-tabs", "active_tab"),
    prevent_initial_call=True
)
def update_progress(*args):
    # Get active tab
    active_tab = args[-1]

    # Animate dots
    current_task = progress_data.get("current-task", "")
    prev_task = progress_data.get("previous-task", "")
    progress_data["dot-count"] = 0 if current_task != prev_task \
        else (progress_data.get("dot-count", 0) + 1) % 4
    progress_data["previous-task"] = current_task
    dots = "." * progress_data["dot-count"] if progress_data.get("show-dots") else ""
    current_task += dots

    # Base UI state while processing
    pct = progress_data.get("progress", 0)
    label = f"{pct}%" if pct >= 5 else ""
    btn_disabled = True
    out_file = progress_data.get("filename")
    # Build href only if out_file exists
    href = out_file and os.path.join(OUTPUT_FOLDER_URL, out_file)
    style = {"width": "40%", "visibility": "hidden"}
    finished_at = progress_data.get("finished_at")
    status = progress_data.get("status")
    poller_disabled = False
    upload_tab_disabled = (active_tab == "tab-sample")
    sample_tab_disabled = not upload_tab_disabled

    # Handle completion
    if status == "exited":
        # Early exit → reset immediately
        pct = 0
        label = ""
        poller_disabled = True
        btn_disabled = False
        upload_tab_disabled = False
        sample_tab_disabled = False
    elif status == "finished":
        # Normal completion: wait 3s before progress bar reset
        if time.time() - finished_at >= 3:
            pct = 0
            label = ""
            poller_disabled = True
            btn_disabled = False
            style["visibility"] = "visible"
            upload_tab_disabled = False
            sample_tab_disabled = False

    return (
        pct,
        label,
        poller_disabled,
        current_task,
        btn_disabled,
        btn_disabled,
        href,
        style,
        btn_disabled,
        btn_disabled,
        upload_tab_disabled,
        sample_tab_disabled,
    )

if __name__ == '__main__':
    app.run(debug=DEBUG_MODE)
