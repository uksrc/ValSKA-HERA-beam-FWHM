# Shared Infrastructure Roadmap

**Version:** 1.0.0-draft
**Status:** Draft
**Last updated:** 2026-01-21

---

## 1. Introduction

### 1.1 Purpose

This document outlines a future refactoring to extract shared infrastructure from individual external tool implementations into a common `core` module. It captures the rationale, identifies candidates for consolidation, and proposes a migration strategy.

### 1.2 Status

This is a **roadmap**, not a specification. The approach described here is intentionally deferred:

- **Current state:** Each tool (BayesEoR, pyuvsim) implements its own utilities
- **Future state:** Common patterns extracted into `valska_hera_beam.external_tools.core`
- **Trigger:** Refactoring should occur after two or more tools are implemented and patterns are validated in practice

### 1.3 Rationale for deferral

Extracting shared infrastructure *before* implementing multiple tools risks:

1. **Premature abstraction** — Guessing at the right interfaces without concrete evidence
2. **Over-engineering** — Building flexibility that is never used
3. **Churn** — Refactoring the shared layer as each new tool reveals edge cases

By implementing BayesEoR and pyuvsim as standalone modules first, we gain:

1. **Concrete duplication** — Clear evidence of what is genuinely shared
2. **Validated patterns** — Interfaces proven to work for different tool characteristics
3. **Lower risk** — Refactoring existing working code is safer than designing upfront

---

## 2. Current state

### 2.1 BayesEoR module structure

```
src/valska_hera_beam/external_tools/bayeseor/
├── __init__.py
├── cli_prepare.py
├── cli_submit.py
├── cli_sweep.py
├── runner.py
├── setup.py
├── slurm.py
├── submit.py
├── sweep.py
├── templates.py
└── templates/
```

### 2.2 pyuvsim module structure (planned)

```
src/valska_hera_beam/external_tools/pyuvsim/
├── __init__.py
├── cli_prepare.py
├── cli_submit.py
├── runner.py
├── setup.py
├── slurm.py
├── submit.py
├── templates.py
└── templates/
```

### 2.3 Observed duplication

Based on the BayesEoR implementation and the pyuvsim patterns described in the Tool Implementer's Guide, the following areas exhibit significant overlap:

| Concern | BayesEoR location | pyuvsim location | Duplication level |
|---------|-------------------|------------------|-------------------|
| Run directory creation | `setup.py` | `setup.py` | High |
| Manifest writing | `setup.py` | `setup.py` | High |
| Jobs.json writing | `submit.py` | `submit.py` | High |
| SLURM submission | `submit.py` | `submit.py` | High |
| Runner definitions | `runner.py` | `runner.py` | Medium |
| Template utilities | `templates.py` | `templates.py` | High |
| Configuration loading | `cli_prepare.py` | `cli_prepare.py` | Medium |
| SLURM directive handling | `slurm.py` | `slurm.py` | Medium |
| UTC timestamp helpers | Multiple files | Multiple files | High |
| Dry-run semantics | CLI files | CLI files | Medium |

---

## 3. Proposed shared infrastructure

### 3.1 Target structure

```
src/valska_hera_beam/external_tools/
├── core/
│   ├── __init__.py
│   ├── run_directory.py      # Run directory creation and validation
│   ├── manifest.py           # Manifest reading/writing
│   ├── jobs.py               # Jobs.json reading/writing
│   ├── slurm.py              # SLURM submission utilities
│   ├── runner.py             # Base runner classes
│   ├── templates.py          # Template discovery utilities
│   ├── config.py             # Configuration loading and merging
│   └── utils.py              # Common utilities (timestamps, JSON, etc.)
├── bayeseor/
│   └── ...                   # Tool-specific implementation
└── pyuvsim/
    └── ...                   # Tool-specific implementation
```

### 3.2 Module responsibilities

#### 3.2.1 `core/run_directory.py`

**Responsibility:** Run directory creation, validation, and path construction.

**Candidate functions:**

