# ValSKA-HERA-beam-FWHM

**An open-source, reproducible, flexible, and extensible package for validating the sensitivity of 21-cm power-spectrum inference to imperfect knowledge of the interferometric primary-beam FWHM.**

---

## Overview

ValSKA-HERA-beam-FWHM provides a Bayesian science-validation case study for the Hydrogen Epoch of Reionization Array (HERA), using the **BayesEoR** modelling framework.

The focus of this repository is **validation tooling**: enabling controlled, inspectable, and reproducible studies of how modelling assumptions — here, uncertainty in the primary-beam full width at half maximum (FWHM) — propagate through a full 21-cm power-spectrum inference pipeline.

This repository is developed as part of the UK Square Kilometre Array Regional Centre (UKSRC) science-validation effort.

---

## Features

- **Bayesian 21-cm inference**
  Uses BayesEoR to perform joint Bayesian modelling of spectrally smooth foreground emission and a stochastic 21-cm signal from the Epoch of Reionization.

- **Instrumental sensitivity validation**
  Quantifies the robustness of inferred 21-cm power spectra to controlled perturbations in the assumed primary-beam FWHM.

- **Reproducible HPC workflows**
  Explicit separation of run preparation, CPU precompute, and GPU inference stages enables resumable, auditable, and HPC-appropriate execution.

---

## Contents

ValSKA-HERA-beam-FWHM includes:

- Validation results from **BaNTER** (Bayesian Null-Test Evidence Ratio) analyses
- BayesEoR chain files from mock HERA foreground-only and foreground-plus-signal datasets
- Full provenance records for all validation runs
- Command-line tooling for preparing, submitting, and managing ensembles of BayesEoR runs

---

## Installation

General guidance:

- Clone the repository
- Install dependencies using `conda` or `mamba` with the supplied environment file:

    conda env create -f valska_env.yaml

- `valska_env.yaml` is configured for **Galahad** by default
  For **Azimuth**, comment out `cudatoolkit` and uncomment `cuda` in the environment file

**Note:**
This repository provides *validation tooling and job orchestration*.
It does **not** automatically create conda environments, clone BayesEoR, or manage HPC accounts.

---

## BayesEoR validation workflow (high-level)

This repository supports **reproducible, sweep-based validation studies** in which BayesEoR analyses are repeated across multiple controlled FWHM perturbations.

At a high level, the workflow is:

- Define a validation sweep over beam FWHM
- Prepare self-contained BayesEoR run directories
- Submit CPU and GPU stages with explicit dependencies
- Inspect, resume, or extend runs as needed

The recommended user interface for this workflow is the `valska-bayeseor-sweep` command, which builds on lower-level `prepare` and `submit` tooling.

For post-processing, `valska-bayeseor-report` can be run on any existing sweep directory to generate summary tables and evidence comparison plots retroactively.

**Detailed usage examples, expected outputs, and recovery patterns are documented separately.**

---

## Documentation

Documentation is hosted on [ReadTheDocs](https://valska-hera-beam-fwhm.readthedocs.io/en/latest/).

Detailed command-line examples and workflow patterns are provided in:

- [BayesEoR CLI examples](https://valska-hera-beam-fwhm.readthedocs.io/en/latest/workflows/bayeseor_cli_examples.html)
- [BayesEoR reporting workflows](https://valska-hera-beam-fwhm.readthedocs.io/en/latest/workflows/bayeseor_reporting.html)

That document is the primary reference for:
- Preparing validation sweeps
- Submitting CPU and GPU stages
- Partial submission and recovery
- Resubmission after walltime
- Inspecting manifests and job records

## Testing

For comprehensive testing instructions, see the [Testing Guide](https://valska-hera-beam-fwhm.readthedocs.io/en/latest/testing.html).


## Contributing

ValSKA-HERA-beam-FWHM is an open source project and contributions to this package in any form are very welcome (e.g. new features, feature requests, bug reports, documentation fixes). Please make such contributions in the form of an issue and/or pull request.

When creating a pull request, please use the provided pull request template which includes a checklist to ensure:
- Self-review of code
- Local tests pass (`make python-test` and `make notebook-test`)
- Relevant documentation is updated

In order to enforce CI checks on pull requests, branch protection rules are in place on the `main` branch to:

- Require status checks to pass before merging
- Require pull request reviews before merging

For any additional questions or comments, please contact one of the UKSRC science validation tooling team:
 - Peter Sims (PO) - ps550 [at] cam.ac.uk
 - Tianyue Chen (SM) - tianyue.chen [at] manchester.ac.uk
 - Quentin Gueuning - qdg20 [at] cam.ac.uk
 - Ed Polehampton - edward.polehampton [at] stfc.ac.uk
 - Vlad Stolyarov - vs237 [at] cam.ac.uk
