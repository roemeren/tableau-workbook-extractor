import base64
import threading
import psutil
from dash import no_update, Dash, html, dcc, Output, Input, State, dash_table
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from dash import callback_context as ctx
import dash_interactive_graphviz
import time
import re
from shared.utils import *
from shared.processing import process_twb
from shared.common import progress_data, pd, COL_FILL_MAIN_FIELD, COL_FILL_SHEET
import networkx as nx
import pydot

# --- initialize folders ---
os.makedirs(STATIC_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# --- module-level state ---
_processing_thread = None
_stop_event = threading.Event()

# --- other initializations ---
sample_files = sorted(SAMPLE_FOLDER.glob("*.twb*"), key=lambda f: f.name.casefold())

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
                                                options=[{"label": f.stem, "value": str(f)} for f in sample_files],
                                                placeholder="Choose sample workbook...",
                                                style={"width": "100%", "marginBottom": "33px"},
                                            )
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

                    dbc.Checkbox(
                        id="include-png-checkbox",
                        label="Include PNG files (default is SVG)",
                        value=False,
                        className="ms-3 mt-2",
                    ),

                    dbc.Row(
                        [
                            dbc.Col(
                                dbc.Button(
                                    "Process Workbook",
                                    id="btn-process",
                                    color="primary",
                                    className="mb-3",
                                ),
                                width="auto",
                            ),
                            dbc.Col(
                                dbc.Button(
                                    "Cancel",
                                    id="btn-cancel",
                                    color="secondary",
                                    className="mb-3 ms-2",
                                    style={"visibility": "hidden"},
                                ),
                                width="auto",
                            ),
                        ],
                        className="g-0",  # no gutter spacing
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
                    html.Div(
                        [
                            html.Div(f"App version: {get_app_version()}"),
                            html.Div(
                                [
                                    "Project page: ",
                                    html.A("GitHub", href=REPO_URL, target="_blank"),
                                ]
                            ),
                            html.Div(
                                [
                                    html.Div("Sample dashboards:"),
                                    html.Div(
                                        html.A(
                                            "  CH24_BBOD_ChurnTurnover by Steve Wexler",
                                            href="https://public.tableau.com/app/profile/swexler/viz/CH24_BBOD_ChurnTurnover/SubscriberChurnAnalysis",
                                            target="_blank",
                                        ),
                                        style={"marginLeft": "10px"},
                                    ),
                                    html.Div(
                                        html.A(
                                            "  #RWFD HR Dashboard by Gandes Goldestan",
                                            href="https://public.tableau.com/app/profile/gandes.goldestan/viz/HRDashboard_16284874251120/Overview",
                                            target="_blank",
                                        ),
                                        style={"marginLeft": "10px"},
                                    ),
                                    html.Div(
                                        html.A(
                                            "  Superstore Dashboard by Priya Padham",
                                            href="https://public.tableau.com/app/profile/p.padham/viz/SuperstoreDashboard_16709573699130/SuperstoreDashboard",
                                            target="_blank",
                                        ),
                                        style={"marginLeft": "10px"},
                                    ),
                                ],
                                style={
                                    "fontSize": "12px",
                                    "color": "#666",
                                    "marginTop": "5px",
                                    "lineHeight": "1.4",
                                },
                            ),
                        ],
                        style={
                            "fontSize": "12px",
                            "color": "#666",
                            "marginTop": "10px",
                            "lineHeight": "1.4",
                        },
                    ),

                    # =======================
                    # HIDDEN ELEMENTS
                    # =======================
                    # path to the graphs folder and currently selected file
                    dcc.Store(id="dot-root-store"),
                    dcc.Store(id="df-root-store"),
                    dcc.Store(id="dot-store"),
                    dcc.Store(id="attrs-store"),
                    dcc.Store(id="main-node-store"),
                    # polling interval
                    dcc.Interval(id="progress-poller", interval=2000, disabled=True),
                    # stores for some of the callback outputs
                    dcc.Store(id="file-ready"),
                    dcc.Store(id="processing-started"),
                    # store selected sample file
                    dcc.Store(id="sample-file-store", data={}),
                ],
                
                className="p-3 rounded",
                style={
                    # left panel width: around 2.5/12 (22%)
                    "flex": "0 0 22%",           
                    "backgroundColor": "#f0f0f0",
                    # make sure that column stretches to full browser height
                    "height": "100vh",
                },
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
                                        height="90px",
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
                                    html.H5("No. Fields", className="text-center mb-2"),

                                    # KPI row: icon + number
                                    html.Div([
                                        html.Img(
                                            src="https://img.icons8.com/ios/50/database--v1.png",
                                            width="36",
                                            height="36",
                                            style={"marginRight": "8px"}
                                        ),
                                        html.H2(id="kpi-fields", children="–", className="mb-0"),
                                    ],
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "justifyContent": "center"
                                    }),

                                    html.Div(
                                        id="kpi-fields-unused",
                                        className="text-center text-muted",
                                        style={"fontSize": "12px", "marginTop": "4px"},
                                        children=MESSAGE_NO_DATA,
                                    ),
                                ])
                            ),
                            width=3
                        ),
                        dbc.Col(
                            dbc.Card(
                                dbc.CardBody([
                                    html.H5("No. Calculated Fields", className="text-center mb-2"),

                                    # KPI row: icon + number
                                    html.Div([
                                        html.Img(
                                            src="https://img.icons8.com/ios/50/calculator--v1.png",
                                            width="36",
                                            height="36",
                                            style={"marginRight": "8px"}
                                        ),
                                        html.H2(id="kpi-calcs", children="–", className="mb-0"),
                                    ],
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "justifyContent": "center"
                                    }),

                                    html.Div(
                                        id="kpi-calcs-lod",
                                        className="text-center text-muted",
                                        style={"fontSize": "12px", "marginTop": "4px"},
                                        children=MESSAGE_NO_DATA,
                                    ),
                                ])
                            ),
                            width=3
                        ),
                        dbc.Col(
                            dbc.Card(
                                dbc.CardBody([
                                    html.H5("Avg. Upstream Sources", className="text-center mb-2"),

                                    # KPI row: icon + value
                                    html.Div([
                                        html.Img(
                                            src="https://img.icons8.com/ios/50/link--v1.png",
                                            width="36",
                                            height="36",
                                            style={"marginRight": "8px"}
                                        ),
                                        html.H2(id="kpi-dep", children="–", className="mb-0"),
                                    ],
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "justifyContent": "center"
                                    }),

                                    html.Div(
                                        id="kpi-dep-range",
                                        className="text-center text-muted",
                                        style={"fontSize": "12px", "marginTop": "4px"},
                                        children=MESSAGE_NO_DATA,
                                    ),
                                ])
                            ),
                            width=3
                        ),
                        dbc.Col(
                            dbc.Card(
                                dbc.CardBody([
                                    html.H5("No. Sheets", className="text-center mb-2"),

                                    # KPI row: icon + value
                                    html.Div([
                                        html.Img(
                                            src="https://img.icons8.com/windows/32/filled-note.png",
                                            width="36",
                                            height="36",
                                            style={"marginRight": "8px"}
                                        ),
                                        html.H2(id="kpi-sheets", children="–", className="mb-0"),
                                    ],
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "justifyContent": "center"
                                    }),

                                    html.Div(
                                        id="kpi-sheets-dep",
                                        className="text-center text-muted",
                                        style={"fontSize": "12px", "marginTop": "4px"},
                                        children=MESSAGE_NO_DATA,
                                    ),
                                ])
                            ),
                            width=3
                        ),
                    ], className="mb-3"),

                    # Visualization and control layout
                    dbc.Row(
                        [
                            # Left part
                            dbc.Col(
                                [
                                    # Control row (folder/file/engine)
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    html.Label("Source", className="fw-bold"),
                                                    dcc.Dropdown(
                                                        id="folder-dropdown",
                                                        placeholder="Select folder",
                                                        clearable=False,
                                                    ),
                                                ],
                                                width=3,
                                            ),
                                            dbc.Col(
                                                [
                                                    html.Label("Item", className="fw-bold"),
                                                    dcc.Dropdown(
                                                        id="file-dropdown",
                                                        placeholder="Select file",
                                                    ),
                                                ],
                                                width=3,
                                            ),
                                            dbc.Col(
                                                [
                                                    html.Label("Layout", className="fw-bold"),
                                                    dcc.Dropdown(
                                                        id="layout-dropdown",
                                                        options=[
                                                            {"label": "Left to right", "value": "LR"},
                                                            {"label": "Top to bottom", "value": "TB"},
                                                        ],
                                                        value="LR",
                                                        clearable=False,
                                                    ),
                                                ],
                                                width=3,
                                            ),
                                            dbc.Col(
                                                [
                                                    dbc.Button(
                                                        "Clear selection",
                                                        id="btn-clear-selection",
                                                        color="secondary",
                                                        className="mt-4 ms-2",
                                                    ),
                                                    dbc.Tooltip(
                                                        "Reset the visualization and info panels by \
                                                            clearing the current dependency selection.",
                                                        target="btn-clear-selection",
                                                        placement="bottom",
                                                    ),
                                                ],
                                                width=3,
                                            ),
                                        ],
                                        className="g-3 mb-3 px-2",
                                    ),

                                    # Visualization row
                                    dbc.Row(
                                        [
                                            # Graph container
                                            dbc.Col(
                                                [
                                                    html.H5(
                                                        "Dependency Graph",
                                                        id="network-title",
                                                        className="card-title mb-3"
                                                    ),
                                                    dash_interactive_graphviz.DashInteractiveGraphviz(
                                                        id="gv",
                                                        style={
                                                            "height": "425px",
                                                            "width": "50%",
                                                        }
                                                    ),
                                                ],
                                                width=12,
                                            ),
                                        ],
                                        className="g-3 px-2",
                                    ),
                                ],
                                width=8,
                            ),

                            # Node info panel
                            dbc.Col(
                                [
                                    dbc.Card(
                                        dbc.CardBody(
                                            [
                                                html.H5("Item Info", className="card-title"),
                                                dbc.Tabs(
                                                    id="node-info-tabs",
                                                    active_tab="tab-general-main",
                                                    class_name="mt-2",
                                                    children=[
                                                        dbc.Tab(
                                                            label="Selection",
                                                            tab_id="tab-general-main",
                                                            children=html.Div(
                                                                html.Div(html.I(MESSAGE_NO_DATA), style={"marginTop": "10px"}),
                                                                id="main-element",
                                                                className="small",
                                                                style={
                                                                    "maxHeight": "475px",
                                                                    "overflowY": "auto",
                                                                    "paddingRight": "8px",
                                                                },
                                                            ),
                                                        ),
                                                        dbc.Tab(
                                                            label="Dependency",
                                                            tab_id="tab-general-selection",
                                                            children=html.Div(
                                                                html.Div(html.I(MESSAGE_NO_DATA), style={"marginTop": "10px"}),
                                                                id="selected-element",
                                                                className="small",
                                                                style={
                                                                    "maxHeight": "475px",
                                                                    "overflowY": "auto",
                                                                    "paddingRight": "8px",
                                                                },
                                                            ),
                                                        ),
                                                        dbc.Tab(
                                                            label="Calculation Path",
                                                            tab_id="tab-calc",
                                                            children=[
                                                                dbc.Button(
                                                                    "Expand view",
                                                                    id="open-calc-modal",
                                                                    color="secondary",
                                                                    size="sm",
                                                                    className="mt-2 mb-2",
                                                                ),
                                                                html.Div(
                                                                    html.Div(html.I(MESSAGE_NO_DATA), style={"marginTop": "10px"}),
                                                                    id="selected-element-calc",
                                                                    className="small",
                                                                    style={
                                                                        "maxHeight": "425px",
                                                                        "overflowY": "auto",
                                                                        "paddingRight": "8px",
                                                                    },
                                                                ),
                                                            ]
                                                        ),
                                                    ],
                                                ),
                                            ]
                                        ),
                                        className="shadow-sm",
                                    ),
                                ],
                                width=4,
                            ),
                        ],
                        className="g-3 px-2",
                    ),


                    # Modal popup to display the expanded full calculation
                    dbc.Modal(
                        [
                            dbc.ModalHeader("Expanded View"),
                            dbc.ModalBody(
                                html.Div(
                                    id="calc-modal-content",
                                    style={
                                        "whiteSpace": "pre-wrap",
                                        "fontFamily": "monospace",
                                        "maxHeight": "75vh",
                                        "overflowY": "auto",
                                        "paddingRight": "10px",
                                    },
                                )
                            ),
                            dbc.ModalFooter(
                                dbc.Button("Close", id="close-calc-modal", color="secondary", className="ms-auto")
                            ),
                        ],
                        id="calc-modal",
                        size="xl",  # xl = wide; lg = medium
                        is_open=False,
                    ),
                ],
                # right panel width: fill up leftover space
                style={"flex": "1"},
            )
        ]),
    ],
    fluid=True,
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
    State("include-png-checkbox", "value"),
    prevent_initial_call=True
)
def start_processing(_, upload_filename, sample_filename, 
                     file_ready, active_tab, include_png):
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

        msg = process_twb(
            filepath=filepath, 
            output_folder=OUTPUT_FOLDER, 
            is_executable=False,
            fPNG=include_png,
            stop_event=_stop_event,
        )

        progress_data["show-dots"] = False

        # early exit in case of an error or cancellation
        if msg:
            progress_data["output_file"] = None
            if msg == "Cancelled":
                progress_data["current-task"] = f"Processing cancelled for {filename}"
                progress_data["status"] = "cancelled"
            else:
                progress_data["current-task"] = f"Processing failed for {filename}: {msg}"
                progress_data["status"] = "exited"
            progress_data["progress"] = 100
            return

        progress_data["current-task"] = f"Finished processing {filename}"
        # store timestamp for deactivation of polling
        progress_data["status"] = "finished"
        progress_data["finished_at"] = time.time()
        progress_data["progress"] = 100

    # assign to the module-level variable, not a new local variable
    global _processing_thread, _stop_event
    _stop_event.clear()
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
    Output("dot-root-store", "data"),
    Output("df-root-store", "data"),
    Output("btn-cancel", "style"),
    Output("btn-cancel", "disabled"),
    Output("include-png-checkbox", "disabled"),
    Input("progress-poller", "n_intervals"), # initially None
    Input("processing-started", "data"), # will (re)activate the poller
    Input("btn-cancel", "n_clicks"),
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
    out_folder = progress_data.get("foldername")
    # Build href only if out_file exists
    href = out_file and os.path.join(OUTPUT_FOLDER_URL, out_file)
    graphs_folder = out_folder and os.path.join(out_folder, "Graphs")
    tables_folder = out_folder and os.path.join(out_folder, "Fields")
    style = {"width": "40%", "visibility": "hidden"}
    finished_at = progress_data.get("finished_at")
    status = progress_data.get("status")
    style_cancel = {"visibility": "visible"}
    poller_disabled = False
    cancel_disabled = False
    upload_tab_disabled = (active_tab == "tab-sample")
    sample_tab_disabled = not upload_tab_disabled

    # Handle cancel button click
    trigger_ids = [t["prop_id"].split(".")[0] for t in ctx.triggered]
    if "btn-cancel" in trigger_ids:
        global _processing_thread, _stop_event

        # Signal the worker thread to stop and wait briefly for it to exit
        if _processing_thread and _processing_thread.is_alive():
            _stop_event.set()
            _processing_thread.join(timeout=3)
            if _processing_thread.is_alive():
                print("Warning: background thread still running after timeout.")
                # only persist progress state if still running
                progress_data["status"] = "cancelling"
                progress_data["show_dots"] = True
            else:
                print("Background thread stopped cleanly after cancel request.")
        else:
            print("No active background thread to cancel.")

        # display a temporary 'cancelling' status
        current_task = "Cancelling..."
        cancel_disabled = True
  
    # Handle completion
    if status in ("exited", "cancelled"):
        # Early exit → reset immediately
        pct = 0
        label = ""
        poller_disabled = True
        btn_disabled = False
        upload_tab_disabled = False
        sample_tab_disabled = False
        style_cancel = {"visibility": "hidden"}
    elif status == "cancelling":
        # persist cancelling status until worker stops (for slow environments)
        current_task = "Cancelling" + dots
        cancel_disabled = True
    elif status == "finished":
        style_cancel = {"visibility": "hidden"}
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
        graphs_folder,
        tables_folder,
        style_cancel,
        cancel_disabled,
        btn_disabled,
    )

