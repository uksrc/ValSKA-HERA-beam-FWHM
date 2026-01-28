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

First, clone the repo.

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

Development and other specific dependencies are specified separately in `pyproject.toml`, and are automatically installed into the conda environment using pip. This is carried out in the last section of `valska_env.yaml` - i.e.:

```bash
  - pip:
      - -e .[dev] # editable-installs valska and all deps from pyproject.toml
```


## Usage

*TBD: Instructions for usage, including examples.*

## Documentation

The documentation is hosted on [ReadTheDocs](https://valska-hera-beam-fwhm.readthedocs.io/en/latest/).

## Testing

For comprehensive testing instructions, see:
- [Testing Documentation](https://valska-hera-beam-fwhm.readthedocs.io/en/latest/testing.html)

Quick start:
```bash
# Install dependencies
conda env create -f valska_env.yaml
conda activate valska

# Run tests
make python-test      # Unit tests
make notebook-test    # Notebook validation
```

## Contributing

ValSKA-HERA-beam-FWHM is an open source project and contributions to this package in any form are very welcome (e.g. new features, feature requests, bug reports, documentation fixes). Please make such contributions in the form of an issue and/or pull request. For any additional questions or comments, please contact one of the UKSRC science validation tooling team:
 - Peter Sims (PO) - ps550 [at] cam.ac.uk
 - Tianyue Chen (SM) - tianyue.chen [at] manchester.ac.uk
 - Quentin Gueuning - qdg20 [at] cam.ac.uk
 - Ed Polehampton - edward.polehampton [at] stfc.ac.uk
 - Vlad Stolyarov - vs237 [at] cam.ac.uk
