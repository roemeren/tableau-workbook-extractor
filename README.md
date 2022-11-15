# tableau-workbook-extractor

Python script to automatically analyze (possibly complex Tableau) workbooks.

## Getting started

### Cloning the repo

Open a terminal and execute the following commands:

```
cd C:\path\to\root\
git clone https://git.bdbelux.be/remerencia/tableau-workbook-extractor.git
```

### Replicating the environment

To be sure that the code will work correctly a `requirements.txt` file has been included.

In case Anaconda has been installed the following commands can be executed to replicate the environment:

1. Open Anaconda and open a terminal for example in the `base` environment
2. Create a new conda environment (for example `myenv`) using the following commands:
```
conda create --name myenv python=3.10
conda activate myenv
cd C:\path\to\root\myrepo
pip install -r requirements.txt
```

### Install Graphviz

For creating graphs the `Graphviz` software is used and should be installed from here: https://graphviz.org/.

## Description

The script prompts the user to select a locally saved Tableau workbook (in `.twb` or `.twbx` format), after which 2 outputs are created:

1. An Excel file `<workbook_name>.xlsx` containing a table of field information (sheet `fields`) and a table of field dependencies (sheet `dependencies`). The tables are a cleaned and processed version of information extracted from the [Tableau Document API](https://tableau.github.io/document-api-python/)
2. A PNG `<source_name>-<field_name>.xlsx` for each field that has at least 1 dependency to ('forward' dependency) or from ('backward' dependency) another field or sheet, containing a graph of all the field's dependencies with different colors and shapes indicating the dependency types (parameter, data source field or calculated field). The graphs are generated using [Pydot](https://pypi.org/project/pydot/), a Python interfact to [Graphviz](https://graphviz.org/)

These files could be useful for the following reasons:

- Get a full overview of **how a field is calculated** (starting from the data source) and how (much) it is used in sheets and/or other calculations
- Get an overview of **unused fields and calculations** that could be removed from the Tableau if needed to improve performance or to keep extract sizes as low as possible
- Get an overview of **overall complexity** of the dashboard and check whether or not it is needed to simplify fields by pruning dependencies
- Automate the **documentation** process of the dashboard


## Sources

- [Document API Python documentation](https://tableau.github.io/document-api-python/): describes how workbook and field information can be extracted
- [Pydot repository](https://github.com/pydot/pydot): methods and attributes in `pydot` package used for visualizing graphs
- [Graphviz documentation](https://graphviz.org/docs/nodes/): node and graph attributes
- [Google Python Style Guide](https://github.com/google/styleguide/blob/gh-pages/pyguide.md#38-comments-and-docstrings): information on docstrings

## Usage

*To be included: example with simple workbook & visuals of outputs*

## Known issues

- **Not all dependencies are captured**: it is possible that flagged fields/parameters are still used/useful in the workbook because they are for example used in a dashboard URL action. Deleting it in Tableau won't raise any warnings (surprisingly) but the field removal may cause issues.
- **Not all field captions are captured**: some data source field captions (among other attributes) are missing when using the Tableau Document API while these captions can be located in the workbook's raw XML (within the `<metadata-record>`'s `<caption>` tag). It appears to be related to hidden fields (maybe previously unhidden?) in the data source.
- **Not all fields are assigned to the correct data source**: for unknown reasons
some (copies of) fields are assigned to a data source it doesn't belong to. This 
may also be related to open issues in the Document API.

## Support
Tell people where they can go to for help. It can be any combination of an issue tracker, a chat room, an email address, etc.

## Roadmap
If you have ideas for releases in the future, it is a good idea to list them in the README.

Some possible extensions:

- Batch processing of a set or folder of workbooks at once
- Code refactoring; the current pandas implementation may not be the fastest/shortest
- Follow up the development of the Documentation API. Currently not all extracted information is 100% correct or directly usable which is why additional processiong is needed. The API may improve in the future, removing the need of some of the post-processing.
- Include additional fields and information in the output Excel file
- Improve the quality/readability of the output graphs

## Contributing

Feel free to contribute or improve this tool! See the 'Roadmap' section for possible ideas and the 'Sources' section for background documentation on some of the external libraries that are used.
State if you are open to contributions and what your requirements are for accepting them.

## Project status

Currently information can be extracted from a single workbook and should be accurate. There are however still some exceptional cases that may be improved further, possibly after future API update checks.