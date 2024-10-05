# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import sys
import pathlib

# Add the app directory to the system path
sys.path.insert(0, (pathlib.Path(__file__).parents[2] / 'app').resolve().as_posix())

project = 'Tableau Workbook Extractor'
copyright = '2024, Robert Emerencia'
author = 'Robert Emerencia'
release = 'latest'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',            # Generate documentation from docstrings in your code
    'sphinx.ext.autosummary',        # Create summary tables for modules, classes, and functions automatically
    'sphinx.ext.napoleon',           # Support for Google-style and NumPy-style docstrings
    #'sphinx_multiversion',          # Enable versioned documentation (requires pip install sphinx-multiversion)
    #'sphinx.ext.viewcode',          # Add links to view the source code of documented objects
]

templates_path = ['_templates']
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# html_theme = 'alabaster' # default theme
html_theme = 'furo' # reauires pip install furo
html_static_path = ['_static']
