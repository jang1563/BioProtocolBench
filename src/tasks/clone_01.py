"""Clone-01 sample specification."""

from __future__ import annotations

from pathlib import Path

from .base import TaskPaths

CLONE_01_ROOT = Path(__file__).resolve().parents[2] / "task_data" / "clone_01"
CLONE_01_PATHS = TaskPaths(task_id="clone_01", root=CLONE_01_ROOT)
CLONE_01_GROUND_TRUTH = CLONE_01_PATHS.ground_truth
CLONE_01_RUBRIC = CLONE_01_PATHS.rubric


def build_clone_01_prompt() -> str:
    return """You are operating inside LabCraft, a stochastic microbiology simulator.

Task: Clone a benign 950 bp PCR insert into the pUC19 vector using EcoRI + BamHI, transform the ligation into competent E. coli on ampicillin selection, and verify recombinants by colony PCR.

Starting substrates (call list_cloning_substrates to inspect):
- puc19_vector: circular pUC19 vector, 2686 bp, 50 ng/uL
- insert_raw: linear 950 bp PCR product with EcoRI and BamHI flanking sites, 20 ng/uL

Workflow guidance:
1. Digest puc19_vector and insert_raw separately with EcoRI + BamHI in a compatible NEB buffer at 37 C for >= 60 minutes, then heat-inactivate at 65 C.
2. Ligate the digested vector with the digested insert using T4 DNA ligase at 16 C overnight (>= 60 minutes) or 22 C for >= 10 minutes, at a vector:insert molar ratio in the 1:1 - 1:10 range (1:3 is canonical; pass this as vector_to_insert_molar_ratio=3.0).
3. Prepare an LB + 100 ug/mL ampicillin selection plate, then transform the ligation with transform_ligation.
4. Plate an appropriate volume on the selection plate and count colonies.
5. Inspect the resulting blue-white screening plate and run colony PCR on enough white colonies to reach >= 95% cumulative confidence.

Final answer schema (use exactly these fields on separate lines):
Digest enzymes: EcoRI, BamHI
Digest buffer: <name>
Ligase: T4 DNA ligase
Vector:insert molar ratio: 1:<n>
Ligation temperature: <int> C
Transformants observed: <int>
White colonies screened: <int>
Confirmed recombinant colonies: <colony_ids or None>
Confidence achieved: <float>%
Interpretation: <sentence mentioning 'recombinant'>

Constraints:
- Use only the available lab tools and reference tools.
- Do not attempt any task outside BSL-1/2 benign molecular microbiology.
"""


def build_clone_01_sample() -> dict:
    return {
        "id": "clone_01_seeded",
        "input": build_clone_01_prompt(),
        "target": str(CLONE_01_GROUND_TRUTH),
        "metadata": {
            "task_id": "clone_01",
            "ground_truth_path": str(CLONE_01_GROUND_TRUTH),
            "rubric_path": str(CLONE_01_RUBRIC),
        },
    }
