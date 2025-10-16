"""
Interactive Graphviz Viewer (Dash + dash_interactive_graphviz)
--------------------------------------------------------------

Displays .dot files (Graphviz source) stored under `assets/folder_name/Graphs/`
in an interactive Dash web app.

Features:
- Dropdowns to select subfolder and .dot file
- Engine selector (dot / neato / etc.)
- Interactive, zoomable, pannable Graphviz rendering
- Click any node to inspect its attributes (fillcolor, label, shape, style, tooltip)
- Tooltip text displayed with preserved line breaks
- Stores parsed attributes in dcc.Store for later use
"""

import os
import re
from dash import Dash, dcc, html, Output, Input, State, no_update
import dash_interactive_graphviz

# -------------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------------
# Relative to your Dash assets folder. Structure:
# assets/
#   folder_name/
#     Graphs/
#       SubfolderA/
#         file1.dot
#         file2.dot
#       SubfolderB/
#         ...
BASE_DIR = "folder_name/Graphs"

# -------------------------------------------------------------------
# HELPER FUNCTIONS
# -------------------------------------------------------------------
def list_subfolders(base_dir):
    """Return all subfolders inside assets/<base_dir>."""
    return [
        f for f in os.listdir(os.path.join("assets", base_dir))
        if os.path.isdir(os.path.join("assets", base_dir, f))
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
    """Read and return the raw DOT text for a given subfolder/file."""
    path = os.path.join("assets", BASE_DIR, subfolder, f"{filename}.dot")
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

# -------------------------------------------------------------------
# DASH APP SETUP
# -------------------------------------------------------------------
app = Dash(__name__)

app.layout = html.Div(
    [
        # ==============================================================
        # Top controls: folder / file / engine
        # ==============================================================
        html.Div(
            [
                html.H3("Interactive Graphviz Viewer", style={"marginBottom": "5px"}),

                # Dropdown row (Folder, File, Engine)
                html.Div(
                    [
                        # Folder selection
                        html.Div(
                            [
                                html.Label("Folder"),
                                dcc.Dropdown(
                                    id="folder-dropdown",
                                    options=[{"label": f, "value": f} for f in list_subfolders(BASE_DIR)],
                                    placeholder="Select a folder",
                                    clearable=False,
                                    style={"width": "250px"},
                                ),
                            ],
                            style={"marginRight": "15px"},
                        ),
                        # File selection
                        html.Div(
                            [
                                html.Label(".dot File"),
                                dcc.Dropdown(
                                    id="file-dropdown",
                                    placeholder="Select a file",
                                    style={"width": "250px"},
                                ),
                            ],
                            style={"marginRight": "15px"},
                        ),
                        # Graphviz layout engine
                        html.Div(
                            [
                                html.Label("Engine"),
                                dcc.Dropdown(
                                    id="engine",
                                    value="dot",
                                    options=[
                                        {"label": e, "value": e}
                                        for e in [
                                            "dot", "neato", "fdp", "sfdp",
                                            "twopi", "circo", "osage", "patchwork"
                                        ]
                                    ],
                                    clearable=False,
                                    style={"width": "150px"},
                                ),
                            ]
                        ),
                    ],
                    style={"display": "flex", "alignItems": "flex-end"},
                ),
            ],
            style={
                "padding": "10px 20px",
                "backgroundColor": "#f8f9fa",
                "borderBottom": "1px solid #ccc",
            },
        ),

        # ==============================================================
        # Graphviz display area
        # ==============================================================
        html.Div(
            dash_interactive_graphviz.DashInteractiveGraphviz(id="gv"),
            style={
                "flexGrow": 1,
                "position": "relative",
                "height": "76vh",  # big viewport for graph
                "borderBottom": "1px solid #ddd",
                "backgroundColor": "white",
            },
        ),

        # ==============================================================
        # Bottom panel: selection info + raw .dot text
        # ==============================================================
        dcc.Store(id="selected-store"),  # holds selected node data for later use
        html.Div(
            [
                html.Div(
                    id="selected-element",
                    style={"marginBottom": "8px", "fontWeight": "bold"},
                ),
                dcc.Textarea(
                    id="dot-source",
                    style={
                        "width": "100%",
                        "height": "14vh",
                        "fontFamily": "monospace",
                        "fontSize": "12px",
                        "whiteSpace": "pre",
                        "overflowY": "scroll",
                    },
                    readOnly=True,
                ),
            ],
            style={"padding": "8px 15px", "backgroundColor": "#f9f9f9"},
        ),
    ],
    style={"display": "flex", "flexDirection": "column", "height": "100vh"},
)

# -------------------------------------------------------------------
# CALLBACKS
# -------------------------------------------------------------------

# -- (1) When folder changes: update available files -----------------
@app.callback(
    Output("file-dropdown", "options"),
    Output("file-dropdown", "value"),
    Input("folder-dropdown", "value"),
)
def update_file_dropdown(selected_folder):
    """List .dot files in the selected subfolder and auto-select the first one."""
    if not selected_folder:
        return [], None
    files = list_dot_files(selected_folder)
    if not files:
        return [], None
    return [{"label": f, "value": f} for f in files], files[0]


# -- (2) When file or engine changes: update the graph viewer --------
@app.callback(
    Output("dot-source", "value"),
    Output("gv", "dot_source"),
    Output("gv", "engine"),
    Input("file-dropdown", "value"),
    Input("engine", "value"),
    State("folder-dropdown", "value"),
)
def update_graph(selected_file, engine, selected_folder):
    """
    Load the selected .dot file, display its raw content in the textarea,
    and render it in the interactive Graphviz viewer.
    """
    if not selected_file or not selected_folder:
        return "", no_update, no_update

    dot_text = read_dot_file(selected_folder, selected_file)
    return dot_text, dot_text, engine


# -- (3) When a node is clicked: parse and display its attributes ----
@app.callback(
    Output("selected-store", "data"),
    Output("selected-element", "children"),
    Input("gv", "selected"),
    State("dot-source", "value"),
)
def show_selected_attributes(selected, dot_source):
    """
    When a user clicks on a node, extract its attributes from the raw DOT source.

    Returns:
        - selected-store.data: a dict {"name": node_name, "attributes": {...}}
        - selected-element.children: human-readable HTML summary
    """
    # Graceful defaults when nothing selected yet
    if not selected or not dot_source:
        return {"name": None, "attributes": {}}, "Selected element: none"

    # Graphviz sometimes returns list for multiple selections
    if isinstance(selected, list) and selected:
        selected = selected[0]

    # Escape node name for regex safety (handles [ and ])
    node_escaped = re.escape(selected.strip('"'))

    # Find the full node definition line, e.g.
    # "[node1]" [fillcolor=orange, label="My Label", tooltip="text\r\nline2"];
    pattern = rf'"{node_escaped}"\s*\[(.*?)\];'
    match = re.search(pattern, dot_source, re.DOTALL)
    if not match:
        return {"name": selected, "attributes": {}}, f"Selected element: {selected}"

    attrs_str = match.group(1)

    # --------------------------------------------------------------
    # Extract key=value pairs, supporting quoted values, escaped quotes,
    # and newlines (e.g. tooltip="some \"quoted\" text\r\nline2")
    # --------------------------------------------------------------
    attr_pattern = r'(\w+)=("([^"\\]|\\.)*"|\S+)'
    attrs = {}
    for m in re.finditer(attr_pattern, attrs_str, re.DOTALL):
        key = m.group(1)
        val = m.group(2)
        # Clean up: remove outer quotes, unescape internal quotes, fix newlines
        cleaned_val = val.strip('"').replace('\\"', '"')
        cleaned_val = cleaned_val.replace("\\r\\n", "\n").replace("\\n", "\n")
        attrs[key] = cleaned_val

    # --------------------------------------------------------------
    # Build HTML representation
    # tooltip is rendered in <pre> so line breaks are preserved
    # --------------------------------------------------------------
    items = []
    for k, v in attrs.items():
        if k == "tooltip":
            items.append(
                html.Li(
                    [
                        html.B("tooltip: "),
                        html.Pre(v, style={"whiteSpace": "pre-wrap", "margin": "0"})
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
                html.Ul(items)
            ]
        ),
    )

# -------------------------------------------------------------------
# RUN SERVER
# -------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