# Output data -> Folder dropdown
@app.callback(
    Output("folder-dropdown", "options"),
    Output("folder-dropdown", "value"),
    Input("btn-download", "disabled"),
    State("dot-root-store", "data")
)
def update_folder_dropdown(download_disabled, base_dir):
    if not base_dir or download_disabled:
        raise PreventUpdate

    folders = list_subfolders(base_dir)

    # Sort alphabetically, but push "Sheets" and "Parameters" to the end
    folders.sort(key=lambda x: (x in ["Sheets", "Parameters"], x.casefold()))

    options = [{"label": f, "value": f} for f in folders]
    first_value = folders[0] if folders else None

    return options, first_value

# Folder -> update file dropdown
@app.callback(
    Output("file-dropdown", "options"),
    Output("file-dropdown", "value"),
    State("dot-root-store", "data"),
    Input("folder-dropdown", "value"),
)
def update_file_dropdown(base_dir, selected_folder):
    """Update .dot file list based on selected folder."""
    if not selected_folder:
        return [], None

    files = list_dot_files(base_dir, selected_folder)
    files.sort(key=str.casefold)

    options = [{"label": f, "value": f} for f in files]

    # Auto-select first file if available
    return options, files[0] if files else None

# File -> load and parse .dot source
@app.callback(
    Output("dot-store", "data"),
    Output("attrs-store", "data"),
    Output("main-node-store", "data"),
    Input("file-dropdown", "value"),
    Input("layout-dropdown", "value"),
    State("dot-root-store", "data"),
    State("folder-dropdown", "value"),
)
def load_dot_source(selected_file, layout, base_dir, selected_folder):
    """Load the selected .dot file, parse its node attributes, and identify the main node as [id, label]."""
    if not selected_file or not selected_folder:
        raise PreventUpdate

    path = os.path.join(base_dir, selected_folder, f"{selected_file}.dot")
    if not os.path.exists(path):
        raise PreventUpdate

    with open(path, "r", encoding="utf-8") as f:
        dot_text = f.read()

    # --- robust, line-anchored parse of node attributes ---
    node_pattern = r'^\s*"([^"]+)"\s*\[(.*?)\]\s*;'
    attr_pattern = r'(\w+)=("([^"\\]|\\.)*"|[^,\]]+)'  # value is quoted or runs until comma or ']'

    node_attrs = {}
    main_node = None

    for node_match in re.finditer(node_pattern, dot_text, re.MULTILINE | re.DOTALL):
        node_id = node_match.group(1)
        attrs_str = node_match.group(2)

        attrs = {}
        for m in re.finditer(attr_pattern, attrs_str):
            key = m.group(1)
            val = m.group(2).strip()

            # normalize + clean value
            if len(val) >= 2 and val[0] == '"' and val[-1] == '"':
                val = val[1:-1].replace('\\"', '"')
                val = val.replace("\\r\\n", "\n").replace("\\n", "\n")
            else:
                val = val.strip()

            attrs[key] = val

        node_attrs[node_id] = attrs

        # detect the "main" node by fill color
        fill = (attrs.get("fillcolor") or "")
        if fill in (COL_FILL_MAIN_FIELD, COL_FILL_SHEET) and main_node is None:
            main_node = [node_id, attrs.get("label", node_id), fill]

	# ---- apply layout direction (TB or LR) ----
    try:
        lines = dot_text.splitlines()
        if len(lines) > 1 and lines[1].strip().startswith("rankdir="):
            lines[1] = f"rankdir={layout};"
            dot_text = "\n".join(lines)
    except Exception:
        pass

    return dot_text, node_attrs, main_node

