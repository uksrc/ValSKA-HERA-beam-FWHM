import json
from pathlib import Path


def _write_submit_fixture(run_dir: Path) -> None:
    scripts = {
        "submit_simulate.sh": "#!/bin/bash\n",
    }
    for name, content in scripts.items():
        path = run_dir / name
        path.write_text(content, encoding="utf-8")
        path.chmod(0o750)

    manifest = {
        "artefacts": {
            "submit_sh_simulate": "submit_simulate.sh",
        },
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )


def test_build_submit_plan(): ...
