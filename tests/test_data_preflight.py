"""Tests for the data_preflight pre-flight check package."""

from __future__ import annotations

import json
from pathlib import Path

import h5py
import pytest

from valska.data_preflight import checks as checks_module
from valska.data_preflight.cli import (
    build_parser,
    default_config_search_dirs,
    discover_uvh5_files,
    inspect_file,
    main,
)
from valska.data_preflight.inspect import read_uvh5_header
from valska.data_preflight.registry import (
    CheckContext,
    CheckResult,
    CheckStatus,
    CheckTier,
    list_checks,
    register_check,
    run_checks,
)

# ---------------------------------------------------------------------
# registry.py
# ---------------------------------------------------------------------


def test_register_check_rejects_duplicate_ids() -> None:
    @register_check("test_dup_check_unique_name", CheckTier.FAST)
    def _first(ctx: CheckContext) -> CheckResult:
        return CheckResult(
            "test_dup_check_unique_name", CheckStatus.PASS, "ok"
        )

    with pytest.raises(ValueError, match="duplicate check_id"):

        @register_check("test_dup_check_unique_name", CheckTier.FAST)
        def _second(ctx: CheckContext) -> CheckResult:
            return CheckResult(
                "test_dup_check_unique_name", CheckStatus.PASS, "ok"
            )


def test_list_checks_includes_builtins() -> None:
    fast_checks = {
        check_id for check_id, tier in list_checks([CheckTier.FAST])
    }
    assert "metadata_summary" in fast_checks
    assert "beam_type_consistency" in fast_checks


def test_run_checks_filters_by_tier() -> None:
    ctx = CheckContext(path=Path("dummy.uvh5"), header={})
    results = run_checks(ctx, [CheckTier.REFERENCE])
    assert results == []


def test_run_checks_catches_exceptions_as_fail() -> None:
    check_id = "test_exploding_check"

    @register_check(check_id, CheckTier.FAST)
    def _explode(ctx: CheckContext) -> CheckResult:
        raise RuntimeError("boom")

    ctx = CheckContext(path=Path("dummy.uvh5"), header={})
    results = run_checks(ctx, [CheckTier.FAST], check_ids=[check_id])
    assert len(results) == 1
    assert results[0].status is CheckStatus.FAIL
    assert "boom" in results[0].message


# ---------------------------------------------------------------------
# checks.py
# ---------------------------------------------------------------------


def _write_config(path: Path, beam_type: str, **extra: object) -> None:
    lines = [
        "beam_paths:",
        "  0:",
        f"    type: '{beam_type}'",
    ]
    for key, value in extra.items():
        lines.append(f"    {key}: {value}")
    lines.append(
        "telescope_location: "
        "(-30.72152777777791, 21.428305555555557, 1073.0000000093132)"
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_declared_beam_type_reads_gaussian(tmp_path: Path) -> None:
    config = tmp_path / "hex-37-gauss.yml"
    _write_config(config, "gaussian", sigma=0.0975)
    assert checks_module.declared_beam_type(config) == "gaussian"


def test_declared_beam_type_reads_airy(tmp_path: Path) -> None:
    config = tmp_path / "hex-37-airy.yml"
    _write_config(config, "airy", diameter=14.0)
    assert checks_module.declared_beam_type(config) == "airy"


def test_declared_beam_type_returns_none_for_missing_file(
    tmp_path: Path,
) -> None:
    assert checks_module.declared_beam_type(tmp_path / "missing.yml") is None


def test_declared_beam_type_returns_none_for_malformed_yaml(
    tmp_path: Path,
) -> None:
    config = tmp_path / "bad.yml"
    config.write_text("not: [valid, beam, config", encoding="utf-8")
    assert checks_module.declared_beam_type(config) is None


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        # Regression case: this is the exact real-world pattern that a
        # naive \b-boundary regex fails on, because "_" is a \w
        # character and so does not form a boundary against "airy".
        ("gsm_plus_gleam-...-airy_quentin.uvh5", {"airy"}),
        ("hex-37-14.6m-gauss-fwhm9.3.yml", {"gaussian"}),
        ("gsm_plus_gleam-...-airy_quentin_ref.uvh5", {"airy"}),
        ("plain_file_with_no_beam_keyword.uvh5", set()),
        # "hairy" should not be mistaken for "airy".
        ("some_hairy_dataset.uvh5", set()),
    ],
)
def test_path_claimed_beam_types(filename: str, expected: set[str]) -> None:
    assert checks_module.path_claimed_beam_types(Path(filename)) == expected