```python
def build_run_dir(
    results_root: Path,
    tool: str,
    taxonomy: dict[str, str],
    run_id: str,
    unique: bool = False,
) -> Path:
    """
    Construct a run directory path.

    Parameters
    ----------
    results_root
        Base results directory.
    tool
        Tool identifier (e.g., 'bayeseor', 'pyuvsim').
    taxonomy
        Tool-specific hierarchy components as key-value pairs.
        e.g., {'beam_model': 'achromatic_Gaussian', 'sky_model': 'GLEAM'}
    run_id
        User-provided run identifier.
    unique
        If True, append UTC timestamp for uniqueness.

    Returns
    -------
    Path to run directory.
    """
    pass


def validate_run_dir(run_dir: Path) -> None:
    """
    Validate that a run directory exists and contains required files.

    Raises
    ------
    RunDirectoryError
        If validation fails.
    """
    pass


def ensure_run_dir(run_dir: Path, exist_ok: bool = False) -> None:
    """
    Create run directory, optionally failing if it exists.
    """
    pass
```

**Current duplication:**
- `bayeseor/setup.py`: Manual path construction
- `pyuvsim/setup.py`: `build_run_dir()` function

---

### 3.2.2 `core/manifest.py`

**Responsibility:** Manifest definition, reading, and writing.

**Candidate functions:**

```python
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ManifestBase:
    """Required fields for all manifests."""
    tool: str
    created_utc: str
    valska_version: str
    run_id: str
    run_dir: str
    results_root: str


def write_manifest(
    run_dir: Path,
    *,
    tool: str,
    run_id: str,
    results_root: Path,
    extra_fields: dict[str, Any] | None = None,
) -> Path:
    """
    Write manifest.json with required fields plus tool-specific extras.

    Automatically includes:
    - tool
    - created_utc
    - valska_version
    - run_id
    - run_dir
    - results_root
    """
    pass


def load_manifest(run_dir: Path) -> dict[str, Any]:
    """
    Load and validate manifest.json from a run directory.

    Raises
    ------
    ManifestError
        If manifest is missing or invalid.
    """
    pass


def validate_manifest(manifest: dict[str, Any]) -> None:
    """
    Validate that manifest contains all required fields and raise clear errors.
    """
    pass
```

**Current duplication:**
- `bayeseor/setup.py`: `write_manifest()` with BayesEoR-specific fields
- `bayeseor/submit.py`: `load_manifest()`
- `pyuvsim/setup.py`: `write_manifest()` with pyuvsim-specific fields
- `pyuvsim/submit.py`: `load_manifest()`

---

#### 3.2.3 `core/jobs.py`

**Responsibility:** Jobs.json schema definition, reading, writing, and archival.

**Candidate functions:**

```python
from pathlib import Path
from typing import Any


def write_jobs_json(
    run_dir: Path,
    *,
    stage: str,
    jobs: dict[str, dict[str, Any]],
    commands: list[str],
    dry_run: bool = False,
    sbatch: str = "sbatch",
    extra_fields: dict[str, Any] | None = None,
) -> Path:
    """
    Write jobs.json with submission details.

    Automatically includes:
    - run_dir
    - manifest path
    - submitted_utc
    """
    pass


def load_jobs_json(run_dir: Path) -> dict[str, Any] | None:
    """
    Load jobs.json if it exists, otherwise return None.
    """
    pass


def archive_jobs_json(run_dir: Path) -> Path | None:
    """
    Archive existing jobs.json with timestamp suffix.

    Returns path to archived file, or None if no jobs.json existed.
    """
    pass


def has_submitted_stage(jobs: dict[str, Any] | None, stage: str) -> bool:
    """
    Check if a stage has been submitted.
    """
    pass
```

**Current duplication:**
- `bayeseor/submit.py`: Jobs.json writing and archival
- `bayeseor/cli_submit.py`: `_archive_jobs_json()`, `_load_jobs_json()`
- `pyuvsim/submit.py`: Jobs.json writing

---

#### 3.2.4 `core/slurm.py`

**Responsibility:** SLURM job submission and output parsing.

**Candidate functions:**

