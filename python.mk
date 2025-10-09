# include Makefile for python related targets and variables

.PHONY: metrics-collect-target
$(filter-out metrics-collect-target, $(MAKECMDGOALS)): metrics-collect-target

# do not declare targets if help had been invoked
ifneq (long-help,$(firstword $(MAKECMDGOALS)))
ifneq (help,$(firstword $(MAKECMDGOALS)))

ifeq ($(strip $(PROJECT)),)
  NAME=$(shell basename $(CURDIR))
else
  NAME=$(PROJECT)
endif

PYTHON_SUPPORT := $(shell dirname $(abspath $(lastword $(MAKEFILE_LIST))))/.make-python-support
RELEASE_SUPPORT := $(shell dirname $(abspath $(lastword $(MAKEFILE_LIST))))/.make-release-support
PYTHON_SCRIPT_DIR := $(shell dirname $(abspath $(lastword $(MAKEFILE_LIST))))
METADATA_SUPPORT := $(shell dirname $(abspath $(lastword $(MAKEFILE_LIST))))/.make-metadata-support

VERSION=$(shell . $(RELEASE_SUPPORT) ; RELEASE_CONTEXT_DIR=$(RELEASE_CONTEXT_DIR) setContextHelper; CONFIG=${CONFIG} setReleaseFile; getVersion)
TAG=$(shell . $(RELEASE_SUPPORT); RELEASE_CONTEXT_DIR=$(RELEASE_CONTEXT_DIR) setContextHelper; CONFIG=${CONFIG} setReleaseFile; getTag)

SHELL=/usr/bin/env bash

PYTHON_SRC ?= src/## Python src directory - defaults to src

PYTHON_RUNNER ?=## use to specify command runner, e.g. "poetry run" or "python -m"

PYTHON_VARS_BEFORE_PYTEST ?= PYTHONPATH=$(CURDIR)/$(PYTHON_SRC):/app/$(PYTHON_SRC):$(PYTHONPATH)## used to include needed argument variables to pass to pytest if necessary

PYTHON_VARS_AFTER_PYTEST ?=## used to include optional pytest flags

PYTHON_TEST_FILE ?= tests/## Option pytest test file

PYTHON_LINE_LENGTH ?= 79## Default value piped to all linting tools

PYTHON_TEST_FOLDER_NBMAKE ?= .## Option folder for notebook tests

NOTEBOOK_IGNORE_FILES ?=## Option to exclude test files, usage: not <file1> and not <file2>

PYTHON_FILE_EXTENSION_IGNORE ?= not .py## Used to ignore .py files from being tested in notebook-test target

ifeq ($(NOTEBOOK_IGNORE_FILES),)
	PYTHON_SWITCHES_FOR_NBMAKE ?= --disable-warnings -rs -k "$(PYTHON_FILE_EXTENSION_IGNORE)"
else
	PYTHON_SWITCHES_FOR_NBMAKE ?= --disable-warnings -rs -k "$(PYTHON_FILE_EXTENSION_IGNORE) and $(NOTEBOOK_IGNORE_FILES)"
endif

PYTHON_SWITCHES_FOR_BLACK ?=## Custom switches added to black

PYTHON_SWITCHES_FOR_ISORT ?=## Custom switches added to isort

PYTHON_SWITCHES_FOR_PYLINT ?=## Custom switches added to pylint for all python code

NOTEBOOK_SWITCHES_FOR_PYLINT ?=## Custom switches added to pylint for notebooks

PYTHON_SWITCHES_FOR_FLAKE8 ?=## Custom switches added to flake8 for all python code

NOTEBOOK_SWITCHES_FOR_FLAKE8 ?=## Custom switches added to flake8 for notebooks

PYTHON_LINT_TARGET ?= $(PYTHON_SRC) tests/## Paths containing python to be formatted and linted

NOTEBOOK_LINT_TARGET ?= .## Paths containing Jupyter notebooks to be formatted and linted