def test_find_cited_telescope_configs() -> None:
    history = (
        "Based on config files: fov-19.4-oscar-sm.yml, "
        "telescope_config/hex-37-14.6m-gauss-fwhm9.3.yml, "
        "telescope_config/hex-37-14.6m.csv Npus = 8."
    )
    assert checks_module.find_cited_telescope_configs(history) == [
        "hex-37-14.6m-gauss-fwhm9.3.yml"
    ]


def test_locate_config_searches_in_order(tmp_path: Path) -> None:
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()
    (dir_b / "hex.yml").write_text("beam_paths: {}", encoding="utf-8")

    found = checks_module.locate_config("hex.yml", (dir_a, dir_b))
    assert found == dir_b / "hex.yml"

    assert checks_module.locate_config("missing.yml", (dir_a, dir_b)) is None


def _ctx_for_history(
    path: Path, history: str, config_search_dirs: tuple[Path, ...] = ()
) -> CheckContext:
    return CheckContext(
        path=path,
        header={"history": history},
        config_search_dirs=config_search_dirs,
    )


def test_beam_type_consistency_fails_on_real_incident_pattern(
    tmp_path: Path,
) -> None:
    config_dir = tmp_path / "telescope_config"
    config_dir.mkdir()
    _write_config(
        config_dir / "hex-37-14.6m-gauss-fwhm9.3.yml", "gaussian", sigma=0.0975
    )

    path = tmp_path / "gsm_plus_gleam-airy_quentin.uvh5"
    ctx = _ctx_for_history(
        path,
        "Based on config files: telescope_config/hex-37-14.6m-gauss-fwhm9.3.yml",
        config_search_dirs=(config_dir,),
    )

    result = checks_module.check_beam_type_consistency(ctx)
    assert result.status is CheckStatus.FAIL
    assert "gaussian" in result.message
    assert "airy" in result.message


def test_beam_type_consistency_passes_when_consistent(tmp_path: Path) -> None:
    config_dir = tmp_path / "telescope_config"
    config_dir.mkdir()
    _write_config(config_dir / "hex-37-airy.yml", "airy", diameter=14.0)

    path = tmp_path / "gsm_plus_gleam-airy_quentin.uvh5"
    ctx = _ctx_for_history(
        path,
        "Based on config files: telescope_config/hex-37-airy.yml",
        config_search_dirs=(config_dir,),
    )

    result = checks_module.check_beam_type_consistency(ctx)
    assert result.status is CheckStatus.PASS


def test_beam_type_consistency_warns_when_config_not_locatable(
    tmp_path: Path,
) -> None:
    path = tmp_path / "gsm_plus_gleam-airy_quentin_ref.uvh5"
    ctx = _ctx_for_history(
        path,
        "Based on config files: telescope_config/hex-37-14.6m-perturbedairy.yml",
        config_search_dirs=(),
    )

    result = checks_module.check_beam_type_consistency(ctx)
    assert result.status is CheckStatus.WARN
    assert "could be located/parsed" in result.message


def test_beam_type_consistency_skips_when_no_history_citation(
    tmp_path: Path,
) -> None:
    path = tmp_path / "some_file.uvh5"
    ctx = _ctx_for_history(path, "no config references here")

    result = checks_module.check_beam_type_consistency(ctx)
    assert result.status is CheckStatus.SKIP


def test_beam_type_consistency_checks_expected_beam_type(
    tmp_path: Path,
) -> None:
    config_dir = tmp_path / "telescope_config"
    config_dir.mkdir()
    _write_config(config_dir / "hex-37-gauss.yml", "gaussian", sigma=0.0975)

    path = tmp_path / "plain_file.uvh5"
    ctx = CheckContext(
        path=path,
        header={
            "history": (
                "Based on config files: telescope_config/hex-37-gauss.yml"
            )
        },
        config_search_dirs=(config_dir,),
        expected_beam_type="airy",
    )

    result = checks_module.check_beam_type_consistency(ctx)
    assert result.status is CheckStatus.FAIL
    assert "expected beam type 'airy'" in result.message


def test_metadata_summary_reports_header_fields() -> None:
    ctx = CheckContext(
        path=Path("dummy.uvh5"),
        header={
            "nants_telescope": 37,
            "nants_data": 13,
            "nbls": 16,
            "vis_units": "Jy",
            "byte_size": 1499569,
        },
    )
    result = checks_module.check_metadata_summary(ctx)
    assert result.status is CheckStatus.PASS
    assert result.details["nants_telescope"] == 37
    assert result.details["vis_units"] == "Jy"


# ---------------------------------------------------------------------
# inspect.py
# ---------------------------------------------------------------------


