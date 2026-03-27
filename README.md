# ValSKA-HERA-beam-FWHM

**An open-source, reproducible, flexible, and extensible package for validating the sensitivity of 21-cm power spectrum forward modeling approaches to imperfect knowledge of the FWHM of the interferometric primary beam.**

## Overview

ValSKA-HERA-beam-FWHM provides a Bayesian science validation case study modelling the Hydrogen Epoch of Reionization Array (HERA) using the BayesEoR modeling framework.

## Features

- **Bayesian Analysis**: BayesEoR enables a joint Bayesian analysis of models for large-spectral-scale foreground emission and a stochastic signal from redshifted 21-cm emission emitted by neutral Hydrogen during the Epoch of Reionization (EoR).
- **Sensitivity Testing**: This package tests the extent to which errors in beam modelling, parameterized in terms of the beam FWHM, can be tolerated without biasing the recovery of the 21-cm power spectrum.

## Contents

ValSKA-HERA-beam-FWHM includes:
- Results from **BaNTER** (Bayesian Null-Test Evidence Ratio) validation of the forward modelling pipeline.
- Chain files from **BayesEoR** power spectrum estimation analysis of mock HERA foreground validation data and full-sky (foregrounds + 21-cm signal) science data.
- Links to data artifacts.

## Installation

*TBD: Instructions for installation.*

 - Clone the repo.
 - All dependencies can be installed with `conda` using the included `valska_env_base.yaml` and `valska_env_gpu.yaml` files via (but see below first):
```
conda env create -f valska_env_base.yaml
conda activate valska
conda env update -f valska_env_gpu.yaml
```
 - in `valska_env_gpu.yaml`, select `cuda` or `cudatoolkit` depending on your system (e.g. Azimuth vs Galahad).


## Usage

*TBD: Instructions for usage, including examples.*

## Documentation

The documentation is hosted on [ReadTheDocs](https://valska-hera-beam-fwhm.readthedocs.io/en/latest/).

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

We use pre-commit hooks to ensure code quality and consistency - please see the [Guide to Contributing](https://valska-hera-beam-fwhm.readthedocs.io/en/latest/contributing.html) for further information about setting up and using pre-commit.


For any additional questions or comments, please contact one of the UKSRC science validation tooling team:
 - Peter Sims (PO) - ps550 [at] cam.ac.uk
 - Tianyue Chen (SM) - tianyue.chen [at] manchester.ac.uk
 - Quentin Gueuning - qdg20 [at] cam.ac.uk
 - Ed Polehampton - edward.polehampton [at] stfc.ac.uk
 - Vlad Stolyarov - vs237 [at] cam.ac.uk
