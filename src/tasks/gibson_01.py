"""Gibson-01 sample specification."""

from __future__ import annotations

from pathlib import Path

from .base import TaskPaths

GIBSON_01_ROOT = Path(__file__).resolve().parents[2] / "task_data" / "gibson_01"
GIBSON_01_PATHS = TaskPaths(task_id="gibson_01", root=GIBSON_01_ROOT)
GIBSON_01_GROUND_TRUTH = GIBSON_01_PATHS.ground_truth
GIBSON_01_RUBRIC = GIBSON_01_PATHS.rubric


def build_gibson_01_prompt() -> str:
    return """You are operating inside LabCraft, a stochastic microbiology simulator.

Task: Assemble a two-fragment construct using Gibson isothermal overlap assembly, transform it into E. coli, plate on ampicillin, and report the outcome.

Starting substrates (call list_gibson_substrates to inspect):
- gibson_backbone_linear: linearised destination vector with 20 bp homology overhangs
- gibson_insert_pcr: PCR insert with matching 20 bp homology overhangs

Workflow guidance:
1. Choose a Gibson master mix (e.g., "Gibson Assembly Master Mix" or "NEBuilder HiFi"). These contain T5 exonuclease + Phusion polymerase + Taq ligase.
2. Incubate isothermally at 50 C for at least 15 minutes (the canonical 2-fragment Gibson condition).
3. Transform the assembled construct into competent E. coli via transform_gibson.
4. Prepare an LB + 100 ug/mL ampicillin selection plate and plate an appropriate volume.
5. Count transformants.

Final answer schema (use exactly these fields on separate lines):
Assembly method: Gibson
Master mix: <name>
Temperature: 50 C
Duration: <int> min
Fragment count: 2
Overlap length: <int> bp
Transformants observed: <int>
Interpretation: <sentence mentioning 'assembly' or 'assembled'>

Constraints:
- Use only the available lab tools and reference tools.
- Do not attempt any task outside BSL-1/2 benign molecular microbiology.
"""


def build_gibson_01_sample() -> dict:
    return {
        "id": "gibson_01_seeded",
        "input": build_gibson_01_prompt(),
        "target": str(GIBSON_01_GROUND_TRUTH),
        "metadata": {
            "task_id": "gibson_01",
            "ground_truth_path": str(GIBSON_01_GROUND_TRUTH),
            "rubric_path": str(GIBSON_01_RUBRIC),
        },
    }
