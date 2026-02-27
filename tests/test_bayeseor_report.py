"""Tests for standalone BayesEoR sweep report generation."""

from __future__ import annotations

import json
from pathlib import Path

from valska_hera_beam.external_tools.bayeseor import cli_report
from valska_hera_beam.external_tools.bayeseor.report import (
    generate_sweep_report,
    parse_data_stats_evidence,
)


def _write_data_stats(
    path: Path, *, ns: float, ns_err: str, ins: float, ins_err: str
) -> None:
    path.write_text(
        (
            "Nested Sampling Global Log-Evidence           : "
            f"   {ns:.15E}  +/-    {ns_err}\n"
            "Nested Importance Sampling Global Log-Evidence: "
            f"   {ins:.15E}  +/-    {ins_err}\n"
        ),
        encoding="utf-8",
    )


def _mk_point(run_dir: Path, *, signal_ns: float, no_signal_ns: float) -> None:
    signal_stats = (
        run_dir / "output" / "signal_fit" / "MN-signal" / "data-stats.dat"
    )
    signal_stats.parent.mkdir(parents=True, exist_ok=True)
    (signal_stats.parent / "data-.txt").write_text(
        "dummy chain content\n", encoding="utf-8"
    )
    _write_data_stats(
        signal_stats,
        ns=signal_ns,
        ns_err="1.0E+00",
        ins=signal_ns - 0.2,
        ins_err="5.0E-02",
    )

    no_signal_stats = (
        run_dir / "output" / "no_signal" / "MN-no-signal" / "data-stats.dat"
    )
    no_signal_stats.parent.mkdir(parents=True, exist_ok=True)
    (no_signal_stats.parent / "data-.txt").write_text(
        "dummy chain content\n", encoding="utf-8"
    )
    _write_data_stats(
        no_signal_stats,
        ns=no_signal_ns,
        ns_err="NaN",
        ins=no_signal_ns - 0.1,
        ins_err="4.0E-02",
    )


def test_parse_data_stats_evidence_reads_ns_and_ins(tmp_path: Path) -> None:
    stats = tmp_path / "data-stats.dat"
    _write_data_stats(
        stats,
        ns=123.4,
        ns_err="2.0E+00",
        ins=122.9,
        ins_err="NaN",
    )

    parsed = parse_data_stats_evidence(stats)
    assert parsed.ns_log_evidence == 123.4
    assert parsed.ns_log_evidence_err == 2.0
    assert parsed.ins_log_evidence == 122.9
    assert parsed.ins_log_evidence_err is None


def test_generate_sweep_report_writes_outputs(tmp_path: Path) -> None:
    sweep_dir = tmp_path / "_sweeps" / "sweep_test"
    point_a = sweep_dir / "validation" / "antdiam_-1.0e-01"
    point_b = sweep_dir / "validation" / "antdiam_0.0e+00"
    _mk_point(point_a, signal_ns=10.0, no_signal_ns=12.0)
    _mk_point(point_b, signal_ns=13.0, no_signal_ns=12.0)

    manifest = {
        "points": [
            {
                "perturb_parameter": "antenna_diameter",
                "perturb_frac": -0.1,
                "run_label": "antdiam_-1.0e-01",
                "run_dir": str(point_a),
            },
            {
                "perturb_parameter": "antenna_diameter",
                "perturb_frac": 0.0,
                "run_label": "antdiam_0.0e+00",
                "run_dir": str(point_b),
            },
        ]
    }
    sweep_dir.mkdir(parents=True, exist_ok=True)
    (sweep_dir / "sweep_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    result = generate_sweep_report(
        sweep_dir=sweep_dir,
        out_dir=None,
        evidence_source="ins",
        make_plots=False,
    )

    assert result.rows_total == 2
    assert result.rows_complete == 2
    assert result.summary_csv.exists()
    assert result.summary_json.exists()

    payload = json.loads(result.summary_json.read_text(encoding="utf-8"))
    assert len(payload["points"]) == 2
    first = payload["points"][0]
    assert first["status"] == "ok"
    assert first["delta_log_evidence"] is not None


def test_cli_report_json_output(tmp_path: Path, capsys) -> None:
    sweep_dir = tmp_path / "_sweeps" / "sweep_test"
    point = sweep_dir / "validation" / "antdiam_0.0e+00"
    _mk_point(point, signal_ns=21.0, no_signal_ns=20.0)

    manifest = {
        "points": [
            {
                "perturb_parameter": "antenna_diameter",
                "perturb_frac": 0.0,
                "run_label": "antdiam_0.0e+00",
                "run_dir": str(point),
            }
        ]
    }
    sweep_dir.mkdir(parents=True, exist_ok=True)
    (sweep_dir / "sweep_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    code = cli_report.main([str(sweep_dir), "--json", "--no-plots"])
    assert code == 0

    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["rows_total"] == 1
    assert payload["rows_complete"] == 1


def test_generate_sweep_report_marks_incomplete_when_chain_file_missing(
    tmp_path: Path,
) -> None:
    sweep_dir = tmp_path / "_sweeps" / "sweep_missing_chain"
    point = sweep_dir / "validation" / "antdiam_0.0e+00"
    _mk_point(point, signal_ns=30.0, no_signal_ns=29.0)

    # Simulate broken/partial run output.
    (point / "output" / "no_signal" / "MN-no-signal" / "data-.txt").unlink()

    manifest = {
        "points": [
            {
                "perturb_parameter": "antenna_diameter",
                "perturb_frac": 0.0,
                "run_label": "antdiam_0.0e+00",
                "run_dir": str(point),
            }
        ]
    }
    sweep_dir.mkdir(parents=True, exist_ok=True)
    (sweep_dir / "sweep_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    result = generate_sweep_report(
        sweep_dir=sweep_dir,
        out_dir=None,
        evidence_source="ins",
        make_plots=False,
    )

    assert result.rows_total == 1
    assert result.rows_complete == 0

    payload = json.loads(result.summary_json.read_text(encoding="utf-8"))
    assert payload["points"][0]["status"] == "incomplete"
    assert "Missing chain file" in payload["points"][0]["note"]
