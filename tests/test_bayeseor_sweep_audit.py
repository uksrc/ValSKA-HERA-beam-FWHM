"""Tests for aggregate sweep audit CLI."""

from __future__ import annotations

import json
from pathlib import Path

from valska_hera_beam.external_tools.bayeseor import cli_sweep_audit


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


def _mk_sweep(
    results_root: Path,
    *,
    beam: str,
    sky: str,
    run_id: str,
    point_kind: str,
) -> Path:
    sweep_dir = results_root / "bayeseor" / beam / sky / "_sweeps" / run_id
    run_dir = sweep_dir / "validation" / "antdiam_0.0e+00"

    if point_kind == "complete":
        _mk_complete_point(run_dir)
    else:
        _mk_partial_point(run_dir)

    manifest = {
        "run_id": run_id,
        "beam_model": beam,
        "sky_model": sky,
        "created_utc": "2026-02-27T00:00:00Z",
        "points": [
            {
                "perturb_parameter": "antenna_diameter",
                "perturb_frac": 0.0,
                "run_label": "antdiam_0.0e+00",
                "run_dir": str(run_dir),
            }
        ],
    }
    sweep_dir.mkdir(parents=True, exist_ok=True)
    (sweep_dir / "sweep_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    return sweep_dir


def test_sweep_audit_json_summary(tmp_path: Path, capsys) -> None:
    results_root = tmp_path / "results"
    _mk_sweep(
        results_root,
        beam="airy_diam14m",
        sky="GSM_plus_GLEAM",
        run_id="sweep_ok",
        point_kind="complete",
    )
    _mk_sweep(
        results_root,
        beam="airy_diam14m",
        sky="GSM_plus_GLEAM",
        run_id="sweep_partial",
        point_kind="partial",
    )

    code = cli_sweep_audit.main(
        [
            "--results-root",
            str(results_root),
            "--json",
        ]
    )
    assert code == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["count"] == 2
    assert payload["summary"]["status_counts"]["ok"] == 1
    assert payload["summary"]["status_counts"]["partial"] == 1
    assert payload["summary"]["invalid_count"] == 1


def test_sweep_audit_fail_on_invalid(tmp_path: Path) -> None:
    results_root = tmp_path / "results"
    _mk_sweep(
        results_root,
        beam="airy_diam14m",
        sky="GSM_plus_GLEAM",
        run_id="sweep_partial",
        point_kind="partial",
    )

    code = cli_sweep_audit.main(
        [
            "--results-root",
            str(results_root),
            "--fail-on-invalid",
        ]
    )
    assert code == 1


def test_sweep_audit_color_always(tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    results_root = tmp_path / "results"
    _mk_sweep(
        results_root,
        beam="airy_diam14m",
        sky="GSM_plus_GLEAM",
        run_id="sweep_partial",
        point_kind="partial",
    )

    code = cli_sweep_audit.main(
        ["--results-root", str(results_root), "--color", "always"]
    )
    assert code == 0

    out = capsys.readouterr().out
    assert "\x1b[" in out
    assert "Sweep audit summary:" in out
    assert "sweep_partial" in out


def test_sweep_audit_missing_search_root_returns_2(
    tmp_path: Path, capsys
) -> None:
    code = cli_sweep_audit.main(["--results-root", str(tmp_path / "missing")])
    assert code == 2
    assert "search root does not exist" in capsys.readouterr().err
