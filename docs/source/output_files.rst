Output Files
=============

Output Folder Structure
------------------------

The output files are structured as follows:

.. code-block:: text

    <Root Folder>/
    ├── Fields/
    │   └── <Workbook Name>.xlsx
    ├── Graphs/
    │   ├── <Data Source Name 1>
    │   │   ├── <Field Name 1>.png
    │   │   ├── <Field Name 1>.svg
    │   │   ├── <Field Name 2>.png
    │   │   ├── <Field Name 2>.svg  
    │   │   └── ...
    │   ├── <Data Source Name 2>
    │   │   ├── <Field Name 1>.png
    │   │   ├── <Field Name 1>.svg
    │   │   ├── <Field Name 2>.png
    │   │   ├── <Field Name 2>.svg  
    │   │   └── ...
    │   ├── Parameters
    │   │   ├── <Parameter Name 1>.png
    │   │   ├── <Parameter Name 1>.svg
    │   │   ├── <Parameter Name 2>.png
    │   │   ├── <Parameter Name 2>.svg  
    │   │   └── ...
    │   └── Sheets
    │   │   ├── <Sheet Name 1>.png
    │   │   ├── <Sheet Name 1>.svg
    │   │   ├── <Sheet Name 2>.png
    │   │   ├── <Sheet Name 2>.svg
    │   │   └── ...
    └── log_file.log (Optional, only for Flask app)

Clarifications w.r.t. this folder structure:

* ``<Root Folder>`` depends on how the tool is run (for more details check :doc:`usage`)
   * Executable: <Workbook Folder>/<Workbook Name> Files
   * Flask: <Workbook Name> Files.zip (saved in browser default download folder)
* ``<Workbook Name>``: name of the selected workbook
* ``<Data Source Name 1>``: name of the first data source used in the workbook
* ``<Field Name 1>``: name of the first (calculated) field from the parent data 
  source used in the workbook
* For parameter and sheet dependency graphs 2 separate subfolders ``Parameters`` 
  and ``Sheets`` are used
* ``log_file.log`` is generated only when the tool is run via the Flask app. 
  In other cases, the output is displayed directly in the command line instead 
  of being written to a log file.

Dependency Graphs
-----------------

The images below show some examples of output dependency graphs. 

The first example is a more complex example of a field with both backward 
and forward dependencies (explanation: see below):

.. image:: _static/images/21-example-graph.png
    :alt: Example Dependency Graph SVG
    :width: 100%

The second example is simpler but shows 1 additional node type that represents
a Level of Detail (LOD) expression (red ellipse, SVG tooltip with 
calculation also shown):

.. image:: _static/images/19-example-graph-lod.png
    :alt: Example Dependency Graph SVG
    :width: 75%

In general, the output images can be read as follows:

* **Green rectangles** represent data source fields (no dependencies)
* **Orange ellipses** represent calculated fields (at least 1 dependency)
* **Red ellipses** represent calculated fields (at least 1 dependency) 
  that contain Level of Detail (LOD) Expressions
* **Purple parallellograms** represent parameters
* **Light blue ellipse** represents the analyzed field (in this case ``CP Sales``)
* Elements **above** the analyzed field are **backward dependencies**, meaning 
  that they are required for the calculation of it
* Elements **below** the analyzed field are **forward dependencies**, meaning 
  that each of these elements directly or indirectly makes use of the ``CP Sales``
  calculated field.
* The levels of the graphs represent the **dependency level** of the 
  different elements. (NOTE: NOT TRUE, PLEASE REWRITE)
  * Backward dependencies are numbered -1 (for direct backward dependencies), -2, etc.
  * Forward dependencies are numbered 1 (for direct forward dependencies), 2, etc.

Field dependency graphs are exported as PNG and SVG files. The advantage of the 
SVG files compared to the PNG files is the ability to show the field calculations 
in the node tooltips, which is not possible for the PNG file.

Field Metadata
---------------

The output file ``Fields\<Workbook Name>.xlsx`` contains 2 sheets ``fields`` and 
``dependencies``. Below their column descriptions are described in detail.


Column definitions for "fields" sheet
"""""""""""""""""""""""""""""""""""""""

.. Alternative is list-table directive which "hard codes" the definitions here
.. list-table appears to be rendered a bit better in furo template

.. csv-table::
   :file: _data/column_definitions_fields.csv
   :widths: 20, 20, 60
   :header-rows: 1

Column definitions for "dependencies" sheet
""""""""""""""""""""""""""""""""""""""""""""

.. Alternative is list-table directive which "hard codes" the definitions here
.. list-table appears to be rendered a bit better in furo template

.. csv-table::
   :file: _data/column_definitions_dependencies.csv
   :widths: 20, 20, 60
   :header-rows: 1
   