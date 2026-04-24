"""Purify-01 sample specification."""

from __future__ import annotations

from pathlib import Path

from .base import TaskPaths

PURIFY_01_ROOT = Path(__file__).resolve().parents[2] / "task_data" / "purify_01"
PURIFY_01_PATHS = TaskPaths(task_id="purify_01", root=PURIFY_01_ROOT)
PURIFY_01_GROUND_TRUTH = PURIFY_01_PATHS.ground_truth
PURIFY_01_RUBRIC = PURIFY_01_PATHS.rubric


def build_purify_01_prompt() -> str:
    return """You are operating inside LabCraft, a stochastic microbiology simulator.

Task: Purify a His-tagged benign MBP-GFP fusion (~72 kDa) from a clarified E. coli lysate by Ni-NTA affinity chromatography, then report the purified concentration, SDS-PAGE band result, and purity percentage.

Call the run_nta_purification tool exactly once with your chosen conditions. Key decisions:
- resin_name: a Ni-NTA-family resin (e.g., "Ni-NTA", "HisPur Ni-NTA", "HisTrap HP").
- load_imidazole_mm: 10-20 mM in the load buffer reduces non-specific binding (QIAexpressionist handbook).
- wash_imidazole_mm: 40-60 mM in the wash buffer removes contaminants without eluting the target.
- elute_imidazole_mm: >= 200 mM to displace the His-tag (250 mM is canonical).
- flow_rate_ml_per_min: 1 mL/min is standard for a 1 mL bed volume.
- column_bed_volume_ml: 1 mL for analytical scale.

Final answer schema (use exactly these fields on separate lines):
Resin: Ni-NTA
Load imidazole: <int> mM
Wash imidazole: <int> mM
Elute imidazole: <int> mM
Expected band size: 72 kDa
Purified concentration: <float> mg/mL
SDS-PAGE result: <verbatim from tool, e.g., single_clean_band_at_72_kDa>
Purity: <float>%
Interpretation: <sentence mentioning 'pure' or 'purity' or 'purification'>

Constraints:
- Use only the available lab tools and reference tools.
- The target protein is a benign MBP-GFP fusion; do not attempt purification of toxins, cytokines, or any out-of-scope protein.
"""


def build_purify_01_sample() -> dict:
    return {
        "id": "purify_01_seeded",
        "input": build_purify_01_prompt(),
        "target": str(PURIFY_01_GROUND_TRUTH),
        "metadata": {
            "task_id": "purify_01",
            "ground_truth_path": str(PURIFY_01_GROUND_TRUTH),
            "rubric_path": str(PURIFY_01_RUBRIC),
        },
    }
