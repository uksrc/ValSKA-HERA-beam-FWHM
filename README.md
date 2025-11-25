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
 - All dependencies can be installed with `conda` using the included `valska_env.yaml` file via (but see below first):
```
conda env create -f valska_env.yaml
```
 - valska_env.yaml is setup for Galahad. To install the dependencies on Azimuth, in valska_env.yaml, comment out cudatoolkit and uncomment cuda.


## Usage

*TBD: Instructions for usage, including examples.*

## Documentation

The documentation is hosted on [ReadTheDocs](https://valska-hera-beam-fwhm.readthedocs.io/en/latest/).

## Contributing

ValSKA-HERA-beam-FWHM is an open source project and contributions to this package in any form are very welcome (e.g. new features, feature requests, bug reports, documentation fixes). Please make such contributions in the form of an issue and/or pull request.

When creating a pull request, please use the provided pull request template which includes a checklist to ensure:
- Self-review of code
- Local tests pass (`make python-test` and `make notebook-test`)
- Relevant documentation is updated

### Branch Protection (Maintainers)

To enforce CI checks on pull requests, repository maintainers should configure [branch protection rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/defining-the-mergeability-of-pull-requests/using-branch-protection-rules) on the `main` branch:

1. Go to **Settings** > **Branches** > **Add branch protection rule**
2. Set **Branch name pattern** to `main`
3. Enable **Require status checks to pass before merging**
4. Select the required status checks (e.g., the `build` job from the CI workflow)
5. Optionally enable **Require pull request reviews before merging**

For any additional questions or comments, please contact one of the UKSRC science validation tooling team:
 - Peter Sims (PO) - ps550 [at] cam.ac.uk
 - Tianyue Chen (SM) - tianyue.chen [at] manchester.ac.uk
 - Quentin Gueuning - qdg20 [at] cam.ac.uk
 - Ed Polehampton - edward.polehampton [at] stfc.ac.uk
 - Vlad Stolyarov - vs237 [at] cam.ac.uk
