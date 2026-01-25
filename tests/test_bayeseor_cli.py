"""
Unit tests for the BayesEoR CLI integration wrappers.

This module exercises the small CLI wrapper entry-points that coordinate
preparation, sweeping and submission of BayesEoR jobs. The tests are focused
on control-flow and error handling rather than full end-to-end execution.
They rely on pytest's tmp_path for filesystem isolation and monkeypatch to
replace system interactions (for example, calls to the scheduler).

Exit codes asserted here (documented as they are used across the tests):
- 2: Missing required inputs or preconditions (e.g. missing beam/sky products
     or an expected recording operation cannot proceed).
- 3: Missing manifest.json in a run directory when attempting to submit.
- 4: Failure when invoking the scheduler (simulated sbatch failure).

Notes on testing techniques used:
- Use tmp_path to create per-test temporary directories/files so tests are
  filesystem-independent and isolated.
- Use monkeypatch.setattr to stub/replace functions inside the module under
  test. Patch the symbol where the code under test will look it up (the
  attribute on the module object used by the CLI), not necessarily where it
  was originally defined.
- The tests purposefully avoid running external processes; instead we emulate
  error conditions and validate that the CLI returns the correct exit codes.
"""

import json
from pathlib import Path

import pytest

from valska_hera_beam.external_tools.bayeseor import (
    cli_prepare,
    cli_submit,
    cli_sweep,
)
from valska_hera_beam.external_tools.bayeseor import submit as submit_mod


def _write_minimal_manifest(run_dir: Path) -> None:
    """
    Create a minimal manifest and a stub submit shell script.

    The submit CLI expects a manifest.json inside the run directory that
    references an artefact containing a submit script.  This helper creates:
      - a trivial executable shell script file named "submit_cpu_precompute.sh"
      - a manifest.json with the minimal keys required by the submit CLI for
        the tests:
          - artefacts.submit_sh_cpu_precompute -> script filename
          - bayeseor.cpu_precompute_driver_hypothesis -> example string

    Tests do not execute the script; its presence in the manifest is enough
    for the CLI code paths exercised here.
    """
    script_name = "submit_cpu_precompute.sh"
    (run_dir / script_name).write_text("#!/bin/bash\n", encoding="utf-8")
    manifest = {
        "artefacts": {"submit_sh_cpu_precompute": script_name},
        "bayeseor": {"cpu_precompute_driver_hypothesis": "signal_fit"},
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )


def test_cli_prepare_missing_beam_sky_returns_2():
    """
    The prepare subcommand requires precomputed beam/sky products. When those
    inputs are missing we expect the CLI to return exit code 2, indicating
    a missing prerequisite.
    """
    code = cli_prepare.main(["--data", "input.uvh5", "--run-id", "r001"])
    assert code == 2


def test_cli_sweep_missing_beam_sky_returns_2():
    """
    The sweep subcommand similarly requires beam/sky inputs. This test calls
    sweep with a non-existent data file; the expected behavior is to return
    exit code 2 (missing required inputs).
    """
    code = cli_sweep.main(
        ["--data", "input.uvh5", "--run-id", "r001", "--dry-run"]
    )
    assert code == 2


def test_cli_submit_missing_manifest_returns_3(tmp_path):
    """
    Submitting from a run directory without a manifest.json should fail early
    with exit code 3 (manifest missing).
    """
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    code = cli_submit.main([str(run_dir), "--dry-run"])
    assert code == 3


def test_cli_submit_record_manifest_returns_2(tmp_path):
    """
    Requesting a 'record' operation (here 'manifest') when necessary preconditions
    for recording are not met should return exit code 2. This test writes a
    minimal manifest so the CLI can locate a manifest file, but the current
    implementation treats this particular record invocation as returning code 2.
    The test documents and protects that behavior against regressions.
    """
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    _write_minimal_manifest(run_dir)
    code = cli_submit.main([str(run_dir), "--record", "manifest", "--dry-run"])
    assert code == 2


def test_cli_submit_sbatch_failure_returns_4(tmp_path, monkeypatch):
    """
    Simulate a scheduler submission failure and verify the submit CLI surface
    reports a submission error via exit code 4.

    Implementation detail:
    - submit_mod._run_sbatch is the internal helper that would invoke the
      system's "sbatch" to schedule a job. Replace it with a stub that
      raises submit_mod.SbatchError to emulate a failed submission.
    - monkeypatch.setattr ensures the original function is restored after the
      test finishes.
    """
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    _write_minimal_manifest(run_dir)

    def _raise_sbatch(*_args, **_kwargs):
        # Emulate a scheduler failure (sbatch error)
        raise submit_mod.SbatchError("boom")

    # Replace the real sbatch invocation with the failing stub. Tests should
    # observe that the CLI returns the expected failure code (4).
    monkeypatch.setattr(submit_mod, "_run_sbatch", _raise_sbatch)
    code = cli_submit.main([str(run_dir), "--stage", "cpu"])
    assert code == 4
