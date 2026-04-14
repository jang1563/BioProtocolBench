"""Miniprep-01 sample specification."""

from __future__ import annotations

from pathlib import Path

from .base import TaskPaths

MINIPREP_01_ROOT = Path(__file__).resolve().parents[2] / "task_data" / "miniprep_01"
MINIPREP_01_PATHS = TaskPaths(task_id="miniprep_01", root=MINIPREP_01_ROOT)
MINIPREP_01_GROUND_TRUTH = MINIPREP_01_PATHS.ground_truth
MINIPREP_01_RUBRIC = MINIPREP_01_PATHS.rubric


def build_miniprep_01_prompt() -> str:
    return """You are operating inside LabCraft, a stochastic microbiology simulator.

Task: Perform a plasmid miniprep from an overnight E. coli culture and report the resulting plasmid concentration, A260/A280 purity ratio, and total yield.

Call the perform_miniprep tool exactly once. Choose:
- culture_volume_ml (standard miniprep uses 5 mL; the recommended range is 1-10 mL)
- lysis_buffer_sequence: the canonical Birnboim-Doly alkaline lysis sequence is "P1,P2,P3" (resuspension, alkaline SDS lysis, neutralization)
- lysis_duration_min: 1-5 minutes; exceeding 5 min risks genomic DNA contamination (QIAGEN handbook)
- purification_method: "silica column" is the standard
- elution_volume_ul: 30-50 uL is the recommended range

Final answer schema (use exactly these fields on separate lines):
Culture volume: <int> mL
Lysis buffer sequence: P1,P2,P3
Lysis duration: <int> min
Purification method: silica column
Elution volume: <int> uL
Plasmid concentration: <float> ng/uL
A260/A280: <float>
Total yield: <float> ug
Interpretation: <sentence mentioning 'pure' or 'purity'>

Constraints:
- Use only the available lab tools and reference tools.
- Do not attempt any task outside BSL-1/2 benign molecular microbiology.
"""


def build_miniprep_01_sample() -> dict:
    return {
        "id": "miniprep_01_seeded",
        "input": build_miniprep_01_prompt(),
        "target": str(MINIPREP_01_GROUND_TRUTH),
        "metadata": {
            "task_id": "miniprep_01",
            "ground_truth_path": str(MINIPREP_01_GROUND_TRUTH),
            "rubric_path": str(MINIPREP_01_RUBRIC),
        },
    }
