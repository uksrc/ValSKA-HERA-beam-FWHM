"""Tests for valska-bayeseor-list-sweeps CLI."""

from __future__ import annotations

import json
from pathlib import Path

from valska.external_tools.bayeseor import cli_list_sweeps


def _mk_sweep(
    root: Path,
    *,
    beam: str,
    sky: str,
    run_id: str,
    created_utc: str,
) -> Path:
    sweep_dir = root / "bayeseor" / beam / sky / "_sweeps" / run_id
    sweep_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "beam_model": beam,
        "sky_model": sky,
        "run_id": run_id,
        "created_utc": created_utc,
        "points": [
            {
                "run_label": "antdiam_0.0e+00",
                "run_dir": str(sweep_dir / "validation" / "antdiam_0.0e+00"),
                "perturb_frac": 0.0,
            }
        ],
    }
    (sweep_dir / "sweep_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    return sweep_dir


def test_list_sweeps_json_and_filters(tmp_path: Path, capsys) -> None:
    results_root = tmp_path / "results"
    _mk_sweep(
        results_root,
        beam="achromatic_Gaussian",
        sky="GLEAM",
        run_id="sweep_a",
        created_utc="2026-02-18T20:00:00Z",
    )
    _mk_sweep(
        results_root,
        beam="airy_diam14m",
        sky="GSM_plus_GLEAM",
        run_id="sweep_b",
        created_utc="2026-02-19T20:00:00Z",
    )

    code = cli_list_sweeps.main(
        [
            "--results-root",
            str(results_root),
            "--beam",
            "airy",
            "--json",
        ]
    )
    assert code == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["count"] == 1
    assert payload["sweeps"][0]["run_id"] == "sweep_b"


def test_list_sweeps_latest(tmp_path: Path, capsys) -> None:
    results_root = tmp_path / "results"
    _mk_sweep(
        results_root,
        beam="achromatic_Gaussian",
        sky="GLEAM",
        run_id="sweep_old",
        created_utc="2026-02-18T20:00:00Z",
    )
    _mk_sweep(
        results_root,
        beam="achromatic_Gaussian",
        sky="GLEAM",
        run_id="sweep_new",
        created_utc="2026-02-20T20:00:00Z",
    )

    code = cli_list_sweeps.main(
        [
            "--results-root",
            str(results_root),
            "--latest",
            "--json",
        ]
    )
    assert code == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["count"] == 1
    assert payload["sweeps"][0]["run_id"] == "sweep_new"


def test_list_sweeps_missing_search_root_returns_2(
    tmp_path: Path, capsys
) -> None:
    code = cli_list_sweeps.main(["--results-root", str(tmp_path / "missing")])
    assert code == 2
    assert "search root does not exist" in capsys.readouterr().err
