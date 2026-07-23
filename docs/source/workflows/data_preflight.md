# Pre-flight data checks (`valska-data-preflight`)

## Purpose and limitations

`valska-data-preflight` runs cheap, self-contained checks against UVH5 visibility
files before they are used in an expensive analysis (e.g. a BayesEoR sweep), so that
inconsistencies in a file's recorded metadata can be caught early rather than
discovered after the analysis has already run.

The checks compare pieces of **recorded metadata against each other** — for
example, whether a file's own name agrees with the beam type declared by the
telescope config its `pyuvsim` history cites. This is **provenance-consistency
checking, not proof of what a file's data actually contain**:

- the recorded `history` string may itself be inaccurate or stale;
- a config file located by name in the search directories may not be
  byte-identical to whatever configuration was actually in effect at
  simulation time;
- agreement between a file's name and its cited config is useful supporting
  evidence, not a guarantee; disagreement is a strong, actionable signal to
  investigate before using the file, not proof that nothing else is wrong.

Only fast, header-only checks are implemented currently (the `fast` tier: see
`valska.data_preflight.registry.CheckTier`). A reference-file comparison tier and
a `hera_pspec`-based delay-domain diagnostic tier are anticipated but not yet
built.

## Advisory versus strict behaviour, and exit codes

The **scientific checks** (e.g. `beam_type_consistency`, `metadata_summary`) are
advisory only by default: a run always exits `0` regardless of PASS/WARN/FAIL/SKIP
results. Pass `--strict` to exit non-zero if any scientific check result is FAIL,
for use as a script-level gate.

`metadata_summary` reports `FAIL` when any required UVH5 header field is absent.
This remains advisory without `--strict`, while strict mode can therefore reject
structurally incomplete files.

**Input-discovery and file-read problems are a separate matter** and always
produce a non-zero exit, independent of `--strict`, so they cannot be silently
missed:

| Exit code | Meaning |
| --- | --- |
| `0` | Clean run: every requested path existed, every discovered file was read successfully, and (if `--strict`) no scientific check FAILed. |
| `1` | `--strict` was passed and at least one scientific check FAILed. Only reached when there were no missing paths or read errors (those take precedence). |
| `2` | Every requested path existed, but none contained (or was) a `.uvh5` file, so there was nothing to check. |
| `3` | One or more requested paths did not exist, and/or one or more discovered files failed to read (e.g. corrupt file, missing `Header` group, unreadable scalar field). Independent of `--strict`. Other requested paths that did exist, and other files that did read successfully, are still processed and reported. |

A requested path that exists but is an empty directory (or one with no `.uvh5`
files) is not treated as "missing" — it was found, it simply contributed no
files.

A file reachable via more than one requested path (passed directly and also
matched by scanning a parent directory, or passed twice) is only inspected and
reported once.

## Configuration-search precedence

`beam_type_consistency` needs to locate the telescope config file(s) a UVH5
file's history cites, by filename, in an ordered list of search directories:

1. Any directories passed via `--config-search-dir` (may be repeated), in the
   order given.
2. This repository's own shipped `pyuvsim` telescope configs
   (`valska.external_tools.pyuvsim`'s packaged `templates/telescope_config`
   directory and its parent `templates` directory), appended after any
   `--config-search-dir` directories.

The first directory in this combined, ordered list containing a file with the
cited name is used. If a cited config file cannot be located in any search
directory, the check reports `WARN` (not `FAIL`) for that citation, since the
beam type genuinely cannot be confirmed from the information available.

## Usage

### Single file

```bash
valska-data-preflight path/to/file.uvh5
```

### Single file, with an expected beam type

```bash
valska-data-preflight path/to/file.uvh5 --expected-beam-type airy
```

Flags the file if its cited config declares a beam type other than the one
given, in addition to the filename-versus-config check. Most useful when you
already know what beam type a file is supposed to have.

### Recursive directory scan

```bash
valska-data-preflight path/to/directory
```

Recurses into the directory and checks every `*.uvh5` file found.

### Multiple paths, mixing files and directories

```bash
valska-data-preflight path/to/file.uvh5 path/to/directory --config-search-dir extra/configs
```

### JSON output

```bash
valska-data-preflight path/to/directory --json
```

Prints a single JSON object instead of text:

```json
{
  "schema_version": 1,
  "missing_paths": ["path/to/nonexistent.uvh5"],
  "reports": [
    {
      "path": "path/to/file.uvh5",
      "error": null,
      "checks": [
        {
          "check_id": "beam_type_consistency",
          "status": "fail",
          "message": "file name claims beam type(s) ['airy'], but its cited telescope config declares 'gaussian'",
          "details": {"...": "..."}
        }
      ]
    }
  ]
}
```

`schema_version` identifies the machine-readable output contract. Consumers
should reject unsupported versions rather than assuming a compatible shape.
`missing_paths` lists any requested path that did not exist. Each entry in
`reports` corresponds to one discovered file; `error` is non-null (and
`checks` empty) if the file could not be read at all.

The JSON object is still emitted when no files can be inspected, including
missing-only inputs (exit `3`) and existing paths containing no `.uvh5` files
(exit `2`). In those cases, `reports` is empty.

### Strict mode (script-level gate)

```bash
valska-data-preflight path/to/directory --strict
```

Exits `1` if any scientific check FAILed (see the exit-code table above for how
this interacts with missing paths and read errors).

## Example scan and its limits

A scan of the full `UKSRC_val_mock_vis` tree run on 2026-07-23 (152 `.uvh5`
files) reported, for `beam_type_consistency`: 31 files whose name and
history-cited config disagreed on beam type (FAIL), 93 files where the cited
config could not be located so the beam type could not be confirmed either way
(WARN), 25 files where name and cited config agreed (PASS), and 3 files with
no config citation in history (SKIP). These are the counts from one specific
scan on one specific date, over one specific directory tree — **not** a claim
that no other beam-type mismatches exist anywhere, including within the 93
WARN cases that could not be checked, or in files/directories not included in
that scan.

## See also

- [`valska.data_preflight`](../generated/valska.data_preflight.rst) — API
  reference (check registry, individual checks, header inspection).
- [Verifying prepared outputs](verifying_prepared_outputs.md) — a related,
  narrower checker for `valska-bayeseor-prepare` outputs specifically.
