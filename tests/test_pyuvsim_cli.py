"""
Unit tests for the pyuvsim CLI integration wrappers.

The tests are focused on control-flow and error handling rather than full end-to-end execution.
"""

import json
from pathlib import Path

import pytest

from valska.external_tools.pyuvsim import (
    cli_prepare,
    cli_submit,
)
from valska.external_tools.pyuvsim import submit as submit_mod


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
    script_name = "submit_simulate.sh"
    (run_dir / script_name).write_text("#!/bin/bash\n", encoding="utf-8")
    manifest = {
        "artefacts": {"submit_sh_simulate": script_name},
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )


class TestCLIPrepare:
    def test_cli_prepare_missing_beam_sky_returns_2(self):
        """
        The prepare subcommand requires precomputed beam/sky products. When those
        inputs are missing we expect the CLI to return exit code 2, indicating
        a missing prerequisite.
        """
        code = cli_prepare.main(["--run-id", "r001", "--dry-run"])
        assert code == 2

        code = cli_prepare.main(
            ["--beam", "achromatic_Gaussian", "--run-id", "r001", "--dry-run"]
        )
        assert code == 2

        code = cli_prepare.main(
            ["--sky", "GLEAM", "--run-id", "r001", "--dry-run"]
        )
        assert code == 2

    def test_cli_prepare_quits_with_bad_arguments(self, capsys):
        with pytest.raises(SystemExit):
            cli_prepare.main(
                ["--argument-that-does-not-exist", "12312 --test"]
            )

        assert "usage:" in capsys.readouterr().err


class TestCLISubmit:
    def test_cli_submit_missing_manifest_returns_1(self, tmp_path):
        """
        Submitting from a run directory without a manifest.json should fail early.
        """
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        code = cli_submit.main([str(run_dir), "--dry-run"])
        assert code == 1

    def test_cli_submit_record_manifest_returns_2(self, tmp_path):
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
        code = cli_submit.main(
            [str(run_dir), "--record", "manifest", "--dry-run"]
        )
        assert code == 2

    def test_cli_submit_sbatch_failure_returns_4(self, tmp_path, monkeypatch):
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
        code = cli_submit.main([str(run_dir)])
        assert code == 4

    def test_cli_submit_quits_with_bad_arguments(self, capsys):
        with pytest.raises(SystemExit):
            cli_submit.main(["--argument-that-does-not-exist", "12312 --test"])

        assert "usage:" in capsys.readouterr().err

    def test_cli_submit_fails_with_empty_run_directory(self, tmp_path):
        run_dir = tmp_path / "run"
        run_dir.mkdir()

        code = cli_submit.main([str(run_dir), "--dry-run"])

        assert code != 0
