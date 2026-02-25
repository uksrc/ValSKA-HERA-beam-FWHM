Testing Guide for Developers
============================

This document provides comprehensive instructions for running tests in the ValSKA-HERA-beam-FWHM project. All testing workflows are automated through Make targets and continuously validated via GitHub Actions CI.

Development Dependencies
------------------------

The project uses ``pyproject.toml`` to manage the devlopment dependencies. These include testing tools, linters, and notebook validation utilities.

**Core development dependencies** (defined in the ``[project.optional-dependencies]`` in ``pyproject.toml``):

- ``pytest`` - Testing framework
- ``pytest-cov`` - Coverage reporting
- ``pytest-mock`` - Mocking support
- ``nbmake`` - Notebook execution and validation
- ``black``, ``isort`` - Code formatting
- ``flake8``, ``pylint`` - Linting
- ``ruff``, ``mypy`` - Additional code quality tools

The recommended way to install the dependencies is via the conda environment specification in ``valska_env.yaml``. This includes a section at the end to install the development dependencies from ``pyproject.toml`` using pip.

 
Unit Tests
----------

Unit tests should be added to the repository in the ``tests/`` directory.

There should be one Python file containing unit tests for each Python file in the main src/ directory. For example, ``utils.py`` in the ``src/`` directory has unit tests in file ``test_utils.py`` in the ``tests/`` directory.

Each method in the source code should be tested with one or more unit tests - there could be several unit tests for the same method if there are different options for the input arguments (e.g. testing the default option as well as user supplied input). Unit tests should check the output of each method using assert statements against hard-coded or independently calculated "truth" values.

We use Makefiles to give convenience methods for running the tests, linting and formatting with Black. These useful make targets are in the file python.mk.

To run pytest with options set to write coverage reports:

.. code-block:: bash

   make python-test

**What this does:**

- Executes pytest against all test files in ``tests/``
- Generates coverage reports for ``src/`` directory
- Creates HTML coverage report in ``build/reports/code-coverage/``
- Creates XML coverage report at ``build/reports/code-coverage.xml``
- Creates JUnit XML test report at ``build/reports/unit-tests.xml``


Notebook Tests
--------------

Jupyter notebooks can be tested (end-to-end) using ``nbmake``. This is set up in Make targets so that it can be called with:

.. code-block:: bash

   make notebook-test

**What this does:**

- Uses ``pytest --nbmake`` to execute notebooks
- Tests notebooks in the project root by default (configurable via ``PYTHON_TEST_FOLDER_NBMAKE``)
- Excludes ``.py`` files automatically
- Validates that notebooks run end-to-end successfully

It won't work where user input is required, or paths need to be set up - for example, the cells which actually make the plots and read the data will not be tested. These cells can be excluded from the test by including a tag in the notebook JSON. Open the notebook in a text editor and modify the metadata to add the "skip-execution" tag:

.. code-block:: bash

   {
   "cell_type": "code",
   "execution_count": 4,
   "metadata": {
       "tags": [
           "skip-execution"
       ]
   },
   "outputs": [...],
   "source": [...],
   }



Linting and Formatting
----------------------

Auto-format code to meet style guidelines:

.. code-block:: bash

   # Format Python code
   make python-format

   # Format notebooks
   make notebook-format


To run linting

.. code-block:: bash

   # Lint Python code
   make python-lint

   # Lint notebooks
   make notebook-lint


Linting and formatting use `ruff <https://docs.astral.sh/ruff/>`_.

Linting results are saved to ``build/reports/linting-python.xml`` and ``build/reports/linting-notebooks.xml``.


Make Targets Reference
----------------------

All of the testing targets are defined in ``python.mk``. Below is a summary of commonly used targets that were described above:

.. list-table:: Make targets.
   :header-rows: 1

   * - Target
     - Description
     - Key Variables
   * - ``python-test``
     - Run pytest with coverage
     - ``PYTHON_TEST_FILE`` (default: ``tests/``), 
       ``PYTHON_VARS_AFTER_PYTEST`` (pytest flags)
   * - ``notebook-test``
     - Execute notebooks with nbmake
     - ``PYTHON_TEST_FOLDER_NBMAKE`` (default: ``.``), 
       ``NOTEBOOK_IGNORE_FILES`` (files to skip)
   * - ``python-lint``
     - Lint Python code
     - ``PYTHON_LINT_TARGET`` (default: ``src/ tests/``),
       ``PYTHON_SWITCHES_FOR_RUFF`` (default: none)
   * - ``notebook-lint``
     - Lint notebooks
     - ``NOTEBOOK_LINT_TARGET`` (default: ``notebooks/``),
       ``NOTEBOOK_SWITCHES_FOR_RUFF`` (default: ``--ignore=D100,N802``)
   * - ``python-format``
     - Auto-format Python code
     - ``PYTHON_LINE_LENGTH`` (default: 79)
   * - ``notebook-format``
     - Auto-format notebooks
     - ``PYTHON_LINE_LENGTH`` (default: 79)