# Possible PYTHON_BUILD_TYPE types:
# 		- tag_setup : Building for release with setup.py
# 	    - tag_pyproject: Building for release with pyproject.toml
#       - non_tag_setup: Dirty Building with setup.py
#	    - non_tag_pyproject: Dirty Building with pyproject.toml

PYTHON_BUILD_TYPE ?= non_tag_pyproject## used to differentiate build types
PYTHON_SWITCHES_FOR_BUILD ?= --sdist --wheel## switches passed to -m build for building wheels and dists

PYTHON_PUBLISH_USERNAME ?=## Username used to publish

PYTHON_PUBLISH_PASSWORD ?=## Password used to publish

PYTHON_PUBLISH_URL ?=## URL to publish

.PHONY: python-pre-build python-do-build python-post-build python-build \
	python-format python-pre-format python-do-format python-post-format \
	python-lint python-pre-lint python-do-lint python-post-lint \
	python-test python-pre-test python-do-test python-post-test \
	python-publish python-pre-publish python-do-publish

python-pre-format:

python-post-format:

python-do-format:
	$(PYTHON_RUNNER) isort --profile black --line-length $(PYTHON_LINE_LENGTH) $(PYTHON_SWITCHES_FOR_ISORT) $(PYTHON_LINT_TARGET)
	$(PYTHON_RUNNER) black --exclude .+\.ipynb --line-length $(PYTHON_LINE_LENGTH) $(PYTHON_SWITCHES_FOR_BLACK) $(PYTHON_LINT_TARGET)

## TARGET: python-format
## SYNOPSIS: make python-format
## HOOKS: python-pre-format, python-post-format
## VARS:
##       PYTHON_RUNNER=<python executor> - defaults to empty, but could pass something like python -m
##       PYTHON_LINT_TARGET=<file or directory path to Python code> - default 'src/ tests/'
##		 PYTHON_LINE_LENGTH=<line length> - defaults to 79, set it once and all linters will use this value
##       PYTHON_SWITCHES_FOR_ISORT=<additional switches to pass to isort>
##       PYTHON_SWITCHES_FOR_BLACK=<additional switch to pass to black>
##
##  Reformat project Python code in the given directories/files using black and isort.

python-format: python-pre-format python-do-format python-post-format  ## format the Python code

python-pre-lint:

python-post-lint:

python-do-lint:
	@mkdir -p build/reports;
	$(PYTHON_RUNNER) isort --check-only --profile black --line-length $(PYTHON_LINE_LENGTH) $(PYTHON_SWITCHES_FOR_ISORT) $(PYTHON_LINT_TARGET)
	$(PYTHON_RUNNER) black --exclude .+\.ipynb --check --line-length $(PYTHON_LINE_LENGTH) $(PYTHON_SWITCHES_FOR_BLACK) $(PYTHON_LINT_TARGET)
	$(PYTHON_RUNNER) flake8 --show-source --statistics --max-line-length $(PYTHON_LINE_LENGTH) $(PYTHON_SWITCHES_FOR_FLAKE8) $(PYTHON_LINT_TARGET)
	$(PYTHON_RUNNER) pylint --output-format=parseable,parseable:build/code_analysis.stdout,pylint_junit.JUnitReporter:build/reports/linting-python.xml --max-line-length $(PYTHON_LINE_LENGTH) $(PYTHON_SWITCHES_FOR_PYLINT) $(PYTHON_LINT_TARGET)
	@make --no-print-directory join-lint-reports

## TARGET: python-lint
## SYNOPSIS: make python-lint
## HOOKS: python-pre-lint, python-post-lint
## VARS:
##       PYTHON_RUNNER=<python executor> - defaults to empty, but could pass something like python -m
##       PYTHON_LINT_TARGET=<file or directory path to Python code> - default 'src/ tests/'
##		 PYTHON_LINE_LENGTH=<line length> - defaults to 79, set it once and all linters will use this value
##       PYTHON_SWITCHES_FOR_ISORT=<additional switches to pass to isort>
##       PYTHON_SWITCHES_FOR_BLACK=<additional switch to pass to black>
##       PYTHON_SWITCHES_FOR_FLAKE8=<additional switch to pass to flake8>
##       PYTHON_SWITCHES_FOR_PYLINT=<additional switch to pass to pylint>
##
##  Lint check project Python code in the given directories/files using black, isort, flake8 and pylint.

