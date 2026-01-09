#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------------------------------------------
# Generate a file containing the directory tree of the repo (or chosen root).
#
# - Uses 'find' with pruning to skip common large/irrelevant directories
# - Supports additional skip patterns passed as positional arguments
# - Can be run from any directory; by default it targets the git repo root
#
# Notes on robustness:
# - This script is written to behave reliably with `set -u` enabled.
# - We avoid referencing unset variables/arrays by declaring them up-front.
# - We keep "core" functionality: root selection, pruning, dirs-only option,
#   optional max-depth, output to a text file.
#
# NOTE ON MAX_DEPTH HANDLING:
# Some bash environments are fussy with `set -u` when expanding an empty array
# (even if declared). To keep things maximally robust, we DO NOT pass an
# "optional args array" into find. Instead we branch on MAX_DEPTH and call find
# with or without `-maxdepth`.
# -----------------------------------------------------------------------------

OUTPUT_FILE="file_structure.txt"

# Default directory-name patterns to skip (shell globs, matched on path components)
# Notes:
# - These are matched by `find -name`, so they apply to individual path components.
# - Keep them broadly applicable; add project-specific noisy dirs as needed.
DEFAULT_SKIP_DIRS=(
  ".git"
  "__pycache__"
  ".pytest_cache"
  ".mypy_cache"
  ".ruff_cache"
  ".ipynb_checkpoints"
  ".venv"
  "venv"
  ".conda"
  "dist"
  "build"
  "site"
  "results*"
  "chains*"
  "old*"
  "logs*"
  "tmp*"
  "temp*"
)

DIRS_ONLY=0
MAX_DEPTH=""     # empty => no max depth
ROOT_DIR=""      # empty => auto-detect (git root)

usage() {
  cat <<EOF
Usage: $0 [OPTIONS] [SKIP_PATTERN ... ]

Generate a file containing the directory tree of this repo.

Output paths are written relative to the chosen root (default: git repo root).

Arguments:
  SKIP_PATTERN          Optional directory-name globs to skip (matched on any
                        path component). If provided, they are used instead of
                        the defaults unless --add-to-defaults is specified.

Options:
  -o, --output FILE     Output file to write (default: ${OUTPUT_FILE})
  -r, --root DIR        Root directory to scan (default: git repo root; fallback: pwd)
  --max-depth N         Limit traversal depth (passed to find as -maxdepth N)
  --dirs-only           Output directories only
  --no-files            Alias for --dirs-only
  --defaults            Use default skip patterns (even if SKIP_PATTERN args exist)
  --add-to-defaults     Add SKIP_PATTERN args in addition to default skips
  -h, --help            Show this help message

Default skip patterns:
  ${DEFAULT_SKIP_DIRS[*]}

Examples:
  $0
  $0 --output structure.txt
  $0 --max-depth 4
  $0 --dirs-only
  $0 "results*" "chains*"
  $0 --add-to-defaults "*.egg-info" ".tox"
EOF
}

die() {
  echo "Error: $*" >&2
  exit 1
}

# --- Parse arguments ----------------------------------------------------------
USE_DEFAULTS=0
ADD_TO_DEFAULTS=0

