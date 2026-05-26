"""Tests for sweep resume CLI."""

from __future__ import annotations

import json
from pathlib import Path

from valska_hera_beam.external_tools.bayeseor import cli_resume


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
    (run_dir / "manifest.json").write_text("{}", encoding="utf-8")


def _mk_missing_point(run_dir: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)


def _mk_sweep(tmp_path: Path) -> Path:
    sweep_dir = tmp_path / "_sweeps" / "sweep_resume"
    point_ok = sweep_dir / "validation" / "antdiam_0.0e+00"
    point_partial = sweep_dir / "validation" / "antdiam_1.0e-02"
    point_missing = sweep_dir / "validation" / "antdiam_2.0e-02"

    _mk_complete_point(point_ok)
    _mk_partial_point(point_partial)
    _mk_missing_point(point_missing)

    manifest = {
        "run_id": "sweep_resume",
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
            {
                "perturb_parameter": "antenna_diameter",
                "perturb_frac": 0.02,
                "run_label": "antdiam_2.0e-02",
                "run_dir": str(point_missing),
            },
        ],
    }
    sweep_dir.mkdir(parents=True, exist_ok=True)
    (sweep_dir / "sweep_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    return sweep_dir


def test_cli_resume_json_all(tmp_path: Path, capsys) -> None:
    sweep_dir = _mk_sweep(tmp_path)

    code = cli_resume.main([str(sweep_dir), "--json"])
    assert code == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["points_total"] == 3
    assert payload["summary"]["points_targeted"] == 2
    assert payload["summary"]["commands_total"] == 3

    rows = {row["run_label"]: row for row in payload["points"]}
    assert "antdiam_1.0e-02" in rows
    assert "antdiam_2.0e-02" in rows
    assert any(
        "--stage gpu --hypothesis no_signal" in cmd
        for cmd in rows["antdiam_1.0e-02"]["commands"]
    )
    assert any(
        "--stage cpu" in cmd for cmd in rows["antdiam_2.0e-02"]["commands"]
    )
    assert any(
        "--stage gpu --hypothesis both" in cmd
        for cmd in rows["antdiam_2.0e-02"]["commands"]
    )


def test_cli_resume_stage_cpu_only(tmp_path: Path, capsys) -> None:
    sweep_dir = _mk_sweep(tmp_path)

    code = cli_resume.main([str(sweep_dir), "--stage", "cpu", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["summary"]["points_targeted"] == 1
    assert payload["summary"]["commands_total"] == 1
    assert payload["points"][0]["run_label"] == "antdiam_2.0e-02"
    assert payload["points"][0]["commands"] == [
        f'valska-bayeseor-submit "{payload["points"][0]["run_dir"]}" --stage cpu'
    ]


def test_cli_resume_color_always(tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    sweep_dir = _mk_sweep(tmp_path)

    code = cli_resume.main([str(sweep_dir), "--color", "always"])
    assert code == 0

    out = capsys.readouterr().out
    assert "\x1b[" in out
    assert "Sweep resume suggestions:" in out
    assert "valska-bayeseor-submit" in out


def test_cli_resume_missing_manifest_returns_2(tmp_path: Path, capsys) -> None:
    code = cli_resume.main([str(tmp_path / "missing")])
    assert code == 2
    assert "ERROR:" in capsys.readouterr().err
