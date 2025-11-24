# Contributing to ValSKA-HERA-beam-FWHM

Thank you for your interest in contributing to ValSKA-HERA-beam-FWHM! This document provides guidelines for contributing to the project.

## Getting Started

### Setting Up Your Development Environment

1. Clone the repository:
   ```bash
   git clone https://github.com/uksrc/ValSKA-HERA-beam-FWHM.git
   cd ValSKA-HERA-beam-FWHM
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

   Or, if using conda:
   ```bash
   conda env create -f valska_env.yaml
   conda activate valska
   ```

### Installing Pre-commit Hooks

This repository uses pre-commit hooks to ensure code quality and consistency. Pre-commit hooks automatically check your code before each commit to catch common issues early.

#### Installation

1. Install pre-commit (if not already installed via requirements.txt):
   ```bash
   pip install pre-commit
   ```

2. Install the git hook scripts:
   ```bash
   pre-commit install
   ```

3. (Optional) Run against all files to check the current state:
   ```bash
   pre-commit run --all-files
   ```

#### What the Pre-commit Hooks Do

Our pre-commit configuration includes:

- **check-yaml**: Validates YAML files
- **end-of-file-fixer**: Ensures files end with a newline
- **trailing-whitespace**: Removes trailing whitespace
- **check-added-large-files**: Prevents large files from being committed (max 1MB)
- **black**: Formats Python code automatically
- **ruff**: Fast Python linter that auto-fixes common issues
- **nbqa-black**: Formats code in Jupyter notebooks
- **nbqa-isort**: Sorts imports in Jupyter notebooks
- **nbstripout**: Strips outputs from Jupyter notebooks to keep the repository clean

#### Using Pre-commit

Once installed, the hooks will run automatically on `git commit`. If any hook fails or modifies files:

1. Review the changes made by the hooks
2. Stage the modified files: `git add <modified-files>`
3. Commit again: `git commit -m "your message"`

To skip the hooks temporarily (not recommended):
```bash
git commit --no-verify
```

To run hooks manually on specific files:
```bash
pre-commit run --files <file1> <file2>
```

## Making Contributions

### Before Submitting a Pull Request

1. Ensure all tests pass:
   ```bash
   make python-test
   make notebook-test
   ```

2. Format and lint your code:
   ```bash
   make python-format
   make python-lint
   make notebook-format
   make notebook-lint
   ```

3. Make sure pre-commit hooks pass:
   ```bash
   pre-commit run --all-files
   ```

### Pull Request Process

1. Create a new branch for your feature or bugfix
2. Make your changes and commit them with clear, descriptive messages
3. Push your branch to GitHub
4. Open a pull request against the main branch
5. Wait for review and address any feedback

## Code Style

- Python code should follow PEP 8 guidelines (enforced by black and ruff)
- Line length is set to 79 characters
- Use type hints where appropriate
- Write clear docstrings for functions and classes

## Jupyter Notebooks

- Always strip outputs before committing (handled automatically by nbstripout hook)
- Keep notebooks focused and well-documented
- Test notebooks to ensure they run end-to-end

## Questions or Issues?

If you have questions or need help, please:

- Open an issue on GitHub
- Contact the UKSRC science validation tooling team (see README.md for contact details)

Thank you for contributing!