def _write_minimal_uvh5_header(
    path: Path,
    *,
    nants_telescope: int = 37,
    nants_data: int = 13,
    nbls: int = 16,
    ntimes: int = 34,
    nfreqs: int = 38,
    npols: int = 4,
    history: str = "test history",
    vis_units: str = "Jy",
) -> None:
    with h5py.File(path, "w") as handle:
        header = handle.create_group("Header")
        header["Nants_telescope"] = nants_telescope
        header["Nants_data"] = nants_data
        header["Nbls"] = nbls
        header["Ntimes"] = ntimes
        header["Nfreqs"] = nfreqs
        header["Npols"] = npols
        header["history"] = history
        header["vis_units"] = vis_units


def test_read_uvh5_header_reads_expected_fields(tmp_path: Path) -> None:
    path = tmp_path / "test.uvh5"
    _write_minimal_uvh5_header(path, history="hello world")

    header = read_uvh5_header(path)
    assert header["nants_telescope"] == 37
    assert header["nants_data"] == 13
    assert header["nbls"] == 16
    assert header["ntimes"] == 34
    assert header["nfreqs"] == 38
    assert header["npols"] == 4
    assert header["history"] == "hello world"
    assert header["vis_units"] == "Jy"
    assert header["byte_size"] == path.stat().st_size


# ---------------------------------------------------------------------
# cli.py
# ---------------------------------------------------------------------


def test_default_config_search_dirs_includes_real_templates() -> None:
    dirs = default_config_search_dirs()
    assert any(d.name == "telescope_config" for d in dirs)


def test_discover_uvh5_files_finds_files_in_directory(tmp_path: Path) -> None:
    (tmp_path / "a.uvh5").touch()
    (tmp_path / "b.uvh5").touch()
    (tmp_path / "not_uvh5.txt").touch()
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.uvh5").touch()

    found = discover_uvh5_files([tmp_path])
    assert {f.name for f in found} == {"a.uvh5", "b.uvh5", "c.uvh5"}


def test_discover_uvh5_files_accepts_direct_file(tmp_path: Path) -> None:
    f = tmp_path / "single.uvh5"
    f.touch()
    assert discover_uvh5_files([f]) == [f]


def test_inspect_file_reports_error_for_unreadable_file(
    tmp_path: Path,
) -> None:
    bad = tmp_path / "not_actually_hdf5.uvh5"
    bad.write_text("not an hdf5 file", encoding="utf-8")

    report = inspect_file(
        bad,
        config_search_dirs=(),
        expected_beam_type=None,
        tiers=(CheckTier.FAST,),
    )
    assert report["error"] is not None
    assert report["checks"] == []


def test_main_end_to_end_flags_real_incident_pattern(
    tmp_path: Path, capsys
) -> None:
    config_dir = tmp_path / "telescope_config"
    config_dir.mkdir()
    _write_config(config_dir / "hex-37-gauss.yml", "gaussian", sigma=0.0975)

    uvh5_path = tmp_path / "gsm_plus_gleam-airy_quentin.uvh5"
    _write_minimal_uvh5_header(
        uvh5_path,
        history=("Based on config files: telescope_config/hex-37-gauss.yml"),
    )

    code = main(
        [
            str(uvh5_path),
            "--config-search-dir",
            str(config_dir),
            "--json",
        ]
    )
    assert code == 0  # advisory by default, even on FAIL

    payload = json.loads(capsys.readouterr().out)
    assert len(payload) == 1
    beam_check = next(
        c
        for c in payload[0]["checks"]
        if c["check_id"] == "beam_type_consistency"
    )
    assert beam_check["status"] == "fail"


def test_main_strict_exits_nonzero_on_fail(tmp_path: Path, capsys) -> None:
    config_dir = tmp_path / "telescope_config"
    config_dir.mkdir()
    _write_config(config_dir / "hex-37-gauss.yml", "gaussian", sigma=0.0975)

    uvh5_path = tmp_path / "gsm_plus_gleam-airy_quentin.uvh5"
    _write_minimal_uvh5_header(
        uvh5_path,
        history=("Based on config files: telescope_config/hex-37-gauss.yml"),
    )

    code = main(
        [
            str(uvh5_path),
            "--config-search-dir",
            str(config_dir),
            "--strict",
            "--json",
        ]
    )
    assert code == 1
    capsys.readouterr()


def test_main_returns_error_when_no_files_found(
    tmp_path: Path, capsys
) -> None:
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    code = main([str(empty_dir)])
    assert code == 2
    captured = capsys.readouterr()
    assert "no .uvh5 files found" in captured.err


def test_build_parser_accepts_repeated_config_search_dir() -> None:
    parser = build_parser()
    args = parser.parse_args(
        ["file.uvh5", "--config-search-dir", "a", "--config-search-dir", "b"]
    )
    assert args.config_search_dirs == [Path("a"), Path("b")]
