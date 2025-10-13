# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here.
import sys
import os
from pathlib import Path
#sys.path.insert(0, str(Path('..', 'src').resolve()))
sys.path.insert(0, str(Path(__file__).resolve().parents[2])+"/src")
#sys.path.insert(0, str(Path(__file__).resolve().parents[2])+"/src/valska_hera_beam")
import valska_hera_beam

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'ValSKA-HERA-beam-FWHM'
copyright = '2025, P.Sims, Q.Gueuning, E.Polehampton, T.Chen, V.Stolyarov'
author = 'P.Sims, Q.Gueuning, E.Polehampton, T.Chen, V.Stolyarov'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['sphinx.ext.duration',
              'sphinx.ext.doctest',
              'sphinx.ext.autodoc',
              'sphinx.ext.autosummary',
]

autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "private-members": True,
}

autodoc_mock_imports = ['bayeseor',
			'anesthetic',
			'matplotlib',
			'yaml']

templates_path = ['_templates']
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
