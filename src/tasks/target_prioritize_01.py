"""Target-prioritization task specification."""

from __future__ import annotations

from pathlib import Path

from .base import TaskPaths

TARGET_PRIORITIZE_01_ROOT = Path(__file__).resolve().parents[2] / "task_data" / "target_prioritize_01"
TARGET_PRIORITIZE_01_PATHS = TaskPaths(task_id="target_prioritize_01", root=TARGET_PRIORITIZE_01_ROOT)
TARGET_PRIORITIZE_01_GROUND_TRUTH = TARGET_PRIORITIZE_01_PATHS.ground_truth
TARGET_PRIORITIZE_01_RUBRIC = TARGET_PRIORITIZE_01_PATHS.rubric


def build_target_prioritize_01_prompt() -> str:
    return """You are operating inside the Discovery Decision Track, a deterministic perturbation-discovery evaluation environment.

Task: Triage four candidate targets for an inflammatory-disease discovery program.

Goal:
1. Inspect the candidate summaries.
2. Look up the full profile for every target before deciding.
3. Pick one top target to advance.
4. Pick one target that should not be advanced because it is the clearest immediate no-go.
5. Explain the main advance rationale and the main remaining risk for the top target.

Final answer schema (use exactly these fields on separate lines):
Top target: <target_id>
Do-not-advance target: <target_id>
Advance reason: <one sentence>
Main risk: <one sentence about the remaining risk for the top target>

Constraints:
- You must inspect all four target profiles before deciding.
- One candidate is intentionally ambiguous and is better handled by follow-up than by using the do-not-advance slot.
- Base the decision on perturbation signal, context consistency, translational support, and liability risk.
- Do not run validation assays in this task.
"""


def build_target_prioritize_01_sample() -> dict:
    return {
        "id": "target_prioritize_01_seeded",
        "input": build_target_prioritize_01_prompt(),
        "target": str(TARGET_PRIORITIZE_01_GROUND_TRUTH),
        "metadata": {
            "task_id": "target_prioritize_01",
            "ground_truth_path": str(TARGET_PRIORITIZE_01_GROUND_TRUTH),
            "rubric_path": str(TARGET_PRIORITIZE_01_RUBRIC),
        },
    }
