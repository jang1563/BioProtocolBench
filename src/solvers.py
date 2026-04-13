"""Solver helpers for LabCraft."""

from __future__ import annotations

from .prompts import LABCRAFT_SYSTEM_PROMPT
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
