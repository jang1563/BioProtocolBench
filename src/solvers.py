"""Solver helpers for LabCraft."""

from __future__ import annotations

from .prompts import DISCOVERY_SYSTEM_PROMPT, LABCRAFT_SYSTEM_PROMPT
from .tools.discovery import set_active_discovery_sample
from .tools.lab_tools import set_active_sample

try:
    from inspect_ai.solver import solver
except ImportError:  # pragma: no cover - only used when Inspect is unavailable locally.
    def solver(func):
        return func


def build_labcraft_solver():
    """Build the LabCraft solver chain using Inspect AI if available."""
    from inspect_ai.agent import react

    from .tools.lab_tools import (
        count_colonies_tool,
        fit_growth_curve_tool,
        incubate_tool,
        inoculate_growth_tool,
        measure_od600_tool,
        plate_tool,
        prepare_media_tool,
        transform_tool,
    )
    from .tools.reference import check_safety_tool, lookup_enzyme_tool, lookup_reagent_tool

    return react(
        prompt=LABCRAFT_SYSTEM_PROMPT,
        tools=[
            lookup_reagent_tool(),
            lookup_enzyme_tool(),
            check_safety_tool(),
            prepare_media_tool(),
            transform_tool(),
            plate_tool(),
            count_colonies_tool(),
            inoculate_growth_tool(),
            incubate_tool(),
            measure_od600_tool(),
            fit_growth_curve_tool(),
        ],
    )


def build_growth_solver():
    """Build the Growth-01 solver chain with only growth-relevant tools."""
    from inspect_ai.agent import AgentPrompt, react

    from .tools.lab_tools import (
        fit_growth_curve_tool,
        incubate_tool,
        inoculate_growth_tool,
        measure_od600_tool,
    )
    from .tools.reference import check_safety_tool, lookup_reagent_tool

    return react(
        prompt=AgentPrompt(
            instructions=LABCRAFT_SYSTEM_PROMPT,
            assistant_prompt=(
                "\nUse the minimum necessary text between tool calls. "
                "Do not restate intermediate observations after each interval. "
                "Continue directly to the next required tool batch until the "
                "experiment is complete, then provide the final answer.\n"
            ),
        ),
        tools=[
            lookup_reagent_tool(),
            check_safety_tool(),
            inoculate_growth_tool(),
            incubate_tool(),
            measure_od600_tool(),
            fit_growth_curve_tool(),
        ],
    )


def build_followup_solver():
    """Build the Followup-01 solver chain for targeted growth follow-up."""
    from inspect_ai.agent import AgentPrompt, react

    from .tools.lab_tools import (
        fit_growth_curve_tool,
        incubate_tool,
        inoculate_growth_tool,
        measure_od600_tool,
    )
    from .tools.reference import check_safety_tool, lookup_reagent_tool

    return react(
        prompt=AgentPrompt(
            instructions=LABCRAFT_SYSTEM_PROMPT,
            assistant_prompt=(
                "\nBe concise between tool calls. Treat this as a targeted follow-up: "
                "focus on the ambiguous chloramphenicol condition, keep the tool path "
                "minimal, and continue collecting OD600 data until the final fit is analyzable "
                "before giving the conclusion.\n"
            ),
        ),
        tools=[
            lookup_reagent_tool(),
            check_safety_tool(),
            inoculate_growth_tool(),
            incubate_tool(),
            measure_od600_tool(),
            fit_growth_curve_tool(),
        ],
    )


def build_pcr_solver():
    """Build the PCR-01 solver chain with only PCR-relevant tools."""
    from inspect_ai.agent import AgentPrompt, react

    from .tools.lab_tools import run_gel_tool, run_pcr_tool
    from .tools.reference import check_safety_tool, lookup_enzyme_tool, lookup_reagent_tool

    return react(
        prompt=AgentPrompt(
            instructions=LABCRAFT_SYSTEM_PROMPT,
            assistant_prompt=(
                "\nUse the minimum necessary text between tool calls. "
                "Do not restate intermediate gel or PCR observations unless they "
                "change the next decision. Continue iterating until you either "
                "obtain the target band or have a clear failure diagnosis, then "
                "provide the final answer.\n"
            ),
        ),
        tools=[
            lookup_reagent_tool(),
            lookup_enzyme_tool(),
            check_safety_tool(),
            run_pcr_tool(),
            run_gel_tool(),
        ],
    )


def build_screen_solver():
    """Build the Screen-01 solver chain with only colony-screening tools."""
    from inspect_ai.agent import AgentPrompt, react

    from .tools.lab_tools import inspect_screening_plate_tool, run_colony_pcr_tool
    from .tools.reference import check_safety_tool, lookup_reagent_tool

    return react(
        prompt=AgentPrompt(
            instructions=LABCRAFT_SYSTEM_PROMPT,
            assistant_prompt=(
                "\nBe concise between tool calls. Inspect the plate once, screen the "
                "minimum sensible set of white colonies needed to meet the confidence "
                "target, then provide the final answer.\n"
            ),
        ),
        tools=[
            lookup_reagent_tool(),
            check_safety_tool(),
            inspect_screening_plate_tool(),
            run_colony_pcr_tool(),
        ],
    )