python-lint: python-pre-lint python-do-lint python-post-lint  ## lint the Python code

python-pre-build:

python-post-build:

python-do-build:
	@. $(PYTHON_SUPPORT) ; \
		PYTHON_RUNNER="$(PYTHON_RUNNER)" \
		PYTHON_SWITCHES_FOR_BUILD="$(PYTHON_SWITCHES_FOR_BUILD)" \
		pythonBuild $(PYTHON_BUILD_TYPE)

## TARGET: python-build
## SYNOPSIS: make python-build
## HOOKS: python-pre-build, python-post-build
## VARS:
##       PYTHON_RUNNER=<python executor> - defaults to empty, but could pass something like python -m
##       PYTHON_BUILD_TYPE=[tag_setup|non_tag_setup|non_tag_pyproject|tag_pyproject]
##       PYTHON_SWITCHES_FOR_BUILD=<options for -m build> - defaults to: --sdist --wheel
##
##  Build the nominated package type for project Python code, and decorate the package
##  with the SKAO metadata required for publishing to the Central Artefact Repository.
##  Types:.
##    tag_setup:         python3 setup.py sdist bdist_wheel
##    non_tag_setup:     python3 setup.py egg_info -b+dev[.c${CI_COMMIT_SHORT_SHA}] sdist bdist_wheel
##    non_tag_pyproject: pyproject-build (or python3 -m build) (pyproject.toml package version set to +dev[.c${CI_COMMIT_SHORT_SHA}])
##    tag_pyproject:     pyproject-build (or python3 -m build)

python-build: python-pre-build python-do-build python-post-build  ## build the Python package

python-pre-test:

python-post-test:

python-do-test:
	@$(PYTHON_RUNNER) pytest --version -c /dev/null
	@mkdir -p build
	$(PYTHON_VARS_BEFORE_PYTEST) $(PYTHON_RUNNER) pytest $(PYTHON_VARS_AFTER_PYTEST) \
	 --cov=$(PYTHON_SRC) --cov-report=term-missing --cov-report html:build/reports/code-coverage --cov-report xml:build/reports/code-coverage.xml --junitxml=build/reports/unit-tests.xml $(PYTHON_TEST_FILE)

## TARGET: python-test
## SYNOPSIS: make python-test
## HOOKS: python-pre-test, python-post-test
## VARS:
##       PYTHON_RUNNER=<python executor> - defaults to empty, but could pass something like python -m
##       PYTHON_TEST_FILE=<paths and/or files for testing> - defaults to tests/unit/
##       PYTHON_VARS_BEFORE_PYTEST=<environment variables defined before pytest in run> - default empty
##       PYTHON_VARS_AFTER_PYTEST=<additional switches passed to pytest> - default empty
##
##  Run pytest against the tests defined in ./tests.  By default, this will pickup any pytest
##  specific configuration set in pytest.ini, setup.cfg etc. located in ./tests

python-test: python-pre-test python-do-test python-post-test  ## test the Python package

python-pre-publish:

python-post-publish:

