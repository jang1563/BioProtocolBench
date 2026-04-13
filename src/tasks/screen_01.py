"""Screen-01 sample specification."""

from __future__ import annotations

from pathlib import Path

from .base import TaskPaths

SCREEN_01_ROOT = Path(__file__).resolve().parents[2] / "task_data" / "screen_01"
SCREEN_01_PATHS = TaskPaths(task_id="screen_01", root=SCREEN_01_ROOT)
SCREEN_01_GROUND_TRUTH = SCREEN_01_PATHS.ground_truth
SCREEN_01_RUBRIC = SCREEN_01_PATHS.rubric


def build_screen_01_prompt() -> str:
    return """You are operating inside LabCraft, a stochastic microbiology simulator.

Task: Screen a benign pUC-style blue-white cloning plate to identify recombinant colonies.

Screening context:
- Insert size for this task: 950 bp benign fragment
- Historical fraction of correct inserts among white colonies for this ligation: 40%
- Target confidence before stopping: >=95% probability of finding at least one correct recombinant colony
- Colony PCR interpretation for this task:
  - Recombinant clone: band near 1200 bp
  - Empty vector/background clone: band near 250 bp

Goal:
1. Inspect the plate and choose which colonies to screen.
2. Prioritize white colonies over blue colonies.
3. Use colony PCR on enough white colonies to reach the confidence target.
4. Report which colonies are confirmed recombinants.

Important constraints:
- Use only the available lab tools and reference tools.
- Keep the workflow efficient and do not screen unnecessary blue colonies.
- In the final answer, use exactly these fields:
  White colonies screened: ...
  Confirmed recombinant colonies: ...
  Confidence achieved: ...%
  Interpretation: ...
"""


def build_screen_01_sample() -> dict:
    return {
        "id": "screen_01_seeded",
        "input": build_screen_01_prompt(),
        "target": str(SCREEN_01_GROUND_TRUTH),
        "metadata": {
            "task_id": "screen_01",
            "ground_truth_path": str(SCREEN_01_GROUND_TRUTH),
            "rubric_path": str(SCREEN_01_RUBRIC),
        },
    }
