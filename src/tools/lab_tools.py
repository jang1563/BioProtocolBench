"""Agent-facing lab-operation wrappers."""

from __future__ import annotations

import contextvars
from typing import Optional

from src.environment import get_or_create_lab_state
from src.environment.observations import render_observation
from src.environment.operations import (
    count_colonies,
    fit_growth_curve,
    incubate,
    inspect_screening_plate,
    inoculate_growth,
    ligate,
    list_cloning_substrates,
    measure_od600,
    plate,
    prepare_media,
    restriction_digest,
    run_colony_pcr,
    run_gel,
    run_pcr,
    transform,
    transform_ligation,
)
from src.environment.state import reset_lab_state

_ACTIVE_SAMPLE_ID = contextvars.ContextVar("labcraft_active_sample_id", default="transform_01_default")
_ACTIVE_SAMPLE_SEED = contextvars.ContextVar("labcraft_active_sample_seed", default=None)


def set_active_sample(sample_id: str, seed: Optional[int] = None):
    _ACTIVE_SAMPLE_ID.set(sample_id)
    _ACTIVE_SAMPLE_SEED.set(seed)
    reset_lab_state(sample_id)
    get_or_create_lab_state(sample_id, seed=seed)


def cleanup_sample(sample_id: str) -> None:
    reset_lab_state(sample_id)


def _current_state():
    sample_id = _ACTIVE_SAMPLE_ID.get()
    seed = _ACTIVE_SAMPLE_SEED.get()
    return get_or_create_lab_state(sample_id, seed=seed)


async def prepare_media_call(
    medium: str,
    antibiotic: str,
    antibiotic_concentration_ug_ml: float,
    plate_count: int = 1,
) -> str:
    state = _current_state()
    return render_observation(
        prepare_media(
            state=state,
            medium=medium,
            antibiotic=antibiotic,
            antibiotic_concentration_ug_ml=antibiotic_concentration_ug_ml,
            plate_count=plate_count,
        )
    )


async def transform_call(
    plasmid_mass_pg: float,
    heat_shock_seconds: int,
    recovery_minutes: int,
    outgrowth_media: str = "SOC",
    shaking: bool = True,
    ice_incubation_minutes: int = 30,
) -> str:
    state = _current_state()
    return render_observation(
        transform(
            state=state,
            plasmid_mass_pg=plasmid_mass_pg,
            heat_shock_seconds=heat_shock_seconds,
            recovery_minutes=recovery_minutes,
            outgrowth_media=outgrowth_media,
            shaking=shaking,
            ice_incubation_minutes=ice_incubation_minutes,
        )
    )


async def plate_call(
    culture_id: str,
    plate_id: str,
    dilution_factor: float,
    volume_ul: float,
) -> str:
    state = _current_state()
    return render_observation(
        plate(
            state=state,
            culture_id=culture_id,
            plate_id=plate_id,
            dilution_factor=dilution_factor,
            volume_ul=volume_ul,
        )
    )


async def count_colonies_call(plating_id: str) -> str:
    state = _current_state()
    return render_observation(count_colonies(state=state, plating_id=plating_id))


async def inoculate_growth_call(condition: str, starting_od600: float) -> str:
    state = _current_state()
    return render_observation(
        inoculate_growth(
            state=state,
            condition=condition,
            starting_od600=starting_od600,
        )
    )


async def incubate_call(growth_id: str, duration_minutes: int) -> str:
    state = _current_state()
    return render_observation(incubate(state=state, growth_id=growth_id, duration_minutes=duration_minutes))


async def measure_od600_call(growth_id: str, dilution_factor: float = 1.0) -> str:
    state = _current_state()
    return render_observation(
        measure_od600(state=state, growth_id=growth_id, dilution_factor=dilution_factor)
    )


async def fit_growth_curve_call(growth_id: str) -> str:
    state = _current_state()
    return render_observation(fit_growth_curve(state=state, growth_id=growth_id))


