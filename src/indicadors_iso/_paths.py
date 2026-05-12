"""Single source of truth for repo-relative filesystem paths.

`indicadors_iso` lives under `<REPO_ROOT>/src/indicadors_iso/`, so anchoring on
this file gives a stable reference regardless of which entry-point (real script
or backward-compat shim) the user invokes.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO_ROOT / "output"
DICTIONARIES_DIR = REPO_ROOT / "dictionaries"


def module_output_dir(*parts: str) -> Path:
    """Return (and create) the canonical output directory for a module.

    Example:
        module_output_dir("demographics", "per_unit")
        -> <repo>/output/demographics/per_unit/
    """
    path = OUTPUT_DIR.joinpath(*parts)
    path.mkdir(parents=True, exist_ok=True)
    return path


__all__ = ["REPO_ROOT", "OUTPUT_DIR", "DICTIONARIES_DIR", "module_output_dir"]