@app.callback(
    Output("network-title", "children"),
    Output("main-element", "children"),
    Input("main-node-store", "data"),
    State("df-root-store", "data"),
)
def update_main_node(main_node, df_root):
    if not main_node:
        return "Dependency Graph", None

    try:
        # --- Load data ---
        df = pd.read_parquet(os.path.join(df_root, "fields.parquet"))
        df_dep = pd.read_parquet(os.path.join(df_root, "dependencies.parquet"))

        # --- Identify main field/sheet ---
        main_id, main_label, _ = main_node
        row_field = df.loc[df["source_field_repl_id"] == main_id]

        # Determine category
        if len(row_field) == 1:
            # field or parameter
            rec = row_field.iloc[0]
            cat = rec["field_category"]
            rows_dep = df_dep.loc[df_dep["source_field_repl_id"] == main_id]
        elif len(row_field) == 0:
            # sheet
            rec = None
            rows_dep = df_dep.loc[df_dep["dependency_to"] == main_label]
            cat = "Sheet"

        html_bw, html_fw = None, None

        # --- Dependency statistics ---
        if cat not in ("Field", "Parameter") and not rows_dep.empty:
            mask = rows_dep["dependency_level"] < 0 if cat != "Sheet" \
                else pd.Series(True, index=rows_dep.index)
            rows_filtered = rows_dep.loc[mask]

            row_count = len(rows_filtered)
            min_level_abs = abs(rows_filtered["dependency_level"].min()) \
                if not rows_filtered.empty else 0

            html_bw = html.Li([
                html.B("Upstream sources: "),
                f"{row_count} (max. level: {min_level_abs})" \
                    if cat != "Sheet" else f"{row_count}"
            ])

        if cat != "Sheet":
            rows_filtered = rows_dep.loc[
                (rows_dep["dependency_level"] > 0) & 
                (rows_dep["dependency_category"] != "Sheet")
            ]
            row_count = len(rows_filtered)
            max_level_abs = rows_filtered["dependency_level"].max() \
                if not rows_filtered.empty else 0

            html_fw = html.Li([
                html.B("Upstream sources: "),
                  f"{row_count} (max. level: {max_level_abs})"
            ])

        if cat:
            metadata_section = html.Div(
                [
                    html.B("Field Information", style={"display": "block", "marginBottom": "6px"}),

                    html.Ul(
                        [
                            html.Li([html.B("Data source: "), "Sheets" if cat == "Sheet" else rec["source_label"]]),
                            html.Li([html.B("Category: "), "Sheet" if cat == "Sheet" else rec["field_category"]]),
                            html.Li([html.B("Data type: "), "(not applicable)" if cat == "Sheet" else rec["field_datatype"]]),
                            html.Li([html.B("Role: "), "(not applicable)" if cat == "Sheet" else rec["field_role"]]),
                            html_bw,
                            html_fw,
                        ],
                        style={"marginLeft": "10px"},
                    ),
                ],
                style={
                    "marginBottom": "12px",
                    "padding": "8px 10px",
                    "backgroundColor": "#f9f9f9",
                    "borderRadius": "6px",
                    "border": "1px solid #ddd",
                },
            )
        else:
            metadata_section = html.Div(MESSAGE_NO_DATA)

    except Exception as e:
        print(f"Error processing parquet files in update_main_node: {e}")
        raise PreventUpdate
    
    # ---- assemble info sections ----
    general_info = html.Div([
        html.B(
            f"Selected item: {main_label}",
            style={"display": "block", "marginTop": "10px", "marginBottom": "10px"},
        ),
        metadata_section,
    ])

    return f"Dependency Graph for {main_node[1]}", general_info

