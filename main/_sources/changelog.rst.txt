Changelog
=========

v2.0.0 (2025-11-03)
-------------------
The original Flask-based deployment with a more full-featured Dash app 
offering the same core functionality plus direct, interactive visualization.

Highlights:

- Immediate visualization of generated dependency graphs, overview statistics, and field details
- Shortest calculation path exploration between Tableau fields
- Limited multi-user support by isolating session data and threading state in user-specific dictionaries instead of global variables
- Safe cooperative cancellation via a Cancel button that gracefully stops background processing
- Unified progress tracking for both the Dash and legacy Flask contexts
- General code cleanup, bug fixes and improved structure for maintainability

v1.2.1 (2025-10-15)
-------------------
Add PNG generation toggle and optimize dependency resolution

- Optional PNG Generation: added a checkbox in the Flask app to 
  let users choose whether to generate PNG files alongside SVGs. By default, 
  only SVGs are created for faster processing.
- Memoization for Dependency Resolution: replaced the previous naive recursive 
  logic in both forward and backward 
  dependency functions with a memoized implementation. This significantly 
  reduces redundant calculations and improves performance (~3× faster).

v1.1.8 (2024-10-10)
-------------------
Switch from Flask development server to Gunicorn

- Updated Dockerfile to use Gunicorn as the web server.
- Changed the ``CMD`` instruction inside Dockerfile to run Gunicorn and 
  bind to ``0.0.0.0:5000``.

v1.1.7 (2024-10-08)
-------------------
- Minor simplification in build-docs workflow
- Use separate production environment for Render deployment

v1.1.6 (2024-10-07)
-------------------
- Modified build-docs workflow permissions
- Fixed indendation errors in module docstrings

v1.1.5 (2024-10-07)
-------------------
- Changed Flask app title

v1.1.4 (2024-10-06)
-------------------
- Changed Flask app output file name

v1.1.3 (2024-10-06)
-------------------
- Added multi-version documentation
- Split application deployment from documentation building workflows
- Changed main documentation link in README

v1.1.2 (2024-10-06)
-------------------
- Added web.flask_app documentation to scripts reference
- Minor changes in README.

v1.1.1 (2024-10-06)
-------------------
- Minor bug correction in the output Excel file.
- Replaced detailed information in `README.md` with Sphinx documentation.
- Reduced the amount of information in `README.md` for improved clarity.

v1.1.0 (2024-09-30)
-------------------
- Initial release of the tool with support for local execution and deployment 
  in a Dockerized environment.