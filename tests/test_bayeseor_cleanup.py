"""Tests for valska-bayeseor-cleanup CLI."""

from __future__ import annotations

import json
from pathlib import Path

from valska_hera_beam.external_tools.bayeseor import cli_cleanup


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


def _mk_missing_point(run_dir: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)


def _mk_sweep(results_root: Path, run_id: str) -> tuple[Path, Path, Path]:
    sweep_dir = (
        results_root
        / "bayeseor"
        / "airy_diam14m"
        / "GSM_plus_GLEAM"
        / "_sweeps"
        / run_id
    )
    point_ok = sweep_dir / "validation" / "antdiam_0.0e+00"
    point_missing = sweep_dir / "validation" / "antdiam_1.0e-02"

    _mk_complete_point(point_ok)
    _mk_missing_point(point_missing)

    (point_ok / "slurm-123.out").write_text("log\n", encoding="utf-8")
    (point_ok / "worker.log").write_text("log\n", encoding="utf-8")
    (point_ok / "tmp").mkdir(exist_ok=True)
    (point_ok / "tmp" / "scratch.tmp").write_text("tmp\n", encoding="utf-8")

    manifest = {
        "run_id": run_id,
        "beam_model": "airy_diam14m",
        "sky_model": "GSM_plus_GLEAM",
        "created_utc": "2026-02-27T00:00:00Z",
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
                "run_dir": str(point_missing),
            },
        ],
    }
    sweep_dir.mkdir(parents=True, exist_ok=True)
    (sweep_dir / "sweep_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    return sweep_dir, point_ok, point_missing


def test_cleanup_dry_run_plans_actions(tmp_path: Path, capsys) -> None:
    results_root = tmp_path / "results"
    _, point_ok, point_missing = _mk_sweep(results_root, "sweep_cleanup")

    code = cli_cleanup.main(
        [
            "--results-root",
            str(results_root),
            "--prune-logs",
            "--prune-temp",
            "--prune-runs",
            "--run-status",
            "missing",
            "--json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["execute"] is False
    assert payload["summary"]["planned_count"] >= 3
    assert any(
        row["scope"] == "run_dir" and row["path"] == str(point_missing)
        for row in payload["actions"]
    )
    assert (point_ok / "slurm-123.out").exists()
    assert point_missing.exists()


def test_cleanup_color_always(tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    results_root = tmp_path / "results"
    _mk_sweep(results_root, "sweep_cleanup")

    code = cli_cleanup.main(
        [
            "--results-root",
            str(results_root),
            "--prune-logs",
            "--color",
            "always",
        ]
    )
    assert code == 0

    out = capsys.readouterr().out
    assert "\x1b[" in out
    assert "Sweep cleanup summary:" in out
    assert "Actions:" in out


def test_cleanup_execute_prune_runs_requires_confirm(
    tmp_path: Path, capsys
) -> None:
    results_root = tmp_path / "results"
    _mk_sweep(results_root, "sweep_cleanup")

    code = cli_cleanup.main(
        [
            "--results-root",
            str(results_root),
            "--prune-runs",
            "--execute",
        ]
    )
    assert code == 2
    assert "requires --confirm-runs DELETE" in capsys.readouterr().err


def test_cleanup_execute_moves_to_trash(tmp_path: Path, capsys) -> None:
    results_root = tmp_path / "results"
    _, _, point_missing = _mk_sweep(results_root, "sweep_cleanup")

    code = cli_cleanup.main(
        [
            "--results-root",
            str(results_root),
            "--prune-runs",
            "--run-status",
            "missing",
            "--execute",
            "--confirm-runs",
            "DELETE",
            "--json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["execute"] is True
    assert payload["summary"]["moved_count"] == 1
    assert not point_missing.exists()
    moved_rows = [
        row
        for row in payload["actions"]
        if row["scope"] == "run_dir" and row["status"] == "moved"
    ]
    assert len(moved_rows) == 1
    target = Path(str(moved_rows[0]["target_path"]))
    assert target.exists()