```python
import re
import subprocess
from pathlib import Path
from typing import Any


JOBID_REGEX = re.compile(r"Submitted\s+batch\s+job\s+(\d+)", re.IGNORECASE)


class SlurmSubmissionError(RuntimeError):
    """Raised when sbatch submission fails."""
    pass


def submit_script(
    script_path: Path,
    *,
    sbatch: str = "sbatch",
    dependency: str | None = None,
    cwd: Path | None = None,
    dry_run: bool = False,
) -> str | None:
    """
    Submit a SLURM script and return the job ID.

    Parameters
    ----------
    script_path
        Path to submit script.
    sbatch
        Path to sbatch executable.
    dependency
        Dependency specification (e.g., 'afterok:12345').
    cwd
        Working directory for submission.
    dry_run
        If True, print command without executing.

    Returns
    -------
    Job ID as string, or None if dry_run.

    Raises
    ------
    SlurmSubmissionError
        If submission fails.
    """
    pass


def parse_job_id(sbatch_output: str) -> str:
    """
    Extract job ID from sbatch output.

    Raises
    ------
    SlurmSubmissionError
        If job ID cannot be parsed.
    """
    pass


def build_dependency_string(job_ids: list[str], mode: str = "afterok") -> str:
    """
    Build a SLURM dependency string.

    Parameters
    ----------
    job_ids
        List of job IDs to depend on.
    mode
        Dependency mode ('afterok', 'afterany', etc.).

    Returns
    -------
    Dependency string (e.g., 'afterok:123:456').
    """
    pass
```

**Current duplication:**
- `bayeseor/submit.py`: `_JOBID_RE`, sbatch invocation
- `pyuvsim/submit.py`: `_JOBID_RE`, sbatch invocation

---

#### 3.2.5 `core/runner.py`

**Responsibility:** Base runner class definitions.

**Candidate classes:**

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CondaRunner:
    """Execute a tool within a conda environment."""

    conda_sh: str
    """Command to source conda (e.g., 'source /path/to/conda.sh')."""

    conda_env: str
    """Name of the conda environment."""

    def activation_commands(self) -> list[str]:
        """Return shell commands to activate the environment."""
        return [self.conda_sh, f"conda activate {self.conda_env}"]


@dataclass(frozen=True)
class ContainerRunner:
    """Execute a tool within an Apptainer/Singularity container."""

    container_image: Path
    """Path to the container image (.sif file)."""

    container_bind: str | None = None
    """Bind mount specification."""

    def exec_prefix(self) -> str:
        """Return the apptainer exec prefix."""
        bind = f"--bind {self.container_bind} " if self.container_bind else ""
        return f"apptainer exec {bind}{self.container_image}"
```

**Current duplication:**
- `bayeseor/runner.py`: `CondaRunner`, `ContainerRunner`, `BayesEoRInstall`
- `pyuvsim/runner.py`: `CondaRunner`, `ContainerRunner`

**Note:** Tool-specific install classes (e.g., `BayesEoRInstall`) remain in tool modules.

---

#### 3.2.6 `core/templates.py`

**Responsibility:** Template discovery utilities.

**Candidate functions:**

```python
from pathlib import Path


def get_templates_dir(tool_module_path: Path) -> Path:
    """
    Return the templates directory for a tool module.

    Parameters
    ----------
    tool_module_path
        Path to a file in the tool module (typically __file__).

    Returns
    -------
    Path to templates/ directory.
    """
    return tool_module_path.parent / "templates"


def list_templates(templates_dir: Path, suffix: str = ".yaml") -> list[str]:
    """
    List available template names in a directory.
    """
    if not templates_dir.exists():
        return []
    return sorted(p.name for p in templates_dir.glob(f"*{suffix}"))


def get_template_path(
    templates_dir: Path,
    name: str,
    suffix: str = ".yaml",
) -> Path:
    """
    Get full path to a template by name.

    Raises
    ------
    FileNotFoundError
        If template does not exist.
    """
    if not name.endswith(suffix):
        name = f"{name}{suffix}"

    path = templates_dir / name
    if not path.exists():
        available = list_templates(templates_dir, suffix)
        raise FileNotFoundError(
            f"Template not found: {name}\n"
            f"Available: {', '.join(available) or '(none)'}"
        )
    return path
```

**Current duplication:**
- `bayeseor/templates.py`: `_templates_dir()`, `list_templates()`, `get_template_path()`
- `pyuvsim/templates.py`: Identical pattern

---

#### 3.2.7 `core/config.py`

**Responsibility:** Configuration loading and merging.

**Candidate functions:**

```python
from pathlib import Path
from typing import Any
import yaml


