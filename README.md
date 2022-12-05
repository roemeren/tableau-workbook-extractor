# tableau-workbook-extractor

Python script to automatically analyze (possibly complex Tableau) workbooks.

## Description

The script prompts the user to select a locally saved Tableau workbook (in `.twb` or `.twbx` format), after which 2 outputs are created:

1. An Excel file `<workbook_name>.xlsx` containing a table of field information (sheet `fields`) and a table of field dependencies (sheet `dependencies`). The tables are a cleaned and processed version of information extracted from the [Tableau Document API](https://tableau.github.io/document-api-python/)
2. A PNG `<source_name>-<field_name>.xlsx` for each field that has at least 1 dependency to ('forward' dependency) or from ('backward' dependency) another field or sheet, containing a graph of all the field's dependencies with different colors and shapes indicating the dependency types (parameter, data source field or calculated field). The graphs are generated using [Pydot](https://pypi.org/project/pydot/), a Python interfact to [Graphviz](https://graphviz.org/)

These files could be useful for the following reasons:

- Get a full overview of **how a field is calculated** (starting from the data source) and how (much) it is used in sheets and/or other calculations
- Get an overview of **unused fields and calculations** that could be removed from the Tableau if needed to improve performance or to keep extract sizes as low as possible
- Get an overview of **overall complexity** of the dashboard and check whether or not it is needed to simplify fields by pruning dependencies
- Automate the **documentation** process of the dashboard

## How to run the script

### Step 1: Install Graphviz

For exporting the graphs as images the `Graphviz` software is used and should be installed from here: https://graphviz.org/download/. 

For Windows it is important to add the Graphviz `bin` subdirectory to the 
`Path` environment variable (otherwise the `dot` command used by `pydot` won't be recognized).

### Step 2: Run the tool

#### Method 1: Run Executable (Windows Only)

The tool can be run on Windows by double-clicking on the executable `tableau-workbook-extractor.exe` inside the `dist` subfolder, which will run a packaged version of the main script `tableau-workbook-extractor.py`.

Notes: 

- The tool has been created using version 6.0.2. on Windows (graphviz-6.0.2 64-bit EXE installer). Installing more recent versions may be blocked by Microsoft Defender SmartScreen.
- separate Linux/MacOS versions can be created by running PyInstaller resp. on Linux or MacOS.

#### Method 2: Run Python script (using Anaconda)

1. **Clone the GitLab repo** by opening a terminal and executing the following commands:

    ```
    cd C:\path\to\root\
    git clone https://git.bdbelux.be/remerencia/tableau-workbook-extractor.git
    ```

2. **Replicate the environment** by creating a new Python 3.8 environment and installing the package versions listed in `requirements.txt`. In Anaconda:

    a. Open a new terminal in Anaconda for example in the `base` environment
    
    b. Create a new conda environment (for example `myenv`) using the following commands:

    ```
    conda create --name myenv python=3.8
    conda activate myenv
    cd C:\path\to\root\myrepo
    pip install -r requirements.txt
    ```

## Sources

- [Document API Python documentation](https://tableau.github.io/document-api-python/): describes how workbook and field information can be extracted
- [Pydot repository](https://github.com/pydot/pydot): methods and attributes in `pydot` package used for visualizing graphs
- [Graphviz documentation](https://graphviz.org/docs/nodes/): node and graph attributes
- [PyInstaller documentation](https://graphviz.org/docs/nodes/): bundling a Python application and all its dependencies into a single packages (i.e. Windows executable)

## Usage

*To be included: example with simple workbook & visuals of outputs*

## Known issues

- **Not all dependencies are captured**: 
    - it is possible that flagged fields/parameters are still used/useful in the workbook because they are for example used in a dashboard URL action. Deleting it in Tableau won't raise any warnings (surprisingly) but the field removal may cause issues.
    - if fields are based on hidden fields from a data source these dependencies won't be captured and/or shown in the outputs
- **Not all field captions are captured**: some data source field captions (among other attributes) are missing when using the Tableau Document API while these captions can be located in the workbook's raw XML (within the `<metadata-record>`'s `<caption>` tag). It appears to be related to hidden fields (maybe previously unhidden?) in the data source.
- **Not all fields are assigned to the correct data source**: for unknown reasons
some (copies of) fields are assigned to a data source it doesn't belong to. This 
may also be related to open issues in the Document API.

## Roadmap

Some possible extensions:

- Batch processing of a set or folder of workbooks at once
- Code refactoring; the current pandas implementation may not be the fastest/shortest
- Follow up the development of the Documentation API. Currently not all extracted information is 100% correct or directly usable which is why additional processiong is needed. The API may improve in the future, removing the need of some of the post-processing.
- Include additional fields and information in the output Excel file
- Improve the quality/readability of the output graphs
- Test more workbooks to find additional edge cases e.g. field names with special characters that aren't processed correctly

## Contributing

Feel free to contribute or improve this tool! See the 'Roadmap' section for possible ideas and the 'Sources' section for background documentation on some of the external libraries that are used.
State if you are open to contributions and what your requirements are for accepting them.

## Project status

Currently information can be extracted from a single workbook and should be accurate. There are however still some exceptional cases that may be improved further, possibly after future API update checks.