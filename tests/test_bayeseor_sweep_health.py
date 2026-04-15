"""Tests for sweep health/status and validation CLIs."""

from __future__ import annotations

import json
from pathlib import Path

from valska.external_tools.bayeseor import (
    cli_sweep_status,
    cli_validate_sweep,
)


def _write_data_stats(path: Path) -> None:
    path.write_text(
        (
            "Nested Sampling Global Log-Evidence           : "
            "   1.000000000000000E+01  +/-    1.0E+00\n"
            "Nested Importance Sampling Global Log-Evidence: "
            "   9.900000000000000E+00  +/-    5.0E-02\n"
        ),
        encoding="utf-8",
    )


def _mk_complete_point(run_dir: Path) -> None:
    for hyp, mn in (
        ("signal_fit", "MN-signal"),
        ("no_signal", "MN-no-signal"),
    ):
        base = run_dir / "output" / hyp / mn
        base.mkdir(parents=True, exist_ok=True)
        (base / "data-.txt").write_text("chain\n", encoding="utf-8")
        _write_data_stats(base / "data-stats.dat")

    (run_dir / "manifest.json").write_text("{}", encoding="utf-8")
    (run_dir / "jobs.json").write_text("{}", encoding="utf-8")


def _mk_partial_point(run_dir: Path) -> None:
    signal = run_dir / "output" / "signal_fit" / "MN-signal"
    signal.mkdir(parents=True, exist_ok=True)
    (signal / "data-.txt").write_text("chain\n", encoding="utf-8")
    _write_data_stats(signal / "data-stats.dat")

    no_signal = run_dir / "output" / "no_signal" / "MN-no-signal"
    no_signal.mkdir(parents=True, exist_ok=True)
    _write_data_stats(no_signal / "data-stats.dat")

    (run_dir / "manifest.json").write_text("{}", encoding="utf-8")


def _mk_sweep(tmp_path: Path) -> Path:
    sweep_dir = tmp_path / "_sweeps" / "sweep_health"
    point_ok = sweep_dir / "validation" / "antdiam_0.0e+00"
    point_partial = sweep_dir / "validation" / "antdiam_1.0e-02"

    _mk_complete_point(point_ok)
    _mk_partial_point(point_partial)

    manifest = {
        "run_id": "sweep_health",
        "beam_model": "airy_diam14m",
        "sky_model": "GSM_plus_GLEAM",
        "points": [
            {
                "perturb_parameter": "antenna_diameter",
                "perturb_frac": 0.0,
                "run_label": "antdiam_0.0e+00",
                "run_dir": str(point_ok),
            },
            {
                "perturb_parameter": "antenna_diameter",
                "perturb_frac": 0.01,
                "run_label": "antdiam_1.0e-02",
                "run_dir": str(point_partial),
            },
        ],
    }
    sweep_dir.mkdir(parents=True, exist_ok=True)
    (sweep_dir / "sweep_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    return sweep_dir


def test_cli_sweep_status_json(tmp_path: Path, capsys) -> None:
    sweep_dir = _mk_sweep(tmp_path)

    code = cli_sweep_status.main([str(sweep_dir), "--json"])
    assert code == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["sweep_status"] == "partial"
    assert payload["points_total"] == 2
    assert payload["points_ok"] == 1
    assert payload["points_partial"] == 1


def test_cli_validate_sweep_fails_without_allow_partial(
    tmp_path: Path, capsys
) -> None:
    sweep_dir = _mk_sweep(tmp_path)

    code = cli_validate_sweep.main([str(sweep_dir)])
    assert code == 1
    assert "Sweep status is 'partial'" in capsys.readouterr().out


def test_cli_validate_sweep_allow_partial_but_require_jobs_json(
    tmp_path: Path, capsys
) -> None:
    sweep_dir = _mk_sweep(tmp_path)

    code = cli_validate_sweep.main(
        [str(sweep_dir), "--allow-partial", "--require-jobs-json", "--json"]
    )
    assert code == 1

    payload = json.loads(capsys.readouterr().out)
    assert payload["validation"]["exit_code"] == 1
    assert any(
        "Missing jobs.json" in msg for msg in payload["validation"]["failures"]
    )


def test_cli_validate_sweep_allow_partial_passes(tmp_path: Path) -> None:
    sweep_dir = _mk_sweep(tmp_path)
    code = cli_validate_sweep.main([str(sweep_dir), "--allow-partial"])
    assert code == 0
