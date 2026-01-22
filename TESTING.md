# Testing Guide

This document provides comprehensive instructions for running tests in the ValSKA-HERA-beam-FWHM project. All testing workflows are automated through Make targets and continuously validated via GitHub Actions CI.

## Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Running Tests](#running-tests)
- [Make Targets Reference](#make-targets-reference)
- [CI/CD Integration](#cicd-integration)
- [Running Specific Tests](#running-specific-tests)
- [Test Reports and Coverage](#test-reports-and-coverage)
- [Special Requirements](#special-requirements)
- [Troubleshooting](#troubleshooting)

## Quick Start

```bash
# Clone the repository
git clone https://github.com/uksrc/ValSKA-HERA-beam-FWHM.git
cd ValSKA-HERA-beam-FWHM

# Install dependencies (choose one method below)

# Option 1: Using conda (recommended)
conda env create -f valska_env.yaml
conda activate valska

# Option 2: Using pip
pip install -r requirements.txt

# Run all tests
make python-test      # Run unit tests
make notebook-test    # Run notebook validation tests
```

## Installation

### Development Dependencies

The project uses `pyproject.toml` to manage dependencies. Development dependencies include testing tools, linters, and notebook validation utilities.

**Core development dependencies** (defined in the `[project.optional-dependencies]` in `pyproject.toml`):
- `pytest` - Testing framework
- `pytest-cov` - Coverage reporting
- `pytest-mock` - Mocking support
- `nbmake` - Notebook execution and validation
- `black`, `isort` - Code formatting
- `flake8`, `pylint` - Linting
- `ruff`, `mypy` - Additional code quality tools

### Installation Methods

#### Method 1: Conda Environment (Recommended)

The `valska_env.yaml` file provides a complete conda environment specification:

```bash
# Create environment
conda env create -f valska_env.yaml

# Activate environment
conda activate valska
```

**Platform-specific notes:**
- **Galahad**: Use `cudatoolkit` (uncommented in `valska_env.yaml`)
- **Azimuth**: Use `cuda` (comment out `cudatoolkit`, uncomment `cuda`)

The conda environment includes:
- All runtime dependencies (astropy, numpy, scipy, etc.)
- MPI support (mpi4py >= 3.0.0)
- GPU support (CUDA, PyCUDA, magma)
- Editable install with dev dependencies via pip

#### Method 2: pip

```bash
# Install with development dependencies
pip install -r requirements.txt

# Or install directly
pip install -e .[dev]
```

**Note**: When using pip alone, system dependencies (MPI, CUDA, MultiNest) must be installed separately.

## Running Tests

### Unit Tests

Run Python unit tests located in the `tests/` directory:

```bash
make python-test
```

**What this does:**
- Executes pytest against all test files in `tests/`
- Generates coverage reports for `src/` directory
- Creates HTML coverage report in `build/reports/code-coverage/`
- Creates XML coverage report at `build/reports/code-coverage.xml`
- Creates JUnit XML test report at `build/reports/unit-tests.xml`

### Notebook Tests

Validate that all Jupyter notebooks execute without errors:

```bash
make notebook-test
```

**What this does:**
- Uses `pytest --nbmake` to execute notebooks
- Tests notebooks in the project root by default (configurable via `PYTHON_TEST_FOLDER_NBMAKE`)
- Excludes `.py` files automatically
- Validates that notebooks run end-to-end successfully

### Linting

Check code quality and formatting:

```bash
# Lint Python code
make python-lint

# Lint notebooks
make notebook-lint
```

**Linting includes:**
- `isort` - Import sorting verification
- `black` - Code formatting verification
- `flake8` - Style guide enforcement
- `pylint` - Advanced code analysis

Linting results are saved to `build/reports/linting-python.xml` and `build/reports/linting-notebooks.xml`.

### Formatting

Auto-format code to meet style guidelines:

```bash
# Format Python code
make python-format

# Format notebooks
make notebook-format
```

## Make Targets Reference

All testing targets are defined in `python.mk`. Below is a summary of commonly used targets:

| Target | Description | Key Variables |
|--------|-------------|---------------|
| `python-test` | Run pytest with coverage | `PYTHON_TEST_FILE` (default: `tests/`)<br>`PYTHON_VARS_AFTER_PYTEST` (pytest flags) |
| `notebook-test` | Execute notebooks with nbmake | `PYTHON_TEST_FOLDER_NBMAKE` (default: `.`)<br>`NOTEBOOK_IGNORE_FILES` (files to skip) |
| `python-lint` | Lint Python code | `PYTHON_LINT_TARGET` (default: `src/ tests/`) |
| `notebook-lint` | Lint notebooks | `NOTEBOOK_LINT_TARGET` (default: `.`) |
| `python-format` | Auto-format Python code | `PYTHON_LINE_LENGTH` (default: 79) |
| `notebook-format` | Auto-format notebooks | `PYTHON_LINE_LENGTH` (default: 79) |

### Customizing Make Variables

You can override Make variables on the command line:

```bash
# Run tests for a specific file
make python-test PYTHON_TEST_FILE=tests/test_utils.py

# Run tests with additional pytest flags
make python-test PYTHON_VARS_AFTER_PYTEST="-v -s"

# Test specific notebooks only
make notebook-test PYTHON_TEST_FOLDER_NBMAKE=notebooks/

# Ignore specific notebooks
make notebook-test NOTEBOOK_IGNORE_FILES="not 01_validation_GSM_beam.ipynb"
```

## CI/CD Integration

The project uses GitHub Actions for continuous integration. The workflow is defined in `.github/workflows/python-app.yml`.

**CI Pipeline:**
1. Checkout code
2. Set up Python 3.12
3. Install dependencies via `pip install -r requirements.txt`
4. Run `make python-test` (unit tests)
5. Run `make notebook-test` (notebook validation)

The CI pipeline runs on every push to validate that:
- All unit tests pass
- All notebooks execute without errors
- Code coverage is maintained

**Viewing CI Results:**
- Go to the [Actions tab](https://github.com/uksrc/ValSKA-HERA-beam-FWHM/actions) on GitHub
- Click on a workflow run to see detailed logs
- Download test artifacts (coverage reports, etc.) from completed runs

## Running Specific Tests

### Run a Single Test File

```bash
# Using Make
make python-test PYTHON_TEST_FILE=tests/test_utils.py

# Using pytest directly
pytest tests/test_utils.py
```

### Run a Single Test Function

```bash
pytest tests/test_utils.py::test_specific_function
```

### Run Tests Matching a Pattern

```bash
pytest -k "test_pattern"
```

### Run Tests with Verbose Output

```bash
make python-test PYTHON_VARS_AFTER_PYTEST="-v"

# Or directly
pytest -v tests/
```

### Run Tests and Stop at First Failure

```bash
pytest -x tests/
```

## Test Reports and Coverage

After running tests, reports are generated in the `build/` directory:

```
build/
├── reports/
│   ├── code-coverage/          # HTML coverage report (open index.html)
│   ├── code-coverage.xml       # XML coverage report (for CI tools)
│   ├── unit-tests.xml          # JUnit XML test results
│   ├── linting-python.xml      # Python linting results
│   └── linting-notebooks.xml   # Notebook linting results
└── code_analysis.stdout         # Detailed linting output
```

### Viewing Coverage Reports

```bash
# After running tests, open the HTML report
firefox build/reports/code-coverage/index.html

# Or check coverage in terminal
pytest --cov=src --cov-report=term-missing tests/
```

### Interpreting Test Failures

- **Unit test failures**: Check the pytest output for detailed error messages and tracebacks
- **Coverage drops**: Review the coverage report to identify untested code paths
- **Linting errors**: Run `make python-format` to auto-fix formatting issues
- **Notebook failures**: Notebooks may fail due to missing data, long execution times, or environment issues

## Special Requirements

### System Dependencies

Some tests require system-level dependencies that cannot be installed via pip or conda alone:

1. **MultiNest**
   - Required for Bayesian inference tests
   - Install from: https://github.com/JohannesBuchner/MultiNest
   - The `pymultinest` Python package requires MultiNest libraries to be available

2. **MPI (Message Passing Interface)**
   - Required for parallel computing tests
   - Provided by `mpi4py` (included in conda environment)
   - On some systems, you may need to install MPI separately:
     ```bash
     # Ubuntu/Debian
     sudo apt-get install libopenmpi-dev
     
     # macOS
     brew install open-mpi
     ```

3. **CUDA (for GPU tests)**
   - Required for GPU-accelerated tests
   - Install appropriate CUDA toolkit for your system
   - See platform-specific notes in [Installation](#installation)

### Heavy/Slow Tests

Some tests are computationally intensive:

#### Notebook Tests
- **Execution time**: Notebooks may take several minutes to complete
- **Data requirements**: Some notebooks require external data files
- **Resource usage**: High memory and CPU usage during execution

**Tips:**
- Run notebook tests separately from unit tests
- Use `NOTEBOOK_IGNORE_FILES` to skip problematic notebooks during development
- Consider running full notebook suite only in CI or before commits

#### Integration Tests
- Tests involving MultiNest or MPI may be slow
- Consider using pytest markers to separate fast and slow tests:
  ```bash
  # Run only fast tests
  pytest -m "not slow" tests/
  
  # Run only slow tests
  pytest -m slow tests/
  ```

### Hardware Dependencies

- **GPU tests**: Require CUDA-compatible GPU and drivers
- **MPI tests**: May require specific cluster/network configuration
- **Memory**: Some tests require significant RAM (4GB+ recommended)

## Troubleshooting

### Common Issues

#### "ModuleNotFoundError" when running tests

**Cause**: Dependencies not installed or environment not activated

**Solution**:
```bash
# Verify environment is activated
conda activate valska

# Reinstall dependencies
pip install -e .[dev]
```

#### Tests pass locally but fail in CI

**Cause**: Environment differences, missing system dependencies

**Solution**:
- Check `.github/workflows/python-app.yml` for CI environment setup
- Ensure your local Python version matches CI (3.12)
- Check for platform-specific code that may behave differently

#### Notebook tests fail with "Kernel died"

**Cause**: Notebook cell raised unhandled exception or used too much memory

**Solution**:
- Run the notebook interactively to identify the failing cell
- Check notebook output for error messages
- Increase available memory or optimize notebook code

#### Coverage report not generated

**Cause**: Tests failed before coverage could be computed

**Solution**:
- Fix failing tests first
- Ensure `pytest-cov` is installed
- Check that `PYTHON_SRC` variable points to correct source directory

#### Linting errors block testing

**Cause**: Code doesn't meet style guidelines

**Solution**:
```bash
# Auto-fix most formatting issues
make python-format

# Then re-run linting
make python-lint
```

#### MultiNest/MPI tests fail

**Cause**: System dependencies not properly installed

**Solution**:
- Verify MultiNest libraries are in system library path
- Check MPI installation: `mpirun --version`
- Consult system-specific installation guides

### Getting Help

If you encounter issues not covered here:

1. Check existing [GitHub Issues](https://github.com/uksrc/ValSKA-HERA-beam-FWHM/issues)
2. Review the [CI workflow logs](https://github.com/uksrc/ValSKA-HERA-beam-FWHM/actions)
3. Contact the UKSRC Science Validation team:
   - Peter Sims (PO) - ps550 [at] cam.ac.uk
   - Tianyue Chen (SM) - tianyue.chen [at] manchester.ac.uk
   - Quentin Gueuning - qdg20 [at] cam.ac.uk
   - Ed Polehampton - edward.polehampton [at] stfc.ac.uk
   - Vlad Stolyarov - vs237 [at] cam.ac.uk

## Maintenance

**Important**: This `TESTING.md` file is the single source of truth for testing documentation. 

- All future edits to testing guidance should be made to this file only
- The Sphinx documentation automatically includes this file via MyST
- Do not duplicate testing instructions in other locations
- Keep this file in sync with changes to `Makefile`, `python.mk`, or CI workflows
