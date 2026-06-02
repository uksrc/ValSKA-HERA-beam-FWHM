# pyuvsim CLI workflows (ValSKA)

## Quick Start

### Setup

Before trying the workflow examples below, make sure you have completed the setup below:

- ValSKA setup:
  - [install the ValSKA environment](../readme.rst#installation) so the `valska-pyuvsim-*` CLI commands are available

- pyuvsim setup:
    - clone pyuvsim locally in a location you control from [the repository on GitHub](https://github.com/RadioAstronomySoftwareGroup/pyuvsim) (`git clone https://github.com/RadioAstronomySoftwareGroup/pyuvsim`)
    - run the next few commands from inside the cloned repository (`cd pyuvsim`)
    - create the pyuvsim conda environment using the environment file to include its dependencies (`mamba env create -f environment.yml`)
    - activate the conda environment (`mamba activate pyuvsim`)
    - install pyuvsim inside the conda environment (`pip install .`)

- ValSKA runtime configuration:
  - copy `config/runtime_paths.example.yaml` to `config/runtime_paths.yaml` in your ValSKA repository
  - edit `config/runtime_paths.yaml` for your system:
    - set `results_root`
    - set the `pyuvsim` conda environment configuration and `conda_sh` file location
    - set any site-level Slurm defaults required by your cluster in `pyuvsim.slurm_defaults`

- Input configuration:
  - create or obtain the pyuvsim template file you want to use for the `--template` flag
  - make sure all paths referenced by the pyuvsim template file are valid on the filesystem visible to the compute nodes

### Minimal first run

After activating the ValSKA environment, run:

```bash
valska-pyuvsim-prepare \
  --beam achromatic_Gaussian \
  --sky GLEAM \
  --template "/path/to/pyuvsim_template.yml" \
  --run-id r001 \
  --dry-run
```

If the paths are okay, you can create the run directory:

```bash
valska-pyuvsim-prepare \
  --beam achromatic_Gaussian \
  --sky GLEAM \
  --template "/path/to/pyuvsim_template.yml" \
  --run-id r001 \
```

After checking the Slurm script `submit_simulate.sh` looks okay, submit the simulation:

```bash
valska-pyuvsim-submit /path/to/run_dir
```

## Definitions

- a run is one prepared pyuvsim simulation directory
- a run directory contains the pyuvsim configuration, Slurm submit script, manifest, and later `jobs.json`
- the simulate stage is the pyuvsim execution stage that generates simulated visibility data
- `manifest.json` records what ValSKA prepared
- `jobs.json` records what ValSKA submitted to Slurm

## Which command should I use?

Need to create a pyuvsim run directory and submit script?

```bash
valska-pyuvsim-prepare
```

Need to check what would be created without writing files?

```bash
valska-pyuvsim-prepare --dry-run
```

Need to submit a prepared pyuvsim run to Slurm?

```bash
valska-pyuvsim-submit /path/to/run_dir
```

Need to preview the `sbatch` command without submitting?

```bash
valska-pyuvsim-submit /path/to/run_dir --dry-run
```

Need to resubmit a run that already has a `jobs.json`?

```bash
valska-pyuvsim-submit /path/to/run_dir --resubmit
```

## valska-pyuvsim-prepare

This command:

- resolves ValSKA runtime configuration
- creates a pyuvsim run directory
- copies or renders the pyuvsim template YAML
- writes `manifest.json`
- writes a Slurm submit script for the `simulate` stage
- prints suggested next steps

### Common options

`--beam`

Beam / instrument model label (e.g. achromatic_Gaussian).

`--sky`

Sky model label (e.g. GLEAM, GSM, GLEAM_plus_GSM).

`--template`

Template name shipped with ValSKA, or a file system path to a template YAML.

`--run-id`

User-facing identifier for this simulation run.

`--results-root`

Optional override for the results root configured in `runtime_paths.yaml`.

`--dry-run`

Preview resolved paths and configuration without creating files.

## valska-pyuvsim-submit

This command:

- validates that the run directory was prepared by ValSKA
- reads `manifest.json`
- submits the `submit_simulate.sh` script to Slurm
- writes `jobs.json` with the submitted job ID and command
- supports dry-run submission previews

### Common options

`--dry-run`

Preview `sbatch` command without submitting any jobs.

`--resubmit`

When `--resubmit` is used, ValSKA should preserve the previous submission record before writing a new `jobs.json`.