@solver
def configure_transform_sample():
    """Initialize per-sample LabCraft state before the main solver runs."""

    async def solve(state, generate):
        set_active_sample(state.sample_id)
        return state

    return solve


@solver
def configure_growth_sample():
    """Initialize per-sample LabCraft state before the growth solver runs."""

    async def solve(state, generate):
        set_active_sample(state.sample_id)
        return state

    return solve


@solver
def configure_pcr_sample():
    """Initialize per-sample LabCraft state before the PCR solver runs."""

    async def solve(state, generate):
        set_active_sample(state.sample_id)
        return state

    return solve


@solver
def configure_screen_sample():
    """Initialize per-sample LabCraft state before the screening solver runs."""

    async def solve(state, generate):
        set_active_sample(state.sample_id)
        return state

    return solve


def build_clone_solver():
    """Build the Clone-01 solver chain with cloning and downstream screening tools."""
    from inspect_ai.agent import AgentPrompt, react

    from .tools.lab_tools import (
        count_colonies_tool,
        inspect_screening_plate_tool,
        ligate_tool,
        list_cloning_substrates_tool,
        plate_tool,
        prepare_media_tool,
        restriction_digest_tool,
        run_colony_pcr_tool,
        transform_ligation_tool,
    )
    from .tools.reference import check_safety_tool, lookup_enzyme_tool, lookup_reagent_tool

    return react(
        prompt=AgentPrompt(
            instructions=LABCRAFT_SYSTEM_PROMPT,
            assistant_prompt=(
                "\nBe concise between tool calls. Digest vector and insert with the "
                "EcoRI + BamHI pair in a compatible NEB buffer, heat-inactivate, "
                "ligate with T4 DNA ligase at a standard molar ratio, transform the "
                "ligation, plate on LB + ampicillin, then inspect the plate and run "
                "colony PCR on enough white colonies to meet the confidence target.\n"
            ),
        ),
        tools=[
            lookup_reagent_tool(),
            lookup_enzyme_tool(),
            check_safety_tool(),
            list_cloning_substrates_tool(),
            restriction_digest_tool(),
            ligate_tool(),
            prepare_media_tool(),
            transform_ligation_tool(),
            plate_tool(),
            count_colonies_tool(),
            inspect_screening_plate_tool(),
            run_colony_pcr_tool(),
        ],
    )


@solver
def configure_clone_sample():
    """Initialize per-sample LabCraft state before the cloning solver runs."""

    async def solve(state, generate):
        set_active_sample(state.sample_id)
        return state

    return solve


def build_golden_gate_solver():
    """Build the Golden Gate-01 solver chain with Type IIS assembly + transformation + plating tools."""
    from inspect_ai.agent import AgentPrompt, react

    from .tools.lab_tools import (
        count_colonies_tool,
        golden_gate_assembly_tool,
        list_golden_gate_substrates_tool,
        plate_tool,
        prepare_media_tool,
        transform_assembly_tool,
    )
    from .tools.reference import check_safety_tool, lookup_enzyme_tool, lookup_reagent_tool

    return react(
        prompt=AgentPrompt(
            instructions=LABCRAFT_SYSTEM_PROMPT,
            assistant_prompt=(
                "\nBe concise between tool calls. Inspect the substrates, choose a Type IIS enzyme "
                "(BsaI) plus T4 DNA ligase, run at least 25 cycles of 37 C / 16 C, transform the "
                "assembled construct, plate on LB + ampicillin, and count transformants.\n"
            ),
        ),
        tools=[
            lookup_reagent_tool(),
            lookup_enzyme_tool(),
            check_safety_tool(),
            list_golden_gate_substrates_tool(),
            golden_gate_assembly_tool(),
            prepare_media_tool(),
            transform_assembly_tool(),
            plate_tool(),
            count_colonies_tool(),
        ],
    )


@solver
def configure_golden_gate_sample():
    """Initialize per-sample LabCraft state before the Golden Gate solver runs."""

    async def solve(state, generate):
        set_active_sample(state.sample_id)
        return state

    return solve


def build_gibson_solver():
    """Build the Gibson-01 solver chain with isothermal Gibson + transform + plate tools."""
    from inspect_ai.agent import AgentPrompt, react

    from .tools.lab_tools import (
        count_colonies_tool,
        gibson_assembly_tool,
        list_gibson_substrates_tool,
        plate_tool,
        prepare_media_tool,
        transform_gibson_tool,
    )
    from .tools.reference import check_safety_tool, lookup_reagent_tool

    return react(
        prompt=AgentPrompt(
            instructions=LABCRAFT_SYSTEM_PROMPT,
            assistant_prompt=(
                "\nBe concise between tool calls. Inspect the Gibson substrates, set up "
                "a Gibson assembly with an appropriate master mix (Gibson Assembly Master "
                "Mix or NEBuilder HiFi) at 50 C for at least 15 min, transform the "
                "construct, plate on LB + ampicillin, and count transformants.\n"
            ),
        ),
        tools=[
            lookup_reagent_tool(),
            check_safety_tool(),
            list_gibson_substrates_tool(),
            gibson_assembly_tool(),
            prepare_media_tool(),
            transform_gibson_tool(),
            plate_tool(),
            count_colonies_tool(),
        ],
    )