def load_runtime_paths() -> dict[str, Any]:
    """
    Load runtime_paths.yaml from the config directory.

    Returns empty dict if file does not exist.
    """
    pass


def get_tool_config(runtime: dict[str, Any], tool: str) -> dict[str, Any]:
    """
    Extract tool-specific configuration section.
    """
    return runtime.get(tool, {})


def get_nested(d: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """
    Safely navigate nested dictionary keys.
    """
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k, default)
        if cur is default:
            return default
    return cur


def merge_slurm_config(
    defaults: dict[str, Any],
    tool_config: dict[str, Any],
    cli_overrides: dict[str, Any],
) -> dict[str, Any]:
    """
    Merge SLURM configuration with precedence: CLI > tool config > defaults.

    None values in higher-precedence layers suppress the key.
    """
    result = dict(defaults)
    result.update({k: v for k, v in tool_config.items() if v is not None})
    result.update({k: v for k, v in cli_overrides.items() if v is not None})
    # Remove any keys explicitly set to None
    return {k: v for k, v in result.items() if v is not None}
```

**Current duplication:**
- `bayeseor/cli_prepare.py`: `_get_nested()`, `_slurm_defaults()`
- `pyuvsim/cli_prepare.py`: `load_runtime_config()`, `build_slurm_config()`

---

#### 3.2.8 `core/utils.py`

**Responsibility:** Common utility functions.

**Candidate functions:**

```python
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    """Return current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def utc_now_compact() -> str:
    """Return current UTC time in compact format (for filenames)."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json_atomic(path: Path, data: dict[str, Any], indent: int = 2) -> None:
    """
    Write JSON atomically to avoid partial writes on failure.
    """
    tmp_path = path.with_suffix(".json.tmp")
    with tmp_path.open("w") as f:
        json.dump(data, f, indent=indent)
    tmp_path.rename(path)


def load_json(path: Path) -> dict[str, Any]:
    """Load JSON file."""
    with path.open() as f:
        return json.load(f)
```

**Current duplication:**
- `bayeseor/setup.py`: `_utc_stamp()`
- `bayeseor/cli_submit.py`: `_utc_now_compact()`
- `bayeseor/submit.py`: `_utc_now_iso()`
- `pyuvsim/submit.py`: `_utc_now_iso()`

---

## 4. Migration strategy

### 4.1 Prerequisites

Before beginning migration:

1. **pyuvsim implemented** — At least two tools exist to validate patterns
2. **Tests passing** — Both tool modules have comprehensive test coverage
3. **Patterns validated** — Identified shared code confirmed to be genuinely common

### 4.2 Phase 1: Extract utilities (low risk)

**Scope:** `core/utils.py`

**Steps:**

1. Create `core/` directory with `__init__.py`
2. Implement `core/utils.py` with timestamp and JSON helpers
3. Update BayesEoR to import from `core.utils`
4. Update pyuvsim to import from `core.utils`
5. Remove duplicated helpers from tool modules
6. Run tests, verify no regressions

**Estimated effort:** 1–2 hours

---

### 4.3 Phase 2: Extract templates (low risk)

**Scope:** `core/templates.py`

**Steps:**

1. Implement `core/templates.py` with generic template utilities
2. Update tool-specific `templates.py` to use core utilities
3. Tool modules retain thin wrappers that specify their templates directory
4. Run tests

**Estimated effort:** 1–2 hours

---

### 4.4 Phase 3: Extract runner base classes (medium risk)

**Scope:** `core/runner.py`

**Steps:**

1. Implement `core/runner.py` with `CondaRunner` and `ContainerRunner`
2. Tool-specific install classes (e.g., `BayesEoRInstall`) remain in tool modules
3. Update tool modules to import base runners from core
4. Run tests

**Estimated effort:** 2–3 hours

---

### 4.5 Phase 4: Extract SLURM submission (medium risk)

**Scope:** `core/slurm.py`

**Steps:**

1. Implement `core/slurm.py` with submission utilities
2. Update tool `submit.py` modules to use core submission
3. Tool modules retain script *generation* (tool-specific)
4. Run tests

**Estimated effort:** 3–4 hours

---

### 4.6 Phase 5: Extract manifest/jobs handling (medium risk)

**Scope:** `core/manifest.py`, `core/jobs.py`

**Steps:**

1. Implement `core/manifest.py` with generic manifest utilities
2. Implement `core/jobs.py` with jobs.json utilities
3. Update tool modules to use core for reading/writing
4. Tool modules provide tool-specific extra fields
5. Run tests

**Estimated effort:** 4–6 hours

---

### 4.7 Phase 6: Extract configuration loading (medium risk)

**Scope:** `core/config.py`

**Steps:**

1. Implement `core/config.py` with configuration utilities
2. Update tool CLI modules to use core configuration loading
3. Tool modules retain tool-specific argument parsing
4. Run tests

**Estimated effort:** 3–4 hours

---

### 4.8 Phase 7: Extract run directory handling (low–medium risk)

**Scope:** `core/run_directory.py`

**Steps:**

1. Implement `core/run_directory.py` with generic path construction
2. Tool modules provide taxonomy definition, core handles construction
3. Update tool modules
4. Run tests

**Estimated effort:** 2–3 hours

---

## 5. Post-migration structure

### 5.1 Core module

```
src/valska_hera_beam/external_tools/core/
├── __init__.py
├── config.py
├── jobs.py
├── manifest.py
├── run_directory.py
├── runner.py
├── slurm.py
├── templates.py
└── utils.py
```

### 5.2 Tool module (simplified)

```
src/valska_hera_beam/external_tools/pyuvsim/
├── __init__.py
├── cli_prepare.py      # Argument parsing, tool-specific logic
├── cli_submit.py       # Thin wrapper around core submission
├── runner.py           # Tool-specific install class (if needed)
├── slurm.py            # SLURM script generation (tool-specific)
├── templates.py        # Thin wrapper around core templates
└── templates/
```

### 5.3 Dependency direction

```
┌─────────────────────┐
│     core module     │  ← No dependencies on tool modules
└─────────────────────┘
          ▲
          │ imports
          │
