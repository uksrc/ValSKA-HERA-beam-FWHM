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

- The simulation parameters for the pyuvsim run are specified by the `--template` argument. If this is not present, the default reference template is used (`external_tools/pyuvsim/templates/fov-19.4-oscar-sm.yml`).

- The simulation parameters template must contain valid paths to the sky catalogue and telescope parameters:
  - `sources.catalog` (e.g. GLEAM skyh5 file)
  - `telescope.array_layout` (e.g. `hex-37-14.6m.csv`)
  - `telescope.telescope_config_name` (e.g. `hex-37-14.6m-gauss-fwhm9.3.yml`)

- Make sure all paths referenced by the template file are valid on the filesystem visible to the compute nodes.

### Minimal first run

This minimal first run uses the default simulation parameter template (located in the repository at `external_tools/pyuvsim/templates/`) to produce a reference simulation, with additional beam check simulation and logs.

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
### Beam check

A beam check simulation is calculated as a separate job after the main simulation is completed. This uses a minimal catalogue with a single point source that passes zenith at the telescope latitude at the mid-point of the observation. {ref}`Beam metrics <beam-metrics>` checks are performed on the beam check simulation to verify the beam shape used for the main simulation. The results of the beam check are stored in a log file and plots that give the fitted beam and its variation with frequency.

The beam check is enabled by default, and sets up a simulation to observe a single 1 Jy source 2 hours either side of transit, with a time step of 10 seconds. All autocorrelation baselines are simulated.

### Run directory and outputs

The `run_dir` is where configuration, slurm scripts, tracking files and outputs are collected. It is constructed as follows:

`<results_root>/pyuvsim/<beam_model>/<sky_model>/<variant>/<run_label>/<run_id>/`

The output simulation is saved as a uvh5 file in the run directory in a sub-directory as specified in the pyuvsim configuration file.
The beam check simulation, logs and plots are also saved into the same output directory.


## Definitions

- a run is one pyuvsim simulation, controlled from the run directory
- a run directory contains the pyuvsim configuration, Slurm submit script, manifest, and later `jobs.json` and the outputs
- the simulate stage is the pyuvsim execution stage that generates simulated visibility data, written out to the results directory specified in `runtime_paths.yaml`.
- `manifest.json` records what ValSKA prepared
- `jobs.json` records what ValSKA submitted to Slurm
- beamcheck is a second simulation lauched to verify the beamshape - it uses a minimal catalogue with a single source that passes zenith at the mid-point of the observation

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
- writes a Slurm submit script for the `beamcheck` stage
- prints suggested next steps

### Common options

`--beam`

Beam / instrument model label (e.g. achromatic_Gaussian). This is a mandatory parameter. It is used only to set the output directory path.

`--sky`

Sky model label (e.g. GLEAM, GSM, GLEAM_plus_GSM). This is a mandatory parameter. It is used only to set the output directory path.

`--template`

Name and path of pyuvsim simulation parameter yaml file. If not specified, the default template will be used.

`--run-id`

User-facing identifier for this simulation run.

`--results-root`

Optional override for the results root configured in `runtime_paths.yaml`.

`--dry-run`

Preview resolved paths and configuration without creating files.

`--no-beamcheck`

Disable the additional beamcheck simulation and tests.

`--beamcheck-hours`

Set the duration in hours either side of transit for the beam check simulation.

`--beamcheck-step_seconds`

Set the time step in seconds for the beam check simulation.

## valska-pyuvsim-submit

This command:

- validates that the run directory was prepared by ValSKA
- reads `manifest.json`
- submits the `submit_simulate.sh` script to Slurm
- submits the `submit_beamcheck.sh` script to Slurm
- writes `jobs.json` with the submitted job ID and command
- supports dry-run submission previews

### Common options

`--dry-run`

Preview `sbatch` command without submitting any jobs.

`--resubmit`

When `--resubmit` is used, ValSKA should preserve the previous submission record before writing a new `jobs.json`.
