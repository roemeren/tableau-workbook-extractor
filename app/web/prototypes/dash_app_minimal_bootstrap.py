import os
import re
from dash import Dash, html, dcc, Output, Input, State, no_update
import dash_bootstrap_components as dbc
import dash_interactive_graphviz

# -------------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------------
BASE_DIR = "folder_name/Graphs"  # relative to assets/
ASSETS_PATH = os.path.join("assets", BASE_DIR)

# -------------------------------------------------------------------
# HELPER FUNCTIONS
# -------------------------------------------------------------------
def list_subfolders(base_dir):
    """Return all subfolders inside assets/<base_dir>."""
    folder_path = os.path.join("assets", base_dir)
    if not os.path.exists(folder_path):
        return []
    return [
        f for f in os.listdir(folder_path)
        if os.path.isdir(os.path.join(folder_path, f))
    ]

def list_dot_files(subfolder):
    """Return all .dot filenames (without extension) inside a subfolder."""
    subfolder_path = os.path.join("assets", BASE_DIR, subfolder)
    if not os.path.exists(subfolder_path):
        return []
    return [
        os.path.splitext(f)[0]
        for f in os.listdir(subfolder_path)
        if f.endswith(".dot")
    ]

def read_dot_file(subfolder, filename):
    """Return the raw DOT source for the given folder + file."""
    path = os.path.join("assets", BASE_DIR, subfolder, f"{filename}.dot")
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

# -------------------------------------------------------------------
# APP INITIALIZATION
# -------------------------------------------------------------------
app = Dash(__name__, external_stylesheets=[dbc.themes.ZEPHYR])
app.title = "Graphviz Viewer (Bootstrap)"

# -------------------------------------------------------------------
# LAYOUT COMPONENTS
# -------------------------------------------------------------------

# ---- Left Panel ---------------------------------------------------
left_panel = dbc.Col(
    [
        html.H5("Actions", className="mb-3 text-center"),

        # Upload button
        dbc.Button("Upload", id="btn-upload", color="primary", className="w-100 mb-2"),

        # Process button
        dbc.Button("Process", id="btn-process", color="secondary", className="w-100 mb-3"),

        # Progress bar + message
        html.Div(
            [
                dbc.Progress(id="progress-bar", value=0, striped=True, animated=True, style={"height": "20px"}),
                html.Div(id="progress-message", className="text-muted small mt-2", children="No process running."),
            ],
            className="mb-3",
        ),

        # Download button
        dbc.Button("Download Results", id="btn-download", color="success", className="w-100 mb-2"),
    ],
    width=3,
    className="p-3 bg-light border-end vh-100",
)

# ---- Right Panel --------------------------------------------------
right_panel = dbc.Col(
    [
        # Header row
        dbc.Row(
            dbc.Col(
                html.H3("Interactive Graphviz Viewer", className="my-3 text-center"),
                width=12,
            ),
        ),

        # Control row (folder/file/engine)
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Folder", className="fw-bold"),
                        dcc.Dropdown(
                            id="folder-dropdown",
                            options=[{"label": f, "value": f} for f in list_subfolders(BASE_DIR)],
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

        # Visualization + Node Info side by side
        dbc.Row(
            [
                # Graph container
                dbc.Col(
                    [
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.H5("Network Visualization", className="card-title"),
                                    dash_interactive_graphviz.DashInteractiveGraphviz(
                                        id="gv",
                                        style={"height": "70vh", "width": "99%"},
                                    ),
                                ]
                            ),
                            className="shadow-sm",
                        )
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
    width=9,
    className="p-0",
)

# ---- Full page layout ---------------------------------------------
app.layout = dbc.Container(
    dbc.Row([left_panel, right_panel]),
    fluid=True,
    className="gx-0",  # remove default Bootstrap gutter spacing
)

# -------------------------------------------------------------------
# CALLBACKS
# -------------------------------------------------------------------

# (1) Folder -> update file dropdown
@app.callback(
    Output("file-dropdown", "options"),
    Output("file-dropdown", "value"),
    Input("folder-dropdown", "value"),
)
def update_file_dropdown(selected_folder):
    """Update .dot file list based on selected folder."""
    if not selected_folder:
        return [], None
    files = list_dot_files(selected_folder)
    if not files:
        return [], None
    return [{"label": f, "value": f} for f in files], files[0]

# (2) File or engine change -> render graph
@app.callback(
    Output("gv", "dot_source"),
    Output("gv", "engine"),
    Input("file-dropdown", "value"),
    Input("engine", "value"),
    State("folder-dropdown", "value"),
)
def update_graph(selected_file, engine, selected_folder):
    """Load and render the selected .dot file."""
    if not selected_file or not selected_folder:
        return no_update, no_update

    path = os.path.join("assets", BASE_DIR, selected_folder, f"{selected_file}.dot")
    if not os.path.exists(path):
        return no_update, no_update

    with open(path, "r", encoding="utf-8") as f:
        dot_text = f.read()

    return dot_text, engine

# (3) When a node is clicked: parse and display its attributes
@app.callback(
    Output("selected-store", "data"),
    Output("selected-element", "children"),
    Input("gv", "selected"),
    State("file-dropdown", "value"),
    State("folder-dropdown", "value"),
)
def show_selected_attributes(selected, selected_file, selected_folder):
    """
    When a user clicks on a node, extract its attributes from the raw DOT source.

    Returns:
        - selected-store.data: a dict {"name": node_name, "attributes": {...}}
        - selected-element.children: human-readable HTML summary
    """
    # Handle missing selection
    if not selected or not selected_file or not selected_folder:
        return {"name": None, "attributes": {}}, "Selected element: none"

    # Graphviz sometimes returns list for multiple selections
    if isinstance(selected, list) and selected:
        selected = selected[0]

    # Load raw .dot text for this graph
    dot_source = read_dot_file(selected_folder, selected_file)
    if not dot_source:
        return {"name": selected, "attributes": {}}, f"Selected element: {selected}"

    # Escape node name for regex safety (handles [ and ])
    node_escaped = re.escape(selected.strip('"'))

    # Find full node definition line
    pattern = rf'"{node_escaped}"\s*\[(.*?)\];'
    match = re.search(pattern, dot_source, re.DOTALL)
    if not match:
        return {"name": selected, "attributes": {}}, f"Selected element: {selected}"

    attrs_str = match.group(1)

    # Extract key=value pairs, supporting quoted values, escaped quotes, newlines
    attr_pattern = r'(\w+)=("([^"\\]|\\.)*"|\S+)'
    attrs = {}
    for m in re.finditer(attr_pattern, attrs_str, re.DOTALL):
        key = m.group(1)
        val = m.group(2)
        cleaned_val = val.strip('"').replace('\\"', '"')
        cleaned_val = cleaned_val.replace("\\r\\n", "\n").replace("\\n", "\n")
        attrs[key] = cleaned_val

    # Build HTML representation with preserved line breaks for tooltips
    items = []
    for k, v in attrs.items():
        if k == "tooltip":
            items.append(
                html.Li(
                    [
                        html.B("tooltip: "),
                        html.Pre(v, style={"whiteSpace": "pre-wrap", "margin": "0"}),
                    ]
                )
            )
        else:
            items.append(html.Li(f"{k}: {v}"))

    return (
        {"name": selected, "attributes": attrs},
        html.Div(
            [
                html.B(f"Selected element: {selected}"),
                html.Ul(items),
            ]
        ),
    )

# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
