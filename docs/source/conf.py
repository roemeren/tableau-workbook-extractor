# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import sys
import pathlib
from sphinx.application import Sphinx

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
    'sphinx_multiversion',           # Enable versioned documentation (requires pip install sphinx-multiversion)
    #'sphinx.ext.viewcode',          # Add links to view the source code of documented objects
]

templates_path = ['_templates']
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# html_theme = 'alabaster' # default theme
html_theme = 'furo' # requires pip install furo
html_static_path = ['_static']
# versioned title not possible? (see https://github.com/sphinx-contrib/multiversion/issues/61)
#  -> override default html_title (<project> <release> documentation) with fixed one
html_title = f"{project}"

# extend default sidebar with version selector
# sources: sphinx-multiversion quickstart + https://pradyunsg.me/furo/customisation/sidebar/)
html_sidebars = {
    "**": [
        # default sidebar
        "sidebar/brand.html",
        "sidebar/search.html",
        "sidebar/scroll-start.html",
        "sidebar/navigation.html",
        "sidebar/ethical-ads.html",
        # custom extension saved in docs/source/_templates
        "versioning.html",
        "sidebar/scroll-end.html",
        "sidebar/variant-selector.html",
    ]
}