python-do-publish:
	$(PYTHON_RUNNER) twine upload --username ${PYTHON_PUBLISH_USERNAME} --password ${PYTHON_PUBLISH_PASSWORD} --repository-url $(PYTHON_PUBLISH_URL) dist/*

## TARGET: python-publish
## SYNOPSIS: make python-publish
## HOOKS: python-pre-publish, python-post-publish
## VARS:
##       PYTHON_RUNNER=<python executor> - defaults to empty, but could pass something like python -m
##       PYTHON_PUBLISH_USERNAME=<twine user> - default empty
##       PYTHON_PUBLISH_PASSWORD=<twine user password> - default empty
##       PYTHON_PUBLISH_URL=<repository URL> - default empty
##
##  Run twine to publish artefacts built in the project dist/ directory.

python-publish: python-pre-publish python-do-publish python-post-publish  ## publish the Python artefact to the repository

## TARGET: python-exportlock
## SYNOPSIS: make python-exportlock
## HOOKS: none
## VARS: none
##
##  Run poetry export to generate requirements.txt and requirements-dev.txt based on pyproject.toml.

python-pre-scan:

python-post-scan:

python-do-scan:
	@. $(PYTHON_SUPPORT) ; \
		pythonScan $(PYTHON_BUILD_TYPE)

python-scan: python-pre-scan python-do-scan python-post-scan  ## scan the Python artefact to the repository

## TARGET: python-scan
## SYNOPSIS: make python-scan
## HOOKS: python-pre-scan, python-post-scan
## VARS:
##       PYTHON_BUILD_TYPE=[tag_setup|non_tag_setup|non_tag_pyproject|tag_pyproject]
##
##  Scan python packages using Gemnasium.

# end of switch to suppress targets for help


python-exportlock: ## Exports runtime dependencies to requirements.txt file if needed
	poetry export --without-hashes -f requirements.txt --output requirements.txt
	poetry export --without-hashes --dev -f requirements.txt --output requirements-dev.txt


notebook-pre-format:

notebook-post-format:

notebook-do-format:
	$(PYTHON_RUNNER) nbqa isort --profile=black --line-length=$(PYTHON_LINE_LENGTH) $(PYTHON_SWITCHES_FOR_ISORT) $(NOTEBOOK_LINT_TARGET)
	$(PYTHON_RUNNER) nbqa black --line-length=$(PYTHON_LINE_LENGTH) $(PYTHON_SWITCHES_FOR_BLACK) $(NOTEBOOK_LINT_TARGET)

## TARGET: notebook-format
## SYNOPSIS: make notebook-format
## HOOKS: notebook-pre-format, notebook-post-format
## VARS:
##       PYTHON_RUNNER=<python executor> - defaults to empty, but could pass something like python -m
##       NOTEBOOK_LINT_TARGET=<file or directory path to Python code> - defaults to . (all notebooks in the repo)
##		 PYTHON_LINE_LENGTH=<line length> - defaults to 79, set it once and all linters will use this value
##       PYTHON_SWITCHES_FOR_ISORT=<additional switches to pass to isort>
##       PYTHON_SWITCHES_FOR_BLACK=<additional switch to pass to black>
##
##  Reformat Jupyter notebooks in the given directories/files using nbQa, black and isort.

notebook-format: notebook-pre-format notebook-do-format notebook-do-format


notebook-pre-lint:

notebook-post-lint:
	@. $(PYTHON_SUPPORT) ; \
		checkNotebookDir

notebook-do-lint:
	@mkdir -p build/reports;
	$(PYTHON_RUNNER) nbqa isort --check-only --profile=black --line-length=$(PYTHON_LINE_LENGTH) $(PYTHON_SWITCHES_FOR_ISORT) $(NOTEBOOK_LINT_TARGET)
	$(PYTHON_RUNNER) nbqa black --check --line-length=$(PYTHON_LINE_LENGTH) $(PYTHON_SWITCHES_FOR_BLACK) $(NOTEBOOK_LINT_TARGET)
	$(PYTHON_RUNNER) nbqa flake8 --show-source --statistics --max-line-length=$(PYTHON_LINE_LENGTH) $(PYTHON_SWITCHES_FOR_FLAKE8) $(NOTEBOOK_SWITCHES_FOR_FLAKE8) $(NOTEBOOK_LINT_TARGET)
	$(PYTHON_RUNNER) nbqa pylint --output-format=parseable --max-line-length=$(PYTHON_LINE_LENGTH) $(PYTHON_SWITCHES_FOR_PYLINT) $(NOTEBOOK_SWITCHES_FOR_PYLINT) $(NOTEBOOK_LINT_TARGET) | tee build/code_analysis.stdout
	$(PYTHON_RUNNER) nbqa pylint --output-format=pylint_junit.JUnitReporter:build/reports/linting-notebooks.xml --max-line-length=$(PYTHON_LINE_LENGTH) $(PYTHON_SWITCHES_FOR_PYLINT) $(NOTEBOOK_SWITCHES_FOR_PYLINT) $(NOTEBOOK_LINT_TARGET)
	@make --no-print-directory join-lint-reports

## TARGET: notebook-lint
## SYNOPSIS: make notebook-lint
## HOOKS: notebook-pre-lint, notebook-post-lint
## VARS:
##       PYTHON_RUNNER=<python executor> - defaults to empty, but could pass something like python -m
##       NOTEBOOK_LINT_TARGET=<file or directory path to notebooks> - defaults to . (all notebooks in the repo)
##		 PYTHON_LINE_LENGTH=<line length> - defaults to 79, set it once and all linters will use this value
##       PYTHON_SWITCHES_FOR_ISORT=<additional switches to pass to isort>
##       PYTHON_SWITCHES_FOR_BLACK=<additional switch to pass to black>
##       PYTHON_SWITCHES_FOR_FLAKE8=<additional switch to pass to flake8 for all python code>
##       PYTHON_SWITCHES_FOR_PYLINT=<additional switch to pass to pylint for all python code>
##       NOTEBOOK_SWITCHES_FOR_FLAKE8=<additional switch to pass to flake8 for notebooks>
##       NOTEBOOK_SWITCHES_FOR_PYLINT=<additional switch to pass to pylint for notebooks>
##
##  Lint check Jupyter notebooks in the given directories/files using nbQa, black, isort, flake8 and pylint.

notebook-lint: notebook-pre-lint notebook-do-lint notebook-post-lint ## Lint Jupyter notebooks


notebook-pre-test:

notebook-post-test:
	@. $(PYTHON_SUPPORT) ; \
		checkNotebookDir

notebook-do-test:
	@$(PYTHON_RUNNER) pytest --version -c /dev/null
	@mkdir -p build
	$(PYTHON_VARS_BEFORE_PYTEST) $(PYTHON_RUNNER) pytest --nbmake $(PYTHON_SWITCHES_FOR_NBMAKE) $(PYTHON_TEST_FOLDER_NBMAKE)

## TARGET: notebook-test
## SYNOPSIS: make notebook-test
## HOOKS: notebook-pre-test, notebook-post-test
## VARS:
##       PYTHON_RUNNER=<python executor> - defaults to empty, but could pass something like python -m
##       PYTHON_TEST_FOLDER_NBMAKE - defaults to . (all notebooks in the repo)
##       PYTHON_VARS_BEFORE_PYTEST=<environment variables defined before pytest in run> - default empty
##       NOTEBOOK_IGNORE_FILES - Notebook files to ignore. Defaults to "not notebook.ipynb".
##       PYTHON_SWITCHES_FOR_NBMAKE - Includes test folder and files to ignore
##
##  Run pytest --nbmake  against the notebooks defined in PYTHON_TEST_FOLDER_NBMAKE.  By default, this will pickup any jupyter notebooks

notebook-test: notebook-pre-test notebook-do-test notebook-post-test  ## test the Jupyter Notebook package


join-lint-reports: ## Join linting report (chart and python)
	@echo -e "<testsuites>\n</testsuites>" > build/reports/linting.xml; \
	for FILE in build/reports/linting-*.xml; do \
	TEST_RESULTS=$$(tr -d "\n" < $${FILE} | \
	sed -e "s/.*<testsuites[^<]*\(.*\)<\/testsuites>.*/\1/"); \
	TT=$$(echo $${TEST_RESULTS} | sed 's/\//\\\//g'); \
	echo "/<\/testsuites>/ s/.*/$${TT}\n&/" > build/reports/command; \
	sed -i.x -f build/reports/command -- build/reports/linting.xml; \
	rm -f build/reports/linting.xml.x; \
	rm -f build/reports/command; \
	done


# end of switch to suppress targets for help
endif
endif