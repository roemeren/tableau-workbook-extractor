Roadmap
========

This document outlines some possible new features and enhancements for 
the application, as well as known issues that are being tracked.

New Features
------------

- **Simplify the extraction of unique dependencies**: Currently, there is no 
  efficient method to quickly extract unique forward and backward dependencies, 
  along with their minimum dependency levels, for a given field, parameter, or 
  sheet, as demonstrated on the :doc:`example` page. By expanding the output 
  Excel file to include additional precalculated columns, 
  we can streamline this process and make it more user-friendly.
- **Batch processing**: implement functionality to process 
  multiple Tableau workbooks at once
- **Remove multi-line comments from cleaned calculations**: Currently, 
  multi-line comments are not removed from the cleaned calculated field 
  expressions in the output Excel file. The goal is to eliminate all single- 
  and multi-line comments from the original calculation expressions.
- **Provide Linux and macOS executables**: Develop and distribute executables 
  for the tool compatible with Linux and macOS, expanding accessibility 
  for users on different operating systems.
- **Improve Flask app error handling**: Enhance the user experience by 
  implementing robust error handling in the Flask app. Users should receive 
  clear feedback when selecting incorrect files or when processing errors 
  occur, ensuring a smoother interaction with the application.

Known Issues
-------------

Some of these issues stem from limitations within the tool. 
Others are related to the current version of the ``tableaudocumentapi`` Python 
package, which at the moment doesn't appear to be actively developed. 
The lack of new releases may be related to emerging alternatives, such as the 
official Tableau Metadata API and other third-party solutions for managing 
Tableau workbooks.

- **Incomplete processing of Tableau workbooks**: Some Tableau workbooks 
  generate errors during analysis, and further investigation is needed to 
  identify the causes and implement necessary bug fixes.
- **Not all dependencies are captured**: Some fields may be used solely to 
  initialize parameter values when the workbook is opened, while data source 
  fields may depend on fields hidden in the data source and not visible in the 
  dashboard; additionally, fields and parameters may be utilized in dashboard 
  actions.
- **Not all field captions are captured**: Field captions may be missing, 
  resulting in the use of their internal ID in the outputs, 
  which may relate to hidden fields and dependencies.
- **Not all extracted fields are assigned to the correct data source**: Some 
  (copies of) fields may be linked to a data source to which they do not belong.

Enhancements
------------

- **Optimization of recursive dependency analysis functions**: Enhance the 
  performance of the recursive functions that analyze backward and 
  forward field dependencies by implementing memoization to cache 
  previously computed results. This enhancement may significantly 
  reduce redundant calculations and improve overall execution time 
  for complex Tableau workbooks.
- **Centralization of configuration settings**: Centralizing configurations 
  such as colors, output file names, and shapes will streamline management 
  and improve consistency across the tool.
- **Improve the quality and readability of output graphs**: Enhance the 
  aesthetics of the output network graphs by refining colors, fonts, and 
  node arrangements in the PNG/SVG images for better visual appeal and clarity.
- **Prettify the Flask app**: Improve the user interface and overall design of 
  the Flask application to enhance user experience and make it visually appealing.
- **Refactor the main processing routine**: The ``process_twb`` function in the 
  ``shared\processing.py`` script is quite large. It could be divided into smaller, 
  distinct parts to improve readability and make the code easier to 
  follow and maintain.
