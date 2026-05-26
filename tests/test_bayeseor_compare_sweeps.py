"""Tests for valska-bayeseor-compare-sweeps CLI."""

from __future__ import annotations

import json
from pathlib import Path

from valska_hera_beam.external_tools.bayeseor import cli_compare_sweeps


def _write_summary(path: Path, points: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"points": points}), encoding="utf-8")


def _point(
    run_label: str,
    *,
    perturb_frac: float,
    status: str,
    delta: float | None,
    log10_bf: float | None,
) -> dict[str, object]:
    return {
        "perturb_parameter": "antenna_diameter",
        "perturb_frac": perturb_frac,
        "run_label": run_label,
        "status": status,
        "delta_log_evidence": delta,
        "log10_bayes_factor_signal_over_no_signal": log10_bf,
        "bayes_factor_signal_over_no_signal": None,
    }


def test_cli_compare_sweeps_json_from_sweep_dirs(
    tmp_path: Path, capsys
) -> None:
    left_summary = tmp_path / "left" / "report" / "sweep_report_summary.json"
    right_summary = tmp_path / "right" / "report" / "sweep_report_summary.json"

    _write_summary(
        left_summary,
        [
            _point(
                "antdiam_0.0e+00",
                perturb_frac=0.0,
                status="ok",
                delta=1.0,
                log10_bf=0.43,
            ),
            _point(
                "antdiam_1.0e-02",
                perturb_frac=0.01,
                status="ok",
                delta=2.0,
                log10_bf=0.87,
            ),
            _point(
                "left_only",
                perturb_frac=0.02,
                status="ok",
                delta=3.0,
                log10_bf=1.3,
            ),
        ],
    )
    _write_summary(
        right_summary,
        [
            _point(
                "antdiam_0.0e+00",
                perturb_frac=0.0,
                status="ok",
                delta=1.5,
                log10_bf=0.65,
            ),
            _point(
                "antdiam_1.0e-02",
                perturb_frac=0.01,
                status="ok",
                delta=1.0,
                log10_bf=0.43,
            ),
            _point(
                "right_only",
                perturb_frac=0.03,
                status="ok",
                delta=4.0,
                log10_bf=1.74,
            ),
        ],
    )

    code = cli_compare_sweeps.main(
        [
            str(left_summary.parent.parent),
            str(right_summary.parent.parent),
            "--json",
            "--top",
            "1",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["summary"]["left_points"] == 3
    assert payload["summary"]["right_points"] == 3
    assert payload["summary"]["shared_points"] == 2
    assert payload["summary"]["left_only_points"] == 1
    assert payload["summary"]["right_only_points"] == 1
    assert payload["summary"]["compared_points"] == 2
    assert len(payload["top_differences"]) == 1
    assert payload["top_differences"][0]["point_key"] == "antdiam_1.0e-02"
    assert payload["top_differences"][0]["delta"] == -1.0


def test_cli_compare_sweeps_metric_and_missing_metric_skip(
    tmp_path: Path, capsys
) -> None:
    left = tmp_path / "left.json"
    right = tmp_path / "right.json"

    _write_summary(
        left,
        [
            _point(
                "antdiam_0.0e+00",
                perturb_frac=0.0,
                status="ok",
                delta=1.0,
                log10_bf=0.2,
            ),
            _point(
                "antdiam_1.0e-02",
                perturb_frac=0.01,
                status="ok",
                delta=2.0,
                log10_bf=None,
            ),
        ],
    )
    _write_summary(
        right,
        [
            _point(
                "antdiam_0.0e+00",
                perturb_frac=0.0,
                status="ok",
                delta=1.2,
                log10_bf=0.3,
            ),
            _point(
                "antdiam_1.0e-02",
                perturb_frac=0.01,
                status="incomplete",
                delta=2.2,
                log10_bf=0.9,
            ),
        ],
    )

    code = cli_compare_sweeps.main(
        [
            str(left),
            str(right),
            "--metric",
            "log10_bayes_factor_signal_over_no_signal",
            "--json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["summary"]["shared_points"] == 2
    assert payload["summary"]["status_mismatch_points"] == 1
    assert payload["summary"]["compared_points"] == 1
    assert payload["summary"]["skipped_missing_metric"] == 1
    assert payload["top_differences"][0]["point_key"] == "antdiam_0.0e+00"
    assert abs(payload["top_differences"][0]["delta"] - 0.1) < 1e-12


def test_cli_compare_sweeps_color_always(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    left = tmp_path / "left.json"
    right = tmp_path / "right.json"
    _write_summary(
        left,
        [
            _point(
                "antdiam_0.0e+00",
                perturb_frac=0.0,
                status="ok",
                delta=1.0,
                log10_bf=0.2,
            )
        ],
    )
    _write_summary(
        right,
        [
            _point(
                "antdiam_0.0e+00",
                perturb_frac=0.0,
                status="ok",
                delta=1.2,
                log10_bf=0.3,
            )
        ],
    )

    code = cli_compare_sweeps.main(
        [str(left), str(right), "--color", "always"]
    )
    assert code == 0

    out = capsys.readouterr().out
    assert "\x1b[" in out
    assert "Sweep comparison summary:" in out
    assert "antdiam_0.0e+00" in out


def test_cli_compare_sweeps_missing_input_returns_2(
    tmp_path: Path, capsys
) -> None:
    left = tmp_path / "missing_left"
    right = tmp_path / "missing_right"

    code = cli_compare_sweeps.main([str(left), str(right)])
    assert code == 2
    assert "ERROR:" in capsys.readouterr().err
