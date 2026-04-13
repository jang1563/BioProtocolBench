"""Transform-01 sample specification."""

from __future__ import annotations

from pathlib import Path

from .base import TaskPaths

TRANSFORM_01_ROOT = Path(__file__).resolve().parents[2] / "task_data" / "transform_01"
TRANSFORM_01_PATHS = TaskPaths(task_id="transform_01", root=TRANSFORM_01_ROOT)
TRANSFORM_01_GROUND_TRUTH = TRANSFORM_01_PATHS.ground_truth
TRANSFORM_01_RUBRIC = TRANSFORM_01_PATHS.rubric


def build_transform_01_prompt() -> str:
    return """You are operating inside LabCraft, a stochastic microbiology simulator.

Task: Measure transformation efficiency across four plasmid DNA inputs using chemically competent E. coli and ampicillin selection.

Available DNA masses to test:
- 10 pg
- 100 pg
- 1,000 pg
- 10,000 pg

Goal:
1. Prepare appropriate ampicillin selection plates.
2. Run transformations for all four DNA inputs.
3. Plate each transformation at a dilution that produces countable colonies.
4. Count colonies and report CFU/ug for each DNA input.

Important constraints:
- Use only the available lab tools and reference tools.
- Countable results require valid ampicillin selection and enough outgrowth before plating.
- In your final answer, report the CFU/ug values for all four DNA inputs and briefly note whether the runs were internally consistent.
"""


def build_transform_01_sample() -> dict:
    return {
        "id": "transform_01_seeded",
        "input": build_transform_01_prompt(),
        "target": str(TRANSFORM_01_GROUND_TRUTH),
        "metadata": {
            "task_id": "transform_01",
            "ground_truth_path": str(TRANSFORM_01_GROUND_TRUTH),
            "rubric_path": str(TRANSFORM_01_RUBRIC),
        },
    }
