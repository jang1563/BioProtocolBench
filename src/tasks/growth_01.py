"""Growth-01 sample specification."""

from __future__ import annotations

from pathlib import Path

from .base import TaskPaths

GROWTH_01_ROOT = Path(__file__).resolve().parents[2] / "task_data" / "growth_01"
GROWTH_01_PATHS = TaskPaths(task_id="growth_01", root=GROWTH_01_ROOT)
GROWTH_01_GROUND_TRUTH = GROWTH_01_PATHS.ground_truth
GROWTH_01_RUBRIC = GROWTH_01_PATHS.rubric


def build_growth_01_prompt() -> str:
    return """You are operating inside LabCraft, a stochastic microbiology simulator.

Task: Characterize early exponential E. coli growth across three conditions using OD600 measurements.

Conditions to test:
- LB
- M9 + glucose
- LB + chloramphenicol (1.8 uM)

Goal:
1. Inoculate all three conditions at the cited starting OD600.
2. Collect OD600 measurements at regular 15-minute intervals until each condition has enough usable points for an analyzable fit.
3. Use dilution when helpful so the growth-fit tool has enough usable OD600 points.
4. Run the growth-fit tool for each condition.
5. In your final answer, report the estimated doubling time for each condition and rank them from fastest to slowest.

Important constraints:
- Use the labels exactly as written above in the final answer.
- Use only the available lab tools and reference tools.
- The fit tool needs enough OD600 measurements in the cited fitting window to return an analyzable result.
- Batch tool calls across conditions whenever practical to avoid unnecessary turns.
- Do not stop to summarize after each interval; keep moving through the required tool batches until all conditions have analyzable fits.
"""


def build_growth_01_sample() -> dict:
    return {
        "id": "growth_01_seeded",
        "input": build_growth_01_prompt(),
        "target": str(GROWTH_01_GROUND_TRUTH),
        "metadata": {
            "task_id": "growth_01",
            "ground_truth_path": str(GROWTH_01_GROUND_TRUTH),
            "rubric_path": str(GROWTH_01_RUBRIC),
        },
    }