async def run_pcr_call(
    polymerase_name: str,
    additive: str,
    extension_seconds: int,
    cycle_count: int,
) -> str:
    state = _current_state()
    return render_observation(
        run_pcr(
            state=state,
            polymerase_name=polymerase_name,
            additive=additive,
            extension_seconds=extension_seconds,
            cycle_count=cycle_count,
        )
    )


async def run_gel_call(
    reaction_id: str,
    agarose_percent: float = 1.0,
    ladder_name: str = "1 kb DNA Ladder",
) -> str:
    state = _current_state()
    return render_observation(
        run_gel(
            state=state,
            reaction_id=reaction_id,
            agarose_percent=agarose_percent,
            ladder_name=ladder_name,
        )
    )


async def inspect_screening_plate_call() -> str:
    state = _current_state()
    return render_observation(inspect_screening_plate(state=state))


async def run_colony_pcr_call(
    colony_ids: list[str],
    primer_pair: str = "M13/pUC flank primers",
) -> str:
    state = _current_state()
    return render_observation(
        run_colony_pcr(
            state=state,
            colony_ids=colony_ids,
            primer_pair=primer_pair,
        )
    )


async def list_cloning_substrates_call() -> str:
    state = _current_state()
    return render_observation(list_cloning_substrates(state=state))


async def restriction_digest_call(
    fragment_id: str,
    enzyme_names: list[str],
    buffer: str,
    temperature_c: float,
    duration_minutes: int,
    heat_inactivate_after: bool,
    heat_inactivation_temperature_c: float = 65.0,
) -> str:
    state = _current_state()
    return render_observation(
        restriction_digest(
            state=state,
            fragment_id=fragment_id,
            enzyme_names=enzyme_names,
            buffer=buffer,
            temperature_c=temperature_c,
            duration_minutes=duration_minutes,
            heat_inactivate_after=heat_inactivate_after,
            heat_inactivation_temperature_c=heat_inactivation_temperature_c,
        )
    )


async def ligate_call(
    vector_fragment_id: str,
    insert_fragment_ids: list[str],
    ligase_name: str,
    vector_to_insert_molar_ratio: float,
    temperature_c: float,
    duration_minutes: int,
    buffer: str = "T4 DNA ligase buffer",
) -> str:
    state = _current_state()
    return render_observation(
        ligate(
            state=state,
            vector_fragment_id=vector_fragment_id,
            insert_fragment_ids=insert_fragment_ids,
            ligase_name=ligase_name,
            vector_to_insert_molar_ratio=vector_to_insert_molar_ratio,
            temperature_c=temperature_c,
            duration_minutes=duration_minutes,
            buffer=buffer,
        )
    )


async def transform_ligation_call(
    ligation_id: str,
    heat_shock_seconds: int = 30,
    recovery_minutes: int = 60,
    outgrowth_media: str = "SOC",
    shaking: bool = True,
    ice_incubation_minutes: int = 30,
) -> str:
    state = _current_state()
    return render_observation(
        transform_ligation(
            state=state,
            ligation_id=ligation_id,
            heat_shock_seconds=heat_shock_seconds,
            recovery_minutes=recovery_minutes,
            outgrowth_media=outgrowth_media,
            shaking=shaking,
            ice_incubation_minutes=ice_incubation_minutes,
        )
    )


def prepare_media_tool():
    from inspect_ai.tool import tool

    @tool(name="prepare_media")
    def prepare_media_tool_impl():
        """Prepare selection plates for a transformation experiment."""

        async def execute(
            medium: str,
            antibiotic: str,
            antibiotic_concentration_ug_ml: float,
            plate_count: int = 1,
        ) -> str:
            """Prepare one or more selection plates.

            Args:
                medium: Plate medium name, such as "LB agar".
                antibiotic: Selection antibiotic name.
                antibiotic_concentration_ug_ml: Working antibiotic concentration in ug/mL.
                plate_count: Number of plates to prepare.
            """
            return await prepare_media_call(
                medium=medium,
                antibiotic=antibiotic,
                antibiotic_concentration_ug_ml=antibiotic_concentration_ug_ml,
                plate_count=plate_count,
            )

        return execute

    return prepare_media_tool_impl()


