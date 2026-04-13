"""PCR-01 sample specification."""

from __future__ import annotations

from pathlib import Path

from .base import TaskPaths

PCR_01_ROOT = Path(__file__).resolve().parents[2] / "task_data" / "pcr_01"
PCR_01_PATHS = TaskPaths(task_id="pcr_01", root=PCR_01_ROOT)
PCR_01_GROUND_TRUTH = PCR_01_PATHS.ground_truth
PCR_01_RUBRIC = PCR_01_PATHS.rubric


def build_pcr_01_prompt() -> str:
    return """You are operating inside LabCraft, a stochastic microbiology simulator.

Task: Optimize PCR for a benign GC-rich E. coli genomic target.

Target properties:
- Expected amplicon size: ~2 kb
- Template: E. coli genomic DNA
- GC content: ~70%

Goal:
1. Choose a polymerase appropriate for a difficult GC-rich genomic amplicon.
2. Choose whether to use a GC-rich PCR additive.
3. Run one or more PCR attempts, adjusting extension time and cycle count as needed.
4. Run a gel for the PCR attempts you want to interpret.
5. Identify the condition that yields a single clean ~2 kb band.

Important constraints:
- Use only the available lab tools and reference tools.
- Prefer lookup_enzyme and lookup_reagent if you need polymerase or additive guidance.
- Keep iterating until you either obtain a single clean 2 kb band or have a clear failure diagnosis.
- When run_pcr returns a reaction_id, pass that exact reaction_id string into run_gel.
- In the final answer, use exactly these fields:
  Polymerase: ...
  Additive: ...
  Extension: ... seconds
  Cycles: ...
  Result: single clean 2 kb band / not achieved
"""


def build_pcr_01_sample() -> dict:
    return {
        "id": "pcr_01_seeded",
        "input": build_pcr_01_prompt(),
        "target": str(PCR_01_GROUND_TRUTH),
        "metadata": {
            "task_id": "pcr_01",
            "ground_truth_path": str(PCR_01_GROUND_TRUTH),
            "rubric_path": str(PCR_01_RUBRIC),
        },
    }
