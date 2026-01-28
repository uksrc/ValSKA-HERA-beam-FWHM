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

**Detailed usage examples, expected outputs, and recovery patterns are documented separately.**

---

## Documentation

Documentation is hosted on [ReadTheDocs](https://valska-hera-beam-fwhm.readthedocs.io/en/latest/).

Detailed command-line examples and workflow patterns are provided in:

- [BayesEoR CLI examples](https://valska-hera-beam-fwhm.readthedocs.io/en/latest/workflows/bayeseor_cli_examples.html)

That document is the primary reference for:
- Preparing validation sweeps
- Submitting CPU and GPU stages
- Partial submission and recovery
- Resubmission after walltime
- Inspecting manifests and job records

## Contributing

ValSKA-HERA-beam-FWHM is an open-source project, and contributions of all kinds are very welcome
(e.g. feature requests, bug reports, documentation improvements, or new validation studies).

Please contribute via GitHub issues and/or pull requests.

For questions or discussion, contact the UKSRC science-validation tooling team:

- **Peter Sims** (Product Owner) — ps550 [at] cam.ac.uk
- **Tianyue Chen** (Scrum Master) — tianyue.chen [at] manchester.ac.uk
- **Quentin Gueuning** — qdg20 [at] cam.ac.uk
- **Ed Polehampton** — edward.polehampton [at] stfc.ac.uk
- **Vlad Stolyarov** — vs237 [at] cam.ac.uk