def transform_tool():
    from inspect_ai.tool import tool

    @tool(name="transform")
    def transform_tool_impl():
        """Transform chemically competent E. coli with plasmid DNA."""

        async def execute(
            plasmid_mass_pg: float,
            heat_shock_seconds: int,
            recovery_minutes: int,
            outgrowth_media: str = "SOC",
            shaking: bool = True,
            ice_incubation_minutes: int = 30,
        ) -> str:
            """Run a chemical transformation.

            Args:
                plasmid_mass_pg: DNA mass in picograms.
                heat_shock_seconds: Heat shock duration in seconds.
                recovery_minutes: Outgrowth duration before plating.
                outgrowth_media: Recovery medium name.
                shaking: Whether the outgrowth is shaken.
                ice_incubation_minutes: Time spent on ice before heat shock.
            """
            return await transform_call(
                plasmid_mass_pg=plasmid_mass_pg,
                heat_shock_seconds=heat_shock_seconds,
                recovery_minutes=recovery_minutes,
                outgrowth_media=outgrowth_media,
                shaking=shaking,
                ice_incubation_minutes=ice_incubation_minutes,
            )

        return execute

    return transform_tool_impl()


def plate_tool():
    from inspect_ai.tool import tool

    @tool(name="plate")
    def plate_tool_impl():
        """Plate a transformed culture onto a prepared selection plate."""

        async def execute(
            culture_id: str,
            plate_id: str,
            dilution_factor: float,
            volume_ul: float,
        ) -> str:
            """Plate a transformed culture.

            Args:
                culture_id: Identifier returned by the transform tool.
                plate_id: Identifier returned by the prepare_media tool.
                dilution_factor: Dilution applied before plating.
                volume_ul: Plated volume in microliters.
            """
            return await plate_call(
                culture_id=culture_id,
                plate_id=plate_id,
                dilution_factor=dilution_factor,
                volume_ul=volume_ul,
            )

        return execute

    return plate_tool_impl()


def count_colonies_tool():
    from inspect_ai.tool import tool

    @tool(name="count_colonies")
    def count_colonies_tool_impl():
        """Count colonies on a plated transformation sample."""

        async def execute(plating_id: str) -> str:
            """Count colonies on a plated sample.

            Args:
                plating_id: Identifier returned by the plate tool.
            """
            return await count_colonies_call(plating_id=plating_id)

        return execute

    return count_colonies_tool_impl()


def inoculate_growth_tool():
    from inspect_ai.tool import tool

    @tool(name="inoculate_growth")
    def inoculate_growth_tool_impl():
        """Start one growth-characterization culture in a named condition."""

        async def execute(condition: str, starting_od600: float) -> str:
            """Inoculate a growth culture.

            Args:
                condition: One of "LB", "M9 + glucose", or "LB + chloramphenicol (1.8 uM)".
                starting_od600: Initial OD600 at inoculation.
            """
            return await inoculate_growth_call(condition=condition, starting_od600=starting_od600)

        return execute

    return inoculate_growth_tool_impl()


def incubate_tool():
    from inspect_ai.tool import tool

    @tool(name="incubate")
    def incubate_tool_impl():
        """Advance a growth culture by a specified incubation interval."""

        async def execute(growth_id: str, duration_minutes: int) -> str:
            """Advance a culture in time.

            Args:
                growth_id: Identifier returned by inoculate_growth.
                duration_minutes: Incubation duration in minutes.
            """
            return await incubate_call(growth_id=growth_id, duration_minutes=duration_minutes)

        return execute

    return incubate_tool_impl()


def measure_od600_tool():
    from inspect_ai.tool import tool

    @tool(name="measure_od600")
    def measure_od600_tool_impl():
        """Measure the OD600 of a growth culture."""

        async def execute(growth_id: str, dilution_factor: float = 1.0) -> str:
            """Record an OD600 measurement.

            Args:
                growth_id: Identifier returned by inoculate_growth.
                dilution_factor: Sample dilution applied before the OD600 reading.
            """
            return await measure_od600_call(growth_id=growth_id, dilution_factor=dilution_factor)

        return execute

    return measure_od600_tool_impl()