@app.callback(
    Output("gv", "selected"),
    Input("btn-clear-selection", "n_clicks"),
    Input("dot-store", "data"),
)
def clear_selected_node(*_):
    """Reset selected node when file changes or user clears."""
    if not ctx.triggered:
        raise PreventUpdate
    
    return None

@app.callback(
    Output("gv", "dot_source"),
    Output("selected-element", "children"),
    Output("selected-element-calc", "children"),
    Input("dot-store", "data"),
    Input("gv", "selected"),
    State("main-node-store", "data"),
    State("attrs-store", "data"),
    State("df-root-store", "data"),
)
def update_graph_and_info(dot_source, selected, main_node, node_attrs, df_root):
    """Render DOT graph + info: highlight path and show metadata, dependency chain."""
    if not dot_source or not main_node or not ctx.triggered:
        msg_none = html.Div(html.I(MESSAGE_NO_DATA), style={"marginTop": "10px"})
        msg_calc = html.Div(html.I(MESSAGE_NO_DATA), style={"marginTop": "10px"})
        return dot_source, msg_none, msg_calc

    trigger = ctx.triggered_id

    # ---- check if no selection or selection cleared ----
    if trigger == "btn-clear-selection" or not selected or not node_attrs:
        msg_none = html.Div(html.I("(no element selected)"), style={"marginTop": "10px"})
        msg_calc = html.Div(html.I("(no calculation path available)"), style={"marginTop": "10px"})
        return dot_source, msg_none, msg_calc
    
    new_dot = dot_source

    # ---- normalize ----
    if isinstance(selected, list) and selected:
        selected = selected[0]
    selected = selected.strip('"')
    main_id, main_label, _ = main_node
    attrs = node_attrs.get(selected, {})
    label_selected = attrs.get("label", selected)

    # ---- parse DOT + compute path ----
    path, direction = None, None
    try:
        graphs = pydot.graph_from_dot_data(dot_source)
        if graphs:
            G = nx.nx_pydot.from_pydot(graphs[0])

            if nx.has_path(G, main_id, selected):
                path = nx.shortest_path(G, source=main_id, target=selected)
                direction = "Downstream"
                direction_label = "Downstream Consumer"
            elif nx.has_path(G, selected, main_id):
                path = nx.shortest_path(G, source=selected, target=main_id)
                direction = "Upstream"
                direction_label = "Upstream Source"
            else:
                path = [selected]
    except Exception:
        pass  # ignore layout/path errors

    # ---- highlight nodes and edges ----
    if path:
        # --- highlight nodes ---
        for node_id in path:
            node_escaped = re.escape(node_id)
            node_pat = rf'("{node_escaped}"\s*\[)(.*?)(\]\s*;)'

            def bump_node_attrs(m):
                before, attrs, after = m.group(1), m.group(2), m.group(3)
                a = attrs
                if re.search(r'\bpenwidth\s*=', a):
                    a = re.sub(r'\bpenwidth\s*=\s*[0-9]+(?:\.[0-9]+)?', 
                               f'penwidth={SELECTED_NODE_PENWIDTH}', a, count=1)
                else:
                    a = a.strip()
                    if a and not a.endswith(','):
                        a += ', '
                    a += f'penwidth={SELECTED_NODE_PENWIDTH}'
                return before + a + after

            new_dot = re.sub(node_pat, bump_node_attrs, new_dot, count=1, flags=re.DOTALL)

        # --- highlight edges along the path ---
        for i in range(len(path) - 1):
            src, tgt = path[i], path[i + 1]
            edge_pat = rf'("{re.escape(src)}"\s*->\s*"{re.escape(tgt)}"\s*\[)(.*?)(\]\s*;)'

            def bump_edge_attrs(m):
                before, attrs, after = m.group(1), m.group(2), m.group(3)
                a = attrs
                if re.search(r'\bpenwidth\s*=', a):
                    a = re.sub(r'\bpenwidth\s*=\s*[0-9]+(?:\.[0-9]+)?', 
                               f'penwidth={SELECTED_EDGE_PENWIDTH}', a, count=1)
                else:
                    a = a.strip()
                    if a and not a.endswith(','):
                        a += ', '
                    a += f'penwidth={SELECTED_EDGE_PENWIDTH}'
                    
                return before + a + after

            new_dot = re.sub(edge_pat, bump_edge_attrs, new_dot, count=1, flags=re.DOTALL)

    # ---- metadata from fields.parquet ----
    metadata_section = html.Div("Node information not available.")
    try:
        parquet_path = os.path.join(df_root, "fields.parquet")
        if os.path.exists(parquet_path):
            df = pd.read_parquet(parquet_path)
            row = df.loc[df["source_field_repl_id"] == selected]

            if len(row) == 1:
                rec = row.iloc[0]
                metadata_section = html.Div(
                    [
                        html.B("Field Information", style={"display": "block", "marginBottom": "6px"}),
                        html.Ul(
                            [
                                html.Li([html.B("Data source: "), rec["source_label"]]),
                                html.Li([html.B("Category: "), rec["field_category"]]),
                                html.Li([html.B("Data type: "), rec["field_datatype"]]),
                                html.Li([html.B("Role: "), rec["field_role"]]),
                                html.Li([html.B(f"{direction} Level: "), len(path)-1]),
                            ],
                            style={"marginLeft": "10px"},
                        ),
                    ],
                    style={
                        "marginBottom": "12px",
                        "padding": "8px 10px",
                        "backgroundColor": "#f9f9f9",
                        "borderRadius": "6px",
                        "border": "1px solid #ddd",
                    },
                )
            elif len(row) == 0:
                metadata_section = html.Div(f"No record found for node ID: {selected}")
            else:
                metadata_section = html.Div(f"Multiple records found for node ID: {selected}")
    except Exception as e:
        metadata_section = html.Div(f"Error reading fields.parquet: {e}")

    # ---- dependency & calc path text ----
    path_text = "No direct dependency path found."
    calc_text = None

    if path:
        path_labels = [node_attrs.get(n, {}).get("label", n) for n in path]
        arrow = " → ".join(path_labels)
        path_text = arrow if direction in ("Downstream", "Upstream") else "No direct dependency path."

        calc_chain = []
        for i, node in enumerate(path):
            label = node_attrs.get(node, {}).get("label", node)
            tooltip = node_attrs.get(node, {}).get("tooltip", "").strip()
            tooltip_display = tooltip if tooltip else "(no calculation)"
            calc_chain.append(
                html.Div([
                    html.B(f"▶ Step {i+1}: {label}"),
                    html.Pre(
                        tooltip_display,
                        style={
                            "whiteSpace": "pre-wrap",
                            "margin": "4px 0 12px 12px",
                            "fontFamily": "monospace",
                        },
                    ),
                ])
            )

        if calc_chain:
            calc_text = html.Div(calc_chain, style={"marginTop": "6px"})

    # ---- assemble info sections ----
    general_info = html.Div([
        html.B(
            f"{direction_label}: {label_selected}",
            style={"display": "block", "marginTop": "10px", "marginBottom": "10px"},
        ),
        metadata_section,
        html.Hr(),
        html.B(f"Shortest path relative to {main_label}:"),
        html.Div(path_text, style={"marginTop": "4px"}),
    ])

    calc_section = calc_text if calc_text else html.Div("(no calculation path available)")

    return new_dot, general_info, calc_section

