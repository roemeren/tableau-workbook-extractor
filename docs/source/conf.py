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
release = 'v1.1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',            # Generate documentation from docstrings in your code
    'sphinx.ext.autosummary',        # Create summary tables for modules, classes, and functions automatically
    'sphinx.ext.napoleon',           # Support for Google-style and NumPy-style docstrings
    #'sphinx.ext.viewcode',          # Add links to view the source code of documented objects
]

# Napoleon settings (not working)
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

templates_path = ['_templates']
exclude_patterns = []

# Display type hints in the documentation
autodoc_typehints = 'description'  # Options: 'description', 'signature', 'none'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']
