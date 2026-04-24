"""Perturb-followup task specification."""

from __future__ import annotations

from pathlib import Path

from .base import TaskPaths

PERTURB_FOLLOWUP_01_ROOT = Path(__file__).resolve().parents[2] / "task_data" / "perturb_followup_01"
PERTURB_FOLLOWUP_01_PATHS = TaskPaths(task_id="perturb_followup_01", root=PERTURB_FOLLOWUP_01_ROOT)
PERTURB_FOLLOWUP_01_GROUND_TRUTH = PERTURB_FOLLOWUP_01_PATHS.ground_truth
PERTURB_FOLLOWUP_01_RUBRIC = PERTURB_FOLLOWUP_01_PATHS.rubric


def build_perturb_followup_01_prompt() -> str:
    return """You are operating inside the Discovery Decision Track, a deterministic perturbation-discovery evaluation environment.

Task: Resolve one ambiguous candidate from a short perturbation shortlist using the minimum orthogonal follow-up.

Program context:
- Indication: inflammatory disease
- The candidate set contains four synthetic targets with different balances of perturbation strength, translation support, and liability risk
- One shortlisted perturbation effect is promising but ambiguous because the primary screen and QC disagree

Goal:
1. Inspect the candidate summaries.
2. Identify the ambiguous target that most needs a focused orthogonal follow-up.
3. Review the validation-assay menu.
4. Run exactly one orthogonal assay on exactly one target.
5. Decide whether the candidate should be kept or dropped.

Final answer schema (use exactly these fields on separate lines):
Chosen target: <target_id>
Follow-up assay: <assay_id>
Result: <pass|fail>
Decision: <keep|drop>
Interpretation: <one sentence>

Constraints:
- Use the minimum necessary tool path.
- Do not run more than one validation assay.
- Treat this as a decision-quality task, not a broad exploration task.
"""


def build_perturb_followup_01_sample() -> dict:
    return {
        "id": "perturb_followup_01_seeded",
        "input": build_perturb_followup_01_prompt(),
        "target": str(PERTURB_FOLLOWUP_01_GROUND_TRUTH),
        "metadata": {
            "task_id": "perturb_followup_01",
            "ground_truth_path": str(PERTURB_FOLLOWUP_01_GROUND_TRUTH),
            "rubric_path": str(PERTURB_FOLLOWUP_01_RUBRIC),
        },
    }