def fit_growth_curve_tool():
    from inspect_ai.tool import tool

    @tool(name="fit_growth_curve")
    def fit_growth_curve_tool_impl():
        """Estimate growth-rate parameters from collected OD600 measurements."""

        async def execute(growth_id: str) -> str:
            """Fit a simple growth curve summary.

            Args:
                growth_id: Identifier returned by inoculate_growth.
            """
            return await fit_growth_curve_call(growth_id=growth_id)

        return execute

    return fit_growth_curve_tool_impl()


def run_pcr_tool():
    from inspect_ai.tool import tool

    @tool(name="run_pcr")
    def run_pcr_tool_impl():
        """Run one PCR condition for the GC-rich PCR optimization task."""

        async def execute(
            polymerase_name: str,
            additive: str,
            extension_seconds: int,
            cycle_count: int,
        ) -> str:
            """Run a PCR reaction.

            Args:
                polymerase_name: Polymerase name, such as "Q5 High-Fidelity DNA polymerase".
                additive: GC-rich additive choice, such as "DMSO", "Betaine", or "none".
                extension_seconds: Extension time per cycle in seconds.
                cycle_count: Total cycle count.

            Returns:
                A PCR result that includes a reaction_id such as "pcr_001". Save that
                exact reaction_id and reuse it when calling run_gel.
            """
            return await run_pcr_call(
                polymerase_name=polymerase_name,
                additive=additive,
                extension_seconds=extension_seconds,
                cycle_count=cycle_count,
            )

        return execute

    return run_pcr_tool_impl()


def run_gel_tool():
    from inspect_ai.tool import tool

    @tool(name="run_gel")
    def run_gel_tool_impl():
        """Visualize a PCR reaction on an agarose gel."""

        async def execute(
            reaction_id: str,
            agarose_percent: float = 1.0,
            ladder_name: str = "1 kb DNA Ladder",
        ) -> str:
            """Run a gel for a PCR reaction.

            Args:
                reaction_id: Reaction identifier returned by run_pcr, preferably reused
                    exactly as returned (for example "pcr_001").
                agarose_percent: Agarose concentration for the gel.
                ladder_name: DNA ladder used for size estimation.
            """
            return await run_gel_call(
                reaction_id=reaction_id,
                agarose_percent=agarose_percent,
                ladder_name=ladder_name,
            )

        return execute

    return run_gel_tool_impl()


def inspect_screening_plate_tool():
    from inspect_ai.tool import tool

    @tool(name="inspect_screening_plate")
    def inspect_screening_plate_tool_impl():
        """Inspect the blue-white screening plate used in Screen-01."""

        async def execute() -> str:
            """Return the plate composition and available colony identifiers."""
            return await inspect_screening_plate_call()

        return execute

    return inspect_screening_plate_tool_impl()


def run_colony_pcr_tool():
    from inspect_ai.tool import tool

    @tool(name="run_colony_pcr")
    def run_colony_pcr_tool_impl():
        """Run colony PCR on one or more candidate colonies from the screening plate."""

        async def execute(
            colony_ids: list[str],
            primer_pair: str = "M13/pUC flank primers",
        ) -> str:
            """Run colony PCR on selected colonies.

            Args:
                colony_ids: Colony identifiers returned by inspect_screening_plate.
                primer_pair: Primer pair label for the screening PCR.
            """
            return await run_colony_pcr_call(
                colony_ids=colony_ids,
                primer_pair=primer_pair,
            )

        return execute

    return run_colony_pcr_tool_impl()


def list_cloning_substrates_tool():
    from inspect_ai.tool import tool

    @tool(name="list_cloning_substrates")
    def list_cloning_substrates_tool_impl():
        """List the starting DNA fragments available for Clone-01."""

        async def execute() -> str:
            """Return the vector and insert fragments provided for the cloning task."""
            return await list_cloning_substrates_call()

        return execute

    return list_cloning_substrates_tool_impl()


