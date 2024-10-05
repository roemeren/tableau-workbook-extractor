Introduction
============

Description
^^^^^^^^^^^

This tool automatically extracts fields and their dependencies from local 
Tableau workbooks.

It uses the `Tableau Document API <https://tableau.github.io/document-api-python>`_ 
for the extraction of field attributes and the 
`Graphviz <https://graphviz.org>`_ software and its `pydot <https://pypi.org/project/pydot>`_ 
interface for the visualization of field dependencies.

It can be run locally as a Windows executable, or via a web interface.

.. note::
   You do not need to have Tableau installed to use the tool and/or analyze its 
   outputs. However, having Tableau installed may help you verify the results 
   more effectively.

It consists of the following 3 steps:

1. The user selects a local Tableau workbook (in `.twb` or `.twbx` format) to be 
   analyzed.
2. The tool processes the workbook and the different fields and their dependencies.
3. Outputs are generated and, depending on how the tool is run, are saved 
   locally or offered as a zipped download.

The output has the following structure:

* The folder `Fields` containing a single Excel file that has 2 sheets 
  `fields` and `dependencies`, with resp. the field metadata and the field 
  dependencies (on other fields and/or sheets).
* A folder `Graphs` containing 1 subfolder for each data source inside 
  the workbook, as well as a folder `Parameters`. Inside each of these
  subfolders, a set of 1 PNG and 1 SVG file is saved for each field that has 
  at least 1 forward or backward dependency to another field or sheet.

Use Cases
^^^^^^^^^

The tool could be used for the following reasons:

- Get a full overview of **how a field is calculated** (starting from 
  data source fields) and how (much) it is used in sheets and/or other calculations

- Get an overview of **unused fields and calculations**. These could be 
  removed from the workbook or data source if needed to improve 
  performance or to keep extract sizes as low as possible

- Get an overview of the **overall complexity** of the 
  dashboard and check whether or not it is needed to 
  simplify fields by pruning dependencies and fields

- Automate part of the **documentation** process of a dashboard

Limitations
^^^^^^^^^^^

Below a list of items that *cannot* be extracted from this tool:

- **Role of a field** in sheets: there is no indication if a field in 
  a particular sheet is used as a dimension, measure, filter, tooltip, etc.
- **Direct or indirect dependency** in sheets: there is no indication if 
  a field in a particular sheet is used *directly* in the sheet or *indirectly* 
  through a calculated field that depends on the field
- **Parameter dependencies**: during loading/opening of the workbook some 
  parameters may be initialized by a calculated field in the workbook (e.g. most 
  recent date). These (backward) dependencies are not captured.
- **Full data source dependencies**: fields from a data source are analyzed 
  from the point of view of a particular dashboard. The used data source 
  itself may contain calculated fields that depend on hidden fields that are 
  not available in the workbook. These 'hidden dependencies' from the data 
  source therefore will not be captured. This may be overcome by running the 
  tool separately for the technical workbook that defines the data source.
- **Dashboard dependencies**: the currently used version of the API 
  doesn't contain links between dashboards and sheets (only a `dashboards` 
  workbook property that returns a list of dashboard names). Because of this 
  it is not possible to (for example) know which data sources and/or fields 
  are used in a specific dashboard.
- **Dashboard actions** processing: dashboard actions depend on fields as well 
  as sheets, and have various other properties (source and target fields/sheets, 
  action type, etc.) that are currently not exposed in the Document API.
- **Filter** properties: filters in visualizations are related to fields but 
  have various other properties (filter expression, filter scope, etc.)

These items are partially related to the limitations in the current version 
of the Tableau Document API.
