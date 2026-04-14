"""Golden Gate-01 sample specification."""

from __future__ import annotations

from pathlib import Path

from .base import TaskPaths

GOLDEN_GATE_01_ROOT = Path(__file__).resolve().parents[2] / "task_data" / "golden_gate_01"
GOLDEN_GATE_01_PATHS = TaskPaths(task_id="golden_gate_01", root=GOLDEN_GATE_01_ROOT)
GOLDEN_GATE_01_GROUND_TRUTH = GOLDEN_GATE_01_PATHS.ground_truth
GOLDEN_GATE_01_RUBRIC = GOLDEN_GATE_01_PATHS.rubric


def build_golden_gate_01_prompt() -> str:
    return """You are operating inside LabCraft, a stochastic microbiology simulator.

Task: Assemble a four-fragment construct using Golden Gate one-pot Type IIS cloning, transform it into E. coli, plate on ampicillin selection, and report the outcome.

Starting substrates (call list_golden_gate_substrates to inspect):
- gg_backbone: linear Golden Gate destination vector, BsaI overhangs A and D
- gg_insert_promoter: insert 1, BsaI overhangs A and B
- gg_insert_cds: insert 2, BsaI overhangs B and C
- gg_insert_terminator: insert 3, BsaI overhangs C and D

Workflow guidance:
1. Choose a Type IIS enzyme (BsaI is canonical; BsmBI is an acceptable alternative) and T4 DNA ligase.
2. Cycle at 37 C (digest) / 16 C (ligate) for at least 25 cycles, followed by a final heat-kill at 60 C.
3. Transform the assembled construct into competent E. coli using transform_assembly.
4. Prepare an LB + 100 ug/mL ampicillin selection plate and plate an appropriate volume.
5. Count transformants.

Final answer schema (use exactly these fields on separate lines):
Type IIS enzyme: BsaI
Ligase: T4 DNA ligase
Digest temperature: 37 C
Ligate temperature: 16 C
Cycle count: <int>
Fragment count: 4
Transformants observed: <int>
Interpretation: <sentence mentioning 'assembly' or 'assembled'>

Constraints:
- Use only the available lab tools and reference tools.
- Do not attempt any task outside BSL-1/2 benign molecular microbiology.
"""


def build_golden_gate_01_sample() -> dict:
    return {
        "id": "golden_gate_01_seeded",
        "input": build_golden_gate_01_prompt(),
        "target": str(GOLDEN_GATE_01_GROUND_TRUTH),
        "metadata": {
            "task_id": "golden_gate_01",
            "ground_truth_path": str(GOLDEN_GATE_01_GROUND_TRUTH),
            "rubric_path": str(GOLDEN_GATE_01_RUBRIC),
        },
    }