┌─────────────────────┐
│   bayeseor module   │
└─────────────────────┘

┌─────────────────────┐
│   pyuvsim module    │
└─────────────────────┘
```

Tool modules depend on core; core never imports from tools.

---

## 6. Success criteria

### 6.1 Quantitative

| Metric | Target |
|--------|--------|
| Lines of code reduction per tool | 30–50% |
| Test duplication reduction | 40–60% |
| Time to implement new tool | 50% less than current |

### 6.2 Qualitative

- New tool implementations focus on tool-specific concerns
- Common bugs fixed once in core, all tools benefit
- Consistent behaviour across tools for shared operations
- Clear separation between "what all tools do" and "what this tool does"

---

## 7. Risks and mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Core abstraction doesn't fit new tool | High | Medium | Keep core interfaces minimal; allow bypass |
| Breaking changes during migration | Medium | Medium | Migrate one module at a time; comprehensive tests |
| Over-abstraction | Medium | Low | Extract only proven patterns; resist "future-proofing" |
| Increased coupling | Medium | Low | Core has no knowledge of specific tools |

---

## 8. Decision log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-21 | Defer shared infrastructure extraction | Avoid premature abstraction; validate patterns with pyuvsim first |
| 2026-01-21 | Document intended structure as roadmap | Capture intent while allowing standalone tool development |

---

## 9. Open questions

### 9.1 To be resolved before migration

1. **Exception hierarchy** — Should core define a base exception class that tool-specific exceptions inherit from?

2. **Logging** — Should core provide a logging configuration, or leave this to tools?

3. **CLI framework** — Is `argparse` sufficient, or should core provide argument parsing helpers?

4. **Schema validation** — Should core provide formal validators (e.g., Pydantic) or lightweight validate-on-read helpers that produce user-friendly errors and include `valska_version` in messages?

### 9.2 To be resolved during migration

1. **Backwards compatibility** — How long to maintain deprecated imports in tool modules?

2. **Documentation** — Should core have its own API documentation, or integrate with tool docs?

---

## 10. References

- [External Tool Integration Specification](external_tool_integration_spec.md)
- [Tool Implementer's Guide](tool_implementers_guide.md)
- BayesEoR reference implementation: `src/valska_hera_beam/external_tools/bayeseor/`