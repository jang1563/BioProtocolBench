"""Target-validation task specification."""

from __future__ import annotations

from pathlib import Path

from .base import TaskPaths

TARGET_VALIDATE_01_ROOT = Path(__file__).resolve().parents[2] / "task_data" / "target_validate_01"
TARGET_VALIDATE_01_PATHS = TaskPaths(task_id="target_validate_01", root=TARGET_VALIDATE_01_ROOT)
TARGET_VALIDATE_01_GROUND_TRUTH = TARGET_VALIDATE_01_PATHS.ground_truth
TARGET_VALIDATE_01_RUBRIC = TARGET_VALIDATE_01_PATHS.rubric


def build_target_validate_01_prompt() -> str:
    return """You are operating inside the Discovery Decision Track, a deterministic perturbation-discovery evaluation environment.

Task: Choose the best first de-risking experiment for the leading candidate from the current discovery program and interpret the result.

Program note:
- The current leading candidate is TGT_A.

Goal:
1. Inspect the full profile for TGT_A.
2. Review the available validation assays.
3. Run exactly one assay.
4. Decide whether the program should advance or hold after seeing the result.

Final answer schema (use exactly these fields on separate lines):
Validation assay: <assay_id>
Primary readout: <string>
Decision: <advance|hold>
Interpretation: <one sentence>

Constraints:
- Use exactly one validation assay run.
- Prefer the best first orthogonal de-risking experiment for the candidate.
- Keep the workflow concise and evidence-driven.
"""


def build_target_validate_01_sample() -> dict:
    return {
        "id": "target_validate_01_seeded",
        "input": build_target_validate_01_prompt(),
        "target": str(TARGET_VALIDATE_01_GROUND_TRUTH),
        "metadata": {
            "task_id": "target_validate_01",
            "ground_truth_path": str(TARGET_VALIDATE_01_GROUND_TRUTH),
            "rubric_path": str(TARGET_VALIDATE_01_RUBRIC),
        },
    }
