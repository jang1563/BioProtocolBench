"""Express-01 sample specification."""

from __future__ import annotations

from pathlib import Path

from .base import TaskPaths

EXPRESS_01_ROOT = Path(__file__).resolve().parents[2] / "task_data" / "express_01"
EXPRESS_01_PATHS = TaskPaths(task_id="express_01", root=EXPRESS_01_ROOT)
EXPRESS_01_GROUND_TRUTH = EXPRESS_01_PATHS.ground_truth
EXPRESS_01_RUBRIC = EXPRESS_01_PATHS.rubric


def build_express_01_prompt() -> str:
    return """You are operating inside LabCraft, a stochastic microbiology simulator.

Task: Perform a single IPTG-induced recombinant protein expression of a benign MBP-GFP fusion (~72 kDa) in a T7 expression host, then lyse for Ni-NTA downstream purification. Report soluble yield in mg/L.

Call the run_protein_expression tool exactly once with your chosen conditions. Key decisions:
- host_strain: a T7 expression host, e.g., BL21(DE3), BL21(DE3) pLysS, Rosetta(DE3).
- iptg_concentration_mm: 0.1 - 1 mM is the canonical range; 1 mM is textbook-standard.
- induction_od600: induce at mid-log (0.4 - 0.8); OD600 = 0.6 is canonical.
- induction_temperature_c: 37 C for fast induction or 18-25 C for overnight low-temperature induction (better for fusion-protein solubility).
- induction_hours: 3-5 h at 37 C, or 12-18 h overnight at 18 C.
- lysis_buffer_ph: 7.0-8.0 for Ni-NTA-compatible lysis; pH 8.0 is standard.

Final answer schema (use exactly these fields on separate lines):
Host strain: <strain>
IPTG concentration: <float> mM
Induction OD600: <float>
Induction temperature: <int> C
Induction duration: <float> h
Lysis buffer pH: <float>
Expected soluble yield: <float> mg/L
Interpretation: <sentence mentioning 'expression'>

Constraints:
- Use only the available lab tools and reference tools.
- The target protein is a benign MBP-GFP fusion; do not attempt expression of toxins, cytokines, or any protein outside the benign reporter / model-enzyme scope.
"""


def build_express_01_sample() -> dict:
    return {
        "id": "express_01_seeded",
        "input": build_express_01_prompt(),
        "target": str(EXPRESS_01_GROUND_TRUTH),
        "metadata": {
            "task_id": "express_01",
            "ground_truth_path": str(EXPRESS_01_GROUND_TRUTH),
            "rubric_path": str(EXPRESS_01_RUBRIC),
        },
    }
