# pyuvsim CLI workflows (ValSKA)

This page is a practical, “example gallery”-style guide to running [pyuvsim](https://pyuvsim.readthedocs.io/en/latest/index.html) using ValSKA.

## Quick Start

### Setup

Before trying the workflow examples below, make sure you have completed the setup below:

ValSKA setup:

- [Install the ValSKA environment](../readme.rst#installation) so the `valska-pyuvsim-*` CLI commands are available

pyuvsim setup:

  - clone pyuvsim locally in a location you control from [the repository on GitHub](https://github.com/RadioAstronomySoftwareGroup/pyuvsim) (`git clone https://github.com/RadioAstronomySoftwareGroup/pyuvsim`)
  - run the next few commands from inside the cloned repository (`cd pyuvsim`)
    - create a pyuvsim virtual environment, e.g. using the environment yaml file to include its dependencies (see [pyuvsim installation documentation](https://pyuvsim.readthedocs.io/en/latest/index.html#developer-installation))
    - activate the virtual environment (e.g. `conda activate pyuvsim`)
    - install pyuvsim inside the virtual environment (`pip install .`)

ValSKA runtime configuration:

- copy `config/runtime_paths.example.yaml` to `config/runtime_paths.yaml` in your ValSKA repository
- edit `config/runtime_paths.yaml` for your system:
  - set `results_root` - this sets the root directory for all of the pyuvsim runs
  - set the `pyuvsim` conda environment configuration and `conda_sh` file location
  - set any site-level Slurm defaults required by your cluster in `pyuvsim.slurm_defaults`

pyuvsim input configuration:

The simulation parameters for the pyuvsim run are specified by the `--template` argument. If this is not present, the internal reference template is used (`external_tools/pyuvsim/templates/fov-19.4-oscar-sm.yml`).

The simulation parameters template must contain valid paths to the telescope parameters and sky catalogue:

- telescope params:
  - location and beam (e.g. `hex-37-14.6m-gauss-fwhm9.3.yml`)
  - array layout (e.g. `hex-37-14.6m.csv`)
- sky catalogue (e.g. GLEAM skyh5 file)

Make sure all paths referenced by the template file are valid on the filesystem visible to the compute nodes.

### Minimal first run

This minimal first run uses the default simulation parameter template (located in the repository at `external_tools/pyuvsim/templates/`) to produce a reference simulation.

After activating the ValSKA environment, run:

```bash
valska-pyuvsim-prepare \
  --beam achromatic_Gaussian \
  --sky GLEAM \
  --run-id r001 \
  --dry-run
```

If the paths are okay, you can create the files for real by running the same command without `--dry-run`.

In order to replace the reference template with your own simulation parameters, add 

```bash
  --template "/path/to/pyuvsim_parameters.yml" \
```

In order to submit the Slurm script that was created in the prepare command (`submit_simulate.sh` located in the run directory):

```bash
valska-pyuvsim-submit /path/to/run_dir
```


## Definitions

- a run is one pyuvsim simulation, controlled from the run directory
- a run directory contains the pyuvsim configuration, Slurm submit script, manifest, and later `jobs.json`
- the simulate stage is the pyuvsim execution stage that generates simulated visibility data, written out to the results directory specified in `runtime_paths.yaml`.
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

Beam / instrument model label (e.g. achromatic_Gaussian). This is a mandatory parameter. It is used only to set the output directory path.

`--sky`

Sky model label (e.g. GLEAM, GSM, GLEAM_plus_GSM). This is a mandatory parameter. It is used only to set the output directory path.

`--template`

Name and path of pyuvsim simulation parameter yaml file. If not specified, the internal template will be used.

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