@solver
def configure_gibson_sample():
    """Initialize per-sample LabCraft state before the Gibson solver runs."""

    async def solve(state, generate):
        set_active_sample(state.sample_id)
        return state

    return solve


def build_miniprep_solver():
    """Build the Miniprep-01 solver chain."""
    from inspect_ai.agent import AgentPrompt, react

    from .tools.lab_tools import perform_miniprep_tool
    from .tools.reference import check_safety_tool, lookup_reagent_tool

    return react(
        prompt=AgentPrompt(
            instructions=LABCRAFT_SYSTEM_PROMPT,
            assistant_prompt=(
                "\nBe concise. Run a single alkaline-lysis miniprep with the P1/P2/P3 "
                "buffer sequence, no more than 5 min in P2, silica column purification, "
                "and an elution volume of at least 30 uL. Report yield and A260/A280 purity.\n"
            ),
        ),
        tools=[
            lookup_reagent_tool(),
            check_safety_tool(),
            perform_miniprep_tool(),
        ],
    )


@solver
def configure_miniprep_sample():
    """Initialize per-sample LabCraft state before the miniprep solver runs."""

    async def solve(state, generate):
        set_active_sample(state.sample_id)
        return state

    return solve


def build_expression_solver():
    """Build the Express-01 solver chain."""
    from inspect_ai.agent import AgentPrompt, react

    from .tools.lab_tools import run_protein_expression_tool
    from .tools.reference import check_safety_tool, lookup_reagent_tool

    return react(
        prompt=AgentPrompt(
            instructions=LABCRAFT_SYSTEM_PROMPT,
            assistant_prompt=(
                "\nBe concise. Run a single recombinant protein expression in a T7 "
                "expression host (BL21(DE3) or a close derivative), induce with 0.1-1 "
                "mM IPTG at mid-log OD600, pick a standard induction temperature, and "
                "lyse in a buffer compatible with Ni-NTA (pH 7-8). Report yield.\n"
            ),
        ),
        tools=[
            lookup_reagent_tool(),
            check_safety_tool(),
            run_protein_expression_tool(),
        ],
    )


@solver
def configure_expression_sample():
    """Initialize per-sample LabCraft state before the expression solver runs."""

    async def solve(state, generate):
        set_active_sample(state.sample_id)
        return state

    return solve


def build_purification_solver():
    """Build the Purify-01 solver chain."""
    from inspect_ai.agent import AgentPrompt, react

    from .tools.lab_tools import run_nta_purification_tool
    from .tools.reference import check_safety_tool, lookup_reagent_tool

    return react(
        prompt=AgentPrompt(
            instructions=LABCRAFT_SYSTEM_PROMPT,
            assistant_prompt=(
                "\nBe concise. Run a single Ni-NTA affinity purification with a "
                "10-20 mM imidazole load, 40-60 mM wash, and >= 200 mM elution. "
                "Report purified concentration, SDS-PAGE band, and purity percent.\n"
            ),
        ),
        tools=[
            lookup_reagent_tool(),
            check_safety_tool(),
            run_nta_purification_tool(),
        ],
    )


@solver
def configure_purification_sample():
    """Initialize per-sample LabCraft state before the purification solver runs."""

    async def solve(state, generate):
        set_active_sample(state.sample_id)
        return state

    return solve


def build_discovery_solver():
    """Build the discovery-decision solver chain."""
    from inspect_ai.agent import AgentPrompt, react

    from .tools.discovery import (
        list_candidate_targets_tool,
        list_validation_assays_tool,
        lookup_target_profile_tool,
        run_validation_assay_tool,
    )

    return react(
        prompt=AgentPrompt(
            instructions=DISCOVERY_SYSTEM_PROMPT,
            assistant_prompt=(
                "\nBe concise between tool calls. Use the discovery tools to inspect only "
                "the evidence needed, avoid repeated lookups unless the task requires them, "
                "and make sure the final answer exactly matches the requested schema.\n"
            ),
        ),
        tools=[
            list_candidate_targets_tool(),
            lookup_target_profile_tool(),
            list_validation_assays_tool(),
            run_validation_assay_tool(),
        ],
    )


@solver
def configure_discovery_sample():
    """Initialize per-sample discovery-track state before the solver runs."""

    async def solve(state, generate):
        set_active_discovery_sample(state.sample_id)
        return state

    return solve
