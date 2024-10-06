Introduction
============

Description
^^^^^^^^^^^

The Tableau Workbook Extractor is a tool designed to streamline the process 
of analyzing field dependencies in Tableau workbooks. I
nstead of manually tracing through complex calculations and dependencies, 
this tool automates the extraction of fields and their relationships, 
providing a clear, structured overview.

It leverages the `Tableau Document API <https://tableau.github.io/document-api-python>`_ 
to extract field attributes and uses `Graphviz <https://graphviz.org>`_ along 
with `Pydot <https://pypi.org/project/pydot>`_ to visualize field dependencies. 
This makes it easy to identify how fields are calculated and how they are 
interrelated across different sheets and calculations.

The tool can be run locally as a Windows executable or via a web interface. 
Importantly, you don’t need Tableau installed to use the tool or analyze its 
outputs—though having Tableau installed may help verify the results more effectively.

The workflow is simple:

* Select a local Tableau workbook (.twb or .twbx format).
* Process the workbook to analyze fields and dependencies.
* Generate outputs—either saving them locally or as a downloadable zip file.

The output includes:

* A **Fields** folder containing an Excel file with two sheets: 
  fields (with field metadata) and dependencies (showing the relationships 
  between fields and sheets).
* A **Graphs** folder containing subfolders for each data source and a folder 
  for parameters, with PNG and SVG visualizations of field dependencies.

Use Cases
^^^^^^^^^

The Tableau Workbook Extractor can be used for various purposes, such as:

* **Understanding field calculations**: Get a comprehensive view of how fields 
  are calculated and how they are used across different sheets and calculations.
* **Identifying unused fields**: Find fields that aren’t being used in the 
  workbook and consider removing them to improve performance or reduce extract sizes.
* **Assessing workbook complexity**: Gain insight into the overall complexity 
  of a workbook and decide whether it can be simplified by reducing dependencies.
* **Automating documentation**: Simplify the process of documenting workbook 
  structure and field dependencies.

Documentation Overview
^^^^^^^^^^^^^^^^^^^^^^^

For more detailed information about the tool and its features, refer to the following pages in the documentation:

* :doc:`usage`: A guide on the different ways to run the tool, 
  including local options such as a pre-created executable or web app, 
  as well as running a Python script or setting up the executable or 
  the Flask app yourself.
* :doc:`example`: A practical example to demonstrate the tool's capabilities.
* :doc:`deployment`: Notes regarding the deployment of the tool.
* :doc:`scripts_reference`: Detailed information on the scripts included with the tool.
* :doc:`changelog`: A log of updates and changes made to the tool over time.
* :doc:`roadmap`: An overview of possible future features and improvements planned for the tool.

Limitations
^^^^^^^^^^^

While this tool is highly effective, there are some limitations, 
many of which are related to the current capabilities of the Tableau Document API:

* It does not identify the **role of a field** within a sheet (e.g., dimension, measure, filter).
* **Indirect dependencies within sheets** are not captured (e.g., if a field is 
  used indirectly through another calculation).
* **Parameter dependencies that are set calculated fields** during workbook 
  initialization are not tracked.
* **Hidden dependencies** from data sources are not extracted, though this 
  can be addressed by running the tool separately on the technical workbook defining the data source.
* **Dashboard dependencies and actions** are not captured due to limitations 
  in the API.
* **Filter properties** (such as filter expressions and scopes) are not analyzed.