@app.callback(
    Output("kpi-fields", "children"),
    Output("kpi-fields-unused", "children"),
    Output("kpi-calcs", "children"),
    Output("kpi-calcs-lod", "children"),
    # Output("kpi-params", "children"),
    # Output("kpi-params-unused", "children"),
    Output("kpi-dep", "children"),
    Output("kpi-dep-range", "children"),
    Output("kpi-sheets", "children"),
    Output("kpi-sheets-dep", "children"),
    Input("btn-download", "disabled"), # only used as trigger
    State("df-root-store", "data"),
)
def update_kpi(disabled, df_root):
    if not df_root or disabled:
        raise PreventUpdate
    
    try:
        parquet_path_field = os.path.join(df_root, "fields.parquet")
        parquet_path_sheet = os.path.join(df_root, "dependencies.parquet")
        df = pd.read_parquet(parquet_path_field)
        df_dep = pd.read_parquet(parquet_path_sheet)

        # field stats
        fields = (df["field_category"] == "Field").sum()
        fields_unused = ((df["field_category"] == "Field") \
                                    & (df["n_worksheet_dependencies"] == 0)).sum()
        calculated_fields = df["field_category"].isin(
            ["Calculated Field", "Calculated Field (LOD)"]
        ).sum()
        calculated_fields_lod = (df["field_category"] == \
                                 "Calculated Field (LOD)").sum()

        # dependency stats
        avg_dependencies, min_dependencies, max_dependencies = (
            df_dep.loc[df_dep["dependency_category"] != "Sheet"]
            .groupby("source_field_repl_id")
            .size()
            .agg(["mean", "min", "max"])
            .round(2)
        )        

        # sheet stats
        sheets = df_dep.loc[df_dep["dependency_category"] == "Sheet",
                             "dependency_to"].nunique()
        avg_elements_per_sheet = (
            df_dep.loc[df_dep["dependency_category"] == "Sheet"]
            .groupby("dependency_to")["dependency_from"]
            .nunique()
            .mean()
        )

    except Exception as e:
        print(f"Error processing parquet files: {e}")
        raise PreventUpdate
    
    return (
        fields,
        f"of which {fields_unused} unused in sheets",
        calculated_fields,
        f"of which {calculated_fields_lod} LODs",
        # parameters,
        # f"of which {parameters_unused} unused in sheets",
        avg_dependencies,
        f"ranging between {min_dependencies:.0f} and {max_dependencies:.0f}",
        sheets,
        f"connected to {avg_elements_per_sheet:.0f} fields & parameters on average"
    )

@app.callback(
    Output("calc-modal", "is_open"),
    Output("calc-modal-content", "children"),
    Input("open-calc-modal", "n_clicks"),
    Input("close-calc-modal", "n_clicks"),
    State("calc-modal", "is_open"),
    State("selected-element-calc", "children"),
)
def toggle_calc_modal(open_click, close_click, is_open, calc_content):

    if not ctx.triggered:
        raise PreventUpdate

    trigger = ctx.triggered_id

    if trigger == "open-calc-modal" and calc_content:
        # Open modal and show the current calc tab content
        return True, calc_content

    # Close button or no content
    return False, None

if __name__ == '__main__':
    app.run(debug=DEBUG_MODE)
