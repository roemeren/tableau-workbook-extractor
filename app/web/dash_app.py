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
from shared.common import progress_data

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
                    # path to the graphs folder and currently selected file
                    dcc.Store(id="dot-root-store"),
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

                    # Control row (folder/file/engine)
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Label("Folder", className="fw-bold"),
                                    dcc.Dropdown(
                                        id="folder-dropdown",
                                        placeholder="Select folder",
                                        clearable=False,
                                    ),
                                ],
                                width=4,
                            ),
                            dbc.Col(
                                [
                                    html.Label(".dot File", className="fw-bold"),
                                    dcc.Dropdown(
                                        id="file-dropdown",
                                        placeholder="Select file",
                                    ),
                                ],
                                width=4,
                            ),
                            dbc.Col(
                                [
                                    html.Label("Engine", className="fw-bold"),
                                    dcc.Dropdown(
                                        id="engine",
                                        value="dot",
                                        options=[
                                            {"label": e, "value": e}
                                            for e in ["dot", "neato", "fdp", "sfdp", "twopi", "circo", "osage", "patchwork"]
                                        ],
                                        clearable=False,
                                    ),
                                ],
                                width=4,
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
                                        "Network Visualization",
                                        id = "network-title",  
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
                                width=8,
                            ),

                            # Node info panel
                            dbc.Col(
                                [
                                    dcc.Store(id="selected-store"),
                                    dbc.Card(
                                        dbc.CardBody(
                                            [
                                                html.H5("Node Info", className="card-title"),
                                                html.Div(id="selected-element", className="small"),
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
    Output("dot-root-store", "data"),
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
    out_folder = progress_data.get("foldername")
    # Build href only if out_file exists
    href = out_file and os.path.join(OUTPUT_FOLDER_URL, out_file)
    graphs_folder = out_folder and os.path.join(out_folder, "Graphs")
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
        graphs_folder,
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
    folders.sort(key=lambda x: (x in ["Sheets", "Parameters"], x.lower()))

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
    options = [{"label": f, "value": f} for f in files]

    # Auto-select first file if available
    return options, files[0] if files else None

# File -> load and parse .dot source
@app.callback(
    Output("dot-store", "data"),
    Output("attrs-store", "data"),
    Output("main-node-store", "data"),
    Input("file-dropdown", "value"),
    State("dot-root-store", "data"),
    State("folder-dropdown", "value"),
)
def load_dot_source(selected_file, base_dir, selected_folder):
    """Load the selected .dot file, parse its node attributes, and identify the main node."""
    if not selected_file or not selected_folder:
        raise PreventUpdate

    path = os.path.join(base_dir, selected_folder, f"{selected_file}.dot")
    if not os.path.exists(path):
        raise PreventUpdate

    with open(path, "r", encoding="utf-8") as f:
        dot_text = f.read()

    # --- robust, line-anchored parse of node attributes ---
    # - Only match lines that START with a quoted node name
    # - Ignore edge lines and graph-level attributes
    node_pattern = r'^\s*"([^"]+)"\s*\[(.*?)\]\s*;'
    attr_pattern = r'(\w+)=("([^"\\]|\\.)*"|[^,\]]+)'  # value is quoted or runs until comma or ']'

    node_attrs = {}
    main_node = None

    for node_match in re.finditer(node_pattern, dot_text, re.MULTILINE | re.DOTALL):
        node_name = node_match.group(1)
        attrs_str = node_match.group(2)

        attrs = {}
        for m in re.finditer(attr_pattern, attrs_str):
            key = m.group(1)
            val = m.group(2).strip()

            # normalize + clean value
            if len(val) >= 2 and val[0] == '"' and val[-1] == '"':
                # strip outer quotes and unescape
                val = val[1:-1].replace('\\"', '"')
                val = val.replace("\\r\\n", "\n").replace("\\n", "\n")
            else:
                # unquoted token; trim any stray whitespace
                val = val.strip()

            attrs[key] = val

        node_attrs[node_name] = attrs

        # detect the "main" node (DOT uses 'fillcolor', not 'fill_color')
        fill = (attrs.get("fillcolor") or attrs.get("fill_color") or "").lower()
        if fill == "lightblue" and main_node is None:
            main_node = attrs.get("label", node_name)

    return dot_text, node_attrs, main_node


@app.callback(
    Output("network-title", "children"),
    Input("main-node-store", "data"),
)
def update_network_title(main_node_name):
    if not main_node_name:
        return "Network Visualization"
    return f"Network Visualization for {main_node_name}"

@app.callback(
    Output("gv", "dot_source"),
    Output("gv", "engine"),
    Input("dot-store", "data"),
    Input("engine", "value"),
    Input("gv", "selected"),
    prevent_initial_call=True,
)
def update_graph(dot_source, engine, selected):
    """Render DOT; if a node is selected, make it visually bigger and bold."""
    if not dot_source:
        raise PreventUpdate

    new_dot = dot_source

    if selected:
        if isinstance(selected, list) and selected:
            selected = selected[0]

        node_escaped = re.escape(selected.strip('"'))
        node_pat = rf'("{node_escaped}"\s*\[)(.*?)(\]\s*;)'

        def bump_attrs(m):
            before, attrs, after = m.group(1), m.group(2), m.group(3)
            a = attrs

            # --- bump fontsize ---
            fs = re.search(r'fontsize\s*=\s*([0-9]+(?:\.[0-9]+)?)', a)
            if fs:
                curr = float(fs.group(1))
                a = re.sub(r'fontsize\s*=\s*[0-9]+(?:\.[0-9]+)?', f'fontsize={curr + 4:g}', a, count=1)
            else:
                a = a.strip()
                if a and not a.endswith(','):
                    a += ', '
                a += 'fontsize=18'

            # --- bump penwidth ---
            if re.search(r'\bpenwidth\s*=', a):
                a = re.sub(r'\bpenwidth\s*=\s*([0-9]+(?:\.[0-9]+)?)', 'penwidth=3', a, count=1)
            else:
                a = a.strip()
                if a and not a.endswith(','):
                    a += ', '
                a += 'penwidth=3'

            # --- make font bold (switch to bold variant if available) ---
            if re.search(r'\bfontname\s*=', a):
                a = re.sub(
                    r'\bfontname\s*=\s*"?(.*?)"?\b',
                    lambda m: f'fontname="{m.group(1).replace("-Bold", "")}-Bold"',
                    a,
                    count=1,
                )
            else:
                a = a.strip()
                if a and not a.endswith(','):
                    a += ', '
                a += 'fontname="Helvetica-Bold"'

            return before + a + after

        new_dot = re.sub(node_pat, bump_attrs, new_dot, count=1, flags=re.DOTALL)

    return new_dot, engine

# When a node is clicked: parse and display its attributes
@app.callback(
    Output("selected-store", "data"),
    Output("selected-element", "children"),
    Input("gv", "selected"),
    State("attrs-store", "data"),
)
def show_selected_attributes(selected, node_attrs):
    """
    When a user clicks on a node, retrieve its attributes from the stored data.

    Returns:
        - selected-store.data: a dict {"name": node_name, "attributes": {...}}
        - selected-element.children: human-readable HTML summary
    """
    if not selected or not node_attrs:
        return {"name": None, "attributes": {}}, "Selected element: none"

    if isinstance(selected, list) and selected:
        selected = selected[0]

    attrs = node_attrs.get(selected.strip('"'), {})

    items = []
    for k, v in attrs.items():
        if k == "tooltip":
            items.append(
                html.Li([
                    html.B("tooltip: "),
                    html.Pre(v, style={"whiteSpace": "pre-wrap", "margin": "0"}),
                ])
            )
        else:
            items.append(html.Li(f"{k}: {v}"))

    return (
        {"name": selected, "attributes": attrs},
        html.Div([
            html.B(f"Selected element: {selected}"),
            html.Ul(items),
        ]),
    )


if __name__ == '__main__':
    app.run(debug=DEBUG_MODE)