# Declare arrays up-front for `set -u` robustness
declare -a ARGS=()
declare -a SKIP_DIRS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    -o|--output)
      shift
      [[ $# -gt 0 ]] || die "Missing value for --output"
      OUTPUT_FILE="$1"
      shift
      ;;
    -r|--root)
      shift
      [[ $# -gt 0 ]] || die "Missing value for --root"
      ROOT_DIR="$1"
      shift
      ;;
    --max-depth)
      shift
      [[ $# -gt 0 ]] || die "Missing value for --max-depth"
      MAX_DEPTH="$1"
      shift
      ;;
    --dirs-only|--no-files)
      DIRS_ONLY=1
      shift
      ;;
    --defaults)
      USE_DEFAULTS=1
      shift
      ;;
    --add-to-defaults)
      ADD_TO_DEFAULTS=1
      shift
      ;;
    --) # end of options
      shift
      while [[ $# -gt 0 ]]; do
        ARGS+=("$1")
        shift
      done
      ;;
    -*)
      die "Unknown option: $1 (try --help)"
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
  esac
done

# --- Determine root directory -------------------------------------------------
if [[ -z "${ROOT_DIR}" ]]; then
  if command -v git >/dev/null 2>&1 && git rev-parse --show-toplevel >/dev/null 2>&1; then
    ROOT_DIR="$(git rev-parse --show-toplevel)"
  else
    ROOT_DIR="$(pwd)"
  fi
fi

if [[ ! -d "${ROOT_DIR}" ]]; then
  die "Root directory does not exist: ${ROOT_DIR}"
fi

# --- Determine skip patterns --------------------------------------------------
# If user provides patterns:
# - default: use them instead of defaults
# - --defaults: ignore args and use defaults
# - --add-to-defaults: merge defaults + args
if [[ "${USE_DEFAULTS}" -eq 1 ]]; then
  SKIP_DIRS=("${DEFAULT_SKIP_DIRS[@]}")
elif [[ "${ADD_TO_DEFAULTS}" -eq 1 ]]; then
  SKIP_DIRS=("${DEFAULT_SKIP_DIRS[@]}")
  if [[ "${#ARGS[@]}" -gt 0 ]]; then
    SKIP_DIRS+=("${ARGS[@]}")
  fi
else
  if [[ "${#ARGS[@]}" -gt 0 ]]; then
    SKIP_DIRS=("${ARGS[@]}")
  else
    SKIP_DIRS=("${DEFAULT_SKIP_DIRS[@]}")
  fi
fi

# --- Logging ------------------------------------------------------------------
echo "Generating file structure listing for:"
echo "  ${ROOT_DIR}"
echo "Output will be written to:"
echo "  ${OUTPUT_FILE}"
echo "Skipping directories matching (any path component):"
for pat in "${SKIP_DIRS[@]}"; do
  echo "  - ${pat}"
done
echo

# --- Build prune expression ---------------------------------------------------
declare -a PRUNE_EXPR=()
for pat in "${SKIP_DIRS[@]}"; do
  if [[ "${#PRUNE_EXPR[@]}" -gt 0 ]]; then
    PRUNE_EXPR+=(-o)
  fi
  PRUNE_EXPR+=(-name "${pat}")
done

# --- Run find (relative paths) ------------------------------------------------
# We `cd` into ROOT_DIR and run find on '.' so output is relative.
# This also makes the output stable/portable for sharing.
#
# Using `sort` stabilizes output (useful for diffs); can remove if undesired.
cd "${ROOT_DIR}"

if [[ "${DIRS_ONLY}" -eq 1 ]]; then
  if [[ -n "${MAX_DEPTH}" ]]; then
    echo "Running: (cd \"${ROOT_DIR}\" && find . -maxdepth \"${MAX_DEPTH}\" (pruned) -type d -print | sort > \"${OUTPUT_FILE}\")"
    find . -maxdepth "${MAX_DEPTH}" \( "${PRUNE_EXPR[@]}" \) -prune -o -type d -print \
      | sort > "${OUTPUT_FILE}"
  else
    echo "Running: (cd \"${ROOT_DIR}\" && find . (pruned) -type d -print | sort > \"${OUTPUT_FILE}\")"
    find . \( "${PRUNE_EXPR[@]}" \) -prune -o -type d -print \
      | sort > "${OUTPUT_FILE}"
  fi
else
  if [[ -n "${MAX_DEPTH}" ]]; then
    echo "Running: (cd \"${ROOT_DIR}\" && find . -maxdepth \"${MAX_DEPTH}\" (pruned) -print | sort > \"${OUTPUT_FILE}\")"
    find . -maxdepth "${MAX_DEPTH}" \( "${PRUNE_EXPR[@]}" \) -prune -o -print \
      | sort > "${OUTPUT_FILE}"
  else
    echo "Running: (cd \"${ROOT_DIR}\" && find . (pruned) -print | sort > \"${OUTPUT_FILE}\")"
    find . \( "${PRUNE_EXPR[@]}" \) -prune -o -print \
      | sort > "${OUTPUT_FILE}"
  fi
fi

echo
echo "Done. Wrote $(wc -l < "${OUTPUT_FILE}") entries to ${OUTPUT_FILE}."