Customizing Make Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~

You can override Make variables on the command line:

.. code-block:: bash

   # Run tests for a specific file
   make python-test PYTHON_TEST_FILE=tests/test_utils.py

   # Run tests with additional pytest flags
   make python-test PYTHON_VARS_AFTER_PYTEST="-v -s"

   # Test specific notebooks only
   make notebook-test PYTHON_TEST_FOLDER_NBMAKE=notebooks/

   # Ignore specific notebooks
   make notebook-test NOTEBOOK_IGNORE_FILES="not 01_validation_GSM_beam.ipynb"


CI/CD Integration
-----------------

The project uses GitHub Actions for continuous integration. The workflow is defined in ``.github/workflows/valska-actions.yml``.

**CI Pipeline:**

The pipeline consists of 3 jobs, with each job checking out the code, installing dependencies (cached between jobs) 
and running the following steps:

1. Linting and Formatting

   - Run ``pre-commit run --all-files``
   - Upload lint reports

2. Testing

   - Run ``make python-test`` (unit tests)
   - Run ``make notebook-test`` (notebook validation)

3. Documentation

   - Run ``sphinx-build -W -b html docs/source/ docs/_build/html``

The CI pipeline runs on every push to validate that:

- Formatting and linting rules have been followed
- All unit tests pass
- All notebooks execute without errors
- Code coverage is maintained
- Documentation builds without errors or warnings

**Viewing CI Results:**

- Go to the `Actions tab <https://github.com/uksrc/ValSKA-HERA-beam-FWHM/actions>`_ on GitHub
- Click on a workflow run to see detailed logs
- Download test artifacts (coverage reports, etc.) from completed runs

Running Specific Tests
----------------------

Run a Single Test File
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Using Make
   make python-test PYTHON_TEST_FILE=tests/test_utils.py

   # Using pytest directly
   pytest tests/test_utils.py


Run a Single Test Function
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Using pytest directly for the test
   # "test_build_pp_groups_from_paths_default"
   pytest tests/test_utils.py::test_build_pp_groups_from_paths_default


Run Tests Matching a Pattern
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Using Make
   make python-test PYTHON_VARS_AFTER_PYTEST="-k build_pp_groups"

   # Using pytest directly
   pytest -k build_pp_groups


Run Tests with Verbose Output
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Using Make
   make python-test PYTHON_VARS_AFTER_PYTEST="-v"

   # Using pytest directly
   pytest -v tests/


Run Tests and Stop at First Failure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Using Make
   make python-test PYTHON_VARS_AFTER_PYTEST="-x"

   # Using pytest directly
   pytest -x tests/


Test Reports and Coverage
-------------------------

After running tests, reports are generated in the ``build/`` directory:

.. code-block::

   build/
   ├── reports/
   │   ├── code-coverage/          # HTML coverage report (open index.html)
   │   ├── code-coverage.xml       # XML coverage report (for CI tools)
   │   ├── unit-tests.xml          # JUnit XML test results
   │   ├── linting-python.xml      # Python linting results
   │   └── linting-notebooks.xml   # Notebook linting results
   └── code_analysis.stdout        # Detailed linting output


In order to view the last run coverage report without re-running the tests, either view in html format from ``build/reports/code-coverage/index.html``, or check on the terminal,

.. code-block:: bash

   coverage report -m


Interpreting Test Failures
~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Unit test failures**: Check the pytest output for detailed error messages and tracebacks
- **Coverage drops**: Review the coverage report to identify untested code paths
- **Linting errors**: Run ``make python-format`` to auto-fix formatting issues
- **Notebook failures**: Notebooks may fail due to missing data, long execution times, or environment issues


Getting Help
------------

If you encounter issues not covered here:

1. Check existing `GitHub Issues <https://github.com/uksrc/ValSKA-HERA-beam-FWHM/issues>`_
2. Review the `CI workflow logs <https://github.com/uksrc/ValSKA-HERA-beam-FWHM/actions>`_
3. Contact the UKSRC Science Validation team:

   - Peter Sims (PO) - ps550 [at] cam.ac.uk
   - Tianyue Chen (SM) - tianyue.chen [at] manchester.ac.uk
   - Quentin Gueuning - qdg20 [at] cam.ac.uk
   - Ed Polehampton - edward.polehampton [at] stfc.ac.uk
   - Vlad Stolyarov - vs237 [at] cam.ac.uk