def restriction_digest_tool():
    from inspect_ai.tool import tool

    @tool(name="restriction_digest")
    def restriction_digest_tool_impl():
        """Run a restriction digest on a DNA fragment for cloning."""

        async def execute(
            fragment_id: str,
            enzyme_names: list[str],
            buffer: str,
            temperature_c: float,
            duration_minutes: int,
            heat_inactivate_after: bool,
            heat_inactivation_temperature_c: float = 65.0,
        ) -> str:
            """Digest a DNA fragment with one or more restriction enzymes.

            Args:
                fragment_id: Fragment to digest, as returned by list_cloning_substrates.
                enzyme_names: Restriction enzymes (e.g., ["EcoRI", "BamHI"]).
                buffer: Reaction buffer (e.g., "CutSmart").
                temperature_c: Incubation temperature in Celsius.
                duration_minutes: Incubation time in minutes.
                heat_inactivate_after: Whether to heat-inactivate the enzymes after digestion.
                heat_inactivation_temperature_c: Temperature used for heat inactivation if enabled.
            """
            return await restriction_digest_call(
                fragment_id=fragment_id,
                enzyme_names=enzyme_names,
                buffer=buffer,
                temperature_c=temperature_c,
                duration_minutes=duration_minutes,
                heat_inactivate_after=heat_inactivate_after,
                heat_inactivation_temperature_c=heat_inactivation_temperature_c,
            )

        return execute

    return restriction_digest_tool_impl()


def ligate_tool():
    from inspect_ai.tool import tool

    @tool(name="ligate")
    def ligate_tool_impl():
        """Set up a ligation reaction from a digested vector and one or more inserts."""

        async def execute(
            vector_fragment_id: str,
            insert_fragment_ids: list[str],
            ligase_name: str,
            vector_to_insert_molar_ratio: float,
            temperature_c: float,
            duration_minutes: int,
            buffer: str = "T4 DNA ligase buffer",
        ) -> str:
            """Ligate a digested vector with one or more digested inserts.

            Args:
                vector_fragment_id: Digested vector fragment id (output of restriction_digest).
                insert_fragment_ids: Digested insert fragment ids.
                ligase_name: Ligase name (use "T4 DNA ligase" for cohesive-end ligation).
                vector_to_insert_molar_ratio: Insert excess over vector (e.g., 3.0 for 1:3 vector:insert).
                temperature_c: Ligation temperature (16, 22, or 25 C).
                duration_minutes: Ligation duration in minutes.
                buffer: Ligation buffer label.
            """
            return await ligate_call(
                vector_fragment_id=vector_fragment_id,
                insert_fragment_ids=insert_fragment_ids,
                ligase_name=ligase_name,
                vector_to_insert_molar_ratio=vector_to_insert_molar_ratio,
                temperature_c=temperature_c,
                duration_minutes=duration_minutes,
                buffer=buffer,
            )

        return execute

    return ligate_tool_impl()


def transform_ligation_tool():
    from inspect_ai.tool import tool

    @tool(name="transform_ligation")
    def transform_ligation_tool_impl():
        """Transform a ligation reaction into competent E. coli and prepare a screening plate."""

        async def execute(
            ligation_id: str,
            heat_shock_seconds: int = 30,
            recovery_minutes: int = 60,
            outgrowth_media: str = "SOC",
            shaking: bool = True,
            ice_incubation_minutes: int = 30,
        ) -> str:
            """Transform a ligation into competent cells.

            Args:
                ligation_id: Ligation identifier (e.g., "ligation_001") from the ligate tool.
                heat_shock_seconds: Heat shock duration (30 s is standard).
                recovery_minutes: Post-shock outgrowth duration in minutes.
                outgrowth_media: Outgrowth medium ("SOC" recommended).
                shaking: Whether to shake during recovery.
                ice_incubation_minutes: Pre-shock ice incubation time.
            """
            return await transform_ligation_call(
                ligation_id=ligation_id,
                heat_shock_seconds=heat_shock_seconds,
                recovery_minutes=recovery_minutes,
                outgrowth_media=outgrowth_media,
                shaking=shaking,
                ice_incubation_minutes=ice_incubation_minutes,
            )

        return execute

    return transform_ligation_tool_impl()
