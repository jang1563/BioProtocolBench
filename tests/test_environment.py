"""Environment tests for Transform-01."""

from __future__ import annotations

import asyncio
import json

import pytest

from pathlib import Path

from src.environment.operations import (
    count_colonies,
    fit_growth_curve,
    incubate,
    inoculate_growth,
    inspect_screening_plate,
    measure_od600,
    plate,
    prepare_media,
    run_colony_pcr,
    run_gel,
    run_pcr,
    transform,
)
from src.environment.state import create_lab_state
from src.environment.stochastic import load_screening_parameters
from src.tools.lab_tools import (
    cleanup_sample,
    count_colonies_call,
    fit_growth_curve_call,
    incubate_call,
    inoculate_growth_call,
    inspect_screening_plate_call,
    measure_od600_call,
    plate_call,
    prepare_media_call,
    run_colony_pcr_call,
    run_gel_call,
    run_pcr_call,
    set_active_sample,
    transform_call,
)


def _run_transform_sequence(sample_id, seed):
    state = create_lab_state(sample_id=sample_id, seed=seed)
    prepared = prepare_media(
        state=state,
        medium="LB agar",
        antibiotic="ampicillin",
        antibiotic_concentration_ug_ml=100,
        plate_count=1,
    )
    plate_id = prepared["plates"][0]["plate_id"]
    transformed = transform(
        state=state,
        plasmid_mass_pg=1000,
        heat_shock_seconds=30,
        recovery_minutes=60,
        outgrowth_media="SOC",
        shaking=True,
    )
    plated = plate(
        state=state,
        culture_id=transformed["culture_id"],
        plate_id=plate_id,
        dilution_factor=10000,
        volume_ul=100,
    )
    counted = count_colonies(state=state, plating_id=plated["plating_id"])
    return {
        "prepared": prepared,
        "transformed": transformed,
        "plated": plated,
        "counted": counted,
    }


def _run_growth_sequence(sample_id, seed):
    state = create_lab_state(sample_id=sample_id, seed=seed)
    cultures = []
    for condition in ("LB", "M9 + glucose", "LB + chloramphenicol (1.8 uM)"):
        inoculated = inoculate_growth(state=state, condition=condition, starting_od600=0.05)
        growth_id = inoculated["growth_id"]
        measure_od600(state=state, growth_id=growth_id, dilution_factor=1.0)
        for minute in range(15, 121, 15):
            incubate(state=state, growth_id=growth_id, duration_minutes=15)
            dilution = 10.0 if condition == "LB" and minute >= 75 else 1.0
            measure_od600(state=state, growth_id=growth_id, dilution_factor=dilution)
        cultures.append(fit_growth_curve(state=state, growth_id=growth_id))
    return cultures


def _run_pcr_sequence(sample_id, seed):
    state = create_lab_state(sample_id=sample_id, seed=seed)
    reaction = run_pcr(
        state=state,
        polymerase_name="Q5 High-Fidelity DNA polymerase",
        additive="DMSO",
        extension_seconds=60,
        cycle_count=32,
    )
    gel = run_gel(state=state, reaction_id=reaction["reaction_id"], agarose_percent=1.0)
    return {"reaction": reaction, "gel": gel}


def test_same_seed_same_trajectory_is_deterministic():
    first = _run_transform_sequence("transform-seed", seed=12345)
    second = _run_transform_sequence("transform-seed-repeat", seed=12345)
    assert first == second


def test_different_seed_changes_outcome():
    first = _run_transform_sequence("transform-seed-a", seed=12345)
    second = _run_transform_sequence("transform-seed-b", seed=67890)
    assert first["counted"]["observed_colonies"] != second["counted"]["observed_colonies"]


def test_growth_sequence_is_deterministic():
    first = _run_growth_sequence("growth-seed-a", seed=12345)
    second = _run_growth_sequence("growth-seed-b", seed=12345)
    assert first == second


def test_pcr_sequence_is_deterministic():
    first = _run_pcr_sequence("pcr-seed-a", seed=12345)
    second = _run_pcr_sequence("pcr-seed-b", seed=12345)
    assert first == second


def test_good_pcr_condition_yields_clean_target_band():
    state = create_lab_state(sample_id="pcr-good", seed=7)
    reaction = run_pcr(
        state=state,
        polymerase_name="Q5 High-Fidelity DNA polymerase",
        additive="DMSO",
        extension_seconds=60,
        cycle_count=32,
    )
    gel = run_gel(state=state, reaction_id=reaction["reaction_id"], agarose_percent=1.0)
    assert reaction["status"] == "clean_target_band"
    assert gel["status"] == "single_clean_target_band"
    assert gel["visible_bands_bp"] == [2000]


def test_pcr_without_gc_additive_fails_clean_amplification():
    state = create_lab_state(sample_id="pcr-no-additive", seed=7)
    reaction = run_pcr(
        state=state,
        polymerase_name="Q5 High-Fidelity DNA polymerase",
        additive="none",
        extension_seconds=60,
        cycle_count=32,
    )
    gel = run_gel(state=state, reaction_id=reaction["reaction_id"], agarose_percent=1.0)
    assert reaction["status"] == "gc_rich_failure"
    assert gel["status"] == "no_visible_product"
    assert gel["visible_bands_bp"] == []


def test_run_gel_accepts_numeric_reaction_suffix():
    state = create_lab_state(sample_id="pcr-gel-suffix", seed=7)
    reaction = run_pcr(
        state=state,
        polymerase_name="Q5 High-Fidelity DNA polymerase",
        additive="DMSO",
        extension_seconds=60,
        cycle_count=32,
    )
    gel = run_gel(state=state, reaction_id="1", agarose_percent=1.0)
    assert reaction["reaction_id"] == "pcr_001"
    assert gel["reaction_id"] == "pcr_001"
    assert gel["status"] == "single_clean_target_band"


def test_run_gel_unknown_reaction_id_raises_clear_error():
    state = create_lab_state(sample_id="pcr-gel-missing", seed=7)
    run_pcr(
        state=state,
        polymerase_name="Q5 High-Fidelity DNA polymerase",
        additive="DMSO",
        extension_seconds=60,
        cycle_count=32,
    )
    with pytest.raises(ValueError, match="Available reaction IDs: pcr_001"):
        run_gel(state=state, reaction_id="7", agarose_percent=1.0)


def test_plate_selection_failure_is_reported():
    state = create_lab_state(sample_id="selection-failure", seed=101)
    prepared = prepare_media(
        state=state,
        medium="LB agar",
        antibiotic="ampicillin",
        antibiotic_concentration_ug_ml=50,
        plate_count=1,
    )
    transformed = transform(
        state=state,
        plasmid_mass_pg=1000,
        heat_shock_seconds=30,
        recovery_minutes=60,
    )
    plated = plate(
        state=state,
        culture_id=transformed["culture_id"],
        plate_id=prepared["plates"][0]["plate_id"],
        dilution_factor=1000,
        volume_ul=100,
    )
    counted = count_colonies(state=state, plating_id=plated["plating_id"])
    assert counted["status"] == "selection_failed"
    assert counted["observed_colonies"] is None


def test_plate_out_of_countable_range_is_reported():
    state = create_lab_state(sample_id="count-out-of-range", seed=123)
    prepared = prepare_media(
        state=state,
        medium="LB agar",
        antibiotic="ampicillin",
        antibiotic_concentration_ug_ml=100,
        plate_count=1,
    )
    transformed = transform(
        state=state,
        plasmid_mass_pg=10000,
        heat_shock_seconds=30,
        recovery_minutes=60,
    )
    plated = plate(
        state=state,
        culture_id=transformed["culture_id"],
        plate_id=prepared["plates"][0]["plate_id"],
        dilution_factor=1000,
        volume_ul=100,
    )
    counted = count_colonies(state=state, plating_id=plated["plating_id"])
    assert counted["status"] == "count_out_of_range"
    assert counted["observed_colonies"] > 250
    assert "25-250 colonies per plate" in counted["warnings"][0]


def test_concurrent_sample_isolation():
    async def run_pair():
        loop = asyncio.get_running_loop()
        return await asyncio.gather(
            loop.run_in_executor(None, _run_transform_sequence, "concurrent-a", 11),
            loop.run_in_executor(None, _run_transform_sequence, "concurrent-b", 22),
        )

    concurrent_a, concurrent_b = asyncio.run(run_pair())
    sequential_a = _run_transform_sequence("sequential-a", 11)
    sequential_b = _run_transform_sequence("sequential-b", 22)
    assert concurrent_a == sequential_a
    assert concurrent_b == sequential_b


async def _run_tool_sequence(sample_id, seed):
    set_active_sample(sample_id, seed=seed)
    try:
        prepared = json.loads(await prepare_media_call("LB agar", "ampicillin", 100, 1))
        transformed = json.loads(await transform_call(1000, 30, 60, outgrowth_media="SOC", shaking=True))
        plated = json.loads(
            await plate_call(
                culture_id=transformed["culture_id"],
                plate_id=prepared["plates"][0]["plate_id"],
                dilution_factor=10000,
                volume_ul=100,
            )
        )
        counted = json.loads(await count_colonies_call(plated["plating_id"]))
        return {
            "prepared": prepared,
            "transformed": transformed,
            "plated": plated,
            "counted": counted,
        }
    finally:
        cleanup_sample(sample_id)


async def _run_growth_tool_sequence(sample_id, seed):
    set_active_sample(sample_id, seed=seed)
    try:
        fits = []
        for condition in ("LB", "M9 + glucose", "LB + chloramphenicol (1.8 uM)"):
            inoculated = json.loads(await inoculate_growth_call(condition, 0.05))
            growth_id = inoculated["growth_id"]
            json.loads(await measure_od600_call(growth_id, 1.0))
            for minute in range(15, 121, 15):
                json.loads(await incubate_call(growth_id, 15))
                dilution = 10.0 if condition == "LB" and minute >= 75 else 1.0
                json.loads(await measure_od600_call(growth_id, dilution))
            fits.append(json.loads(await fit_growth_curve_call(growth_id)))
        return fits
    finally:
        cleanup_sample(sample_id)


async def _run_pcr_tool_sequence(sample_id, seed):
    set_active_sample(sample_id, seed=seed)
    try:
        reaction = json.loads(
            await run_pcr_call(
                polymerase_name="Q5 High-Fidelity DNA polymerase",
                additive="DMSO",
                extension_seconds=60,
                cycle_count=32,
            )
        )
        gel = json.loads(await run_gel_call(reaction_id=reaction["reaction_id"], agarose_percent=1.0))
        return {"reaction": reaction, "gel": gel}
    finally:
        cleanup_sample(sample_id)


def test_tool_wrapper_concurrent_sample_isolation():
    async def run_pair():
        return await asyncio.gather(
            _run_tool_sequence("tool-concurrent-a", 11),
            _run_tool_sequence("tool-concurrent-b", 22),
        )

    concurrent_a, concurrent_b = asyncio.run(run_pair())
    sequential_a = asyncio.run(_run_tool_sequence("tool-sequential-a", 11))
    sequential_b = asyncio.run(_run_tool_sequence("tool-sequential-b", 22))
    assert concurrent_a == sequential_a
    assert concurrent_b == sequential_b


def test_growth_tool_wrapper_concurrent_sample_isolation():
    async def run_pair():
        return await asyncio.gather(
            _run_growth_tool_sequence("growth-tool-concurrent-a", 31),
            _run_growth_tool_sequence("growth-tool-concurrent-b", 42),
        )

    concurrent_a, concurrent_b = asyncio.run(run_pair())
    sequential_a = asyncio.run(_run_growth_tool_sequence("growth-tool-sequential-a", 31))
    sequential_b = asyncio.run(_run_growth_tool_sequence("growth-tool-sequential-b", 42))
    assert concurrent_a == sequential_a
    assert concurrent_b == sequential_b


def test_pcr_tool_wrapper_concurrent_sample_isolation():
    async def run_pair():
        return await asyncio.gather(
            _run_pcr_tool_sequence("pcr-tool-concurrent-a", 51),
            _run_pcr_tool_sequence("pcr-tool-concurrent-b", 62),
        )

    concurrent_a, concurrent_b = asyncio.run(run_pair())
    sequential_a = asyncio.run(_run_pcr_tool_sequence("pcr-tool-sequential-a", 51))
    sequential_b = asyncio.run(_run_pcr_tool_sequence("pcr-tool-sequential-b", 62))
    assert concurrent_a == sequential_a
    assert concurrent_b == sequential_b


SCREENING_PARAMETERS_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "parameters" / "screening.json"
)


def test_screening_parameter_bundle_exposes_required_values():
    bundle = load_screening_parameters(SCREENING_PARAMETERS_PATH)
    assert bundle.value("historical_positive_rate_among_white_colonies") == pytest.approx(0.4)
    assert bundle.value("screening_target_confidence") == pytest.approx(0.95)
    assert bundle.integer("minimum_white_colonies_for_40pct_hit_rate_at_95pct_confidence") == 6
    assert bundle.integer("screening_recombinant_colony_pcr_band_bp") == 1200
    assert bundle.integer("screening_empty_vector_colony_pcr_band_bp") == 250


def test_inspect_screening_plate_reports_expected_composition():
    state = create_lab_state(sample_id="screen-inspect", seed=1)
    observation = inspect_screening_plate(state=state)
    assert observation["status"] == "screening_plate_ready"
    assert observation["white_colony_count"] == 12
    assert observation["blue_colony_count"] == 18
    assert observation["recombinant_band_bp"] == 1200
    assert observation["empty_vector_band_bp"] == 250
    assert observation["historical_positive_rate_among_white"] == pytest.approx(0.4)
    assert observation["target_confidence"] == pytest.approx(0.95)


def test_run_colony_pcr_on_six_white_colonies_hits_confidence_target():
    state = create_lab_state(sample_id="screen-six-whites", seed=1)
    inspect_screening_plate(state=state)
    result = run_colony_pcr(
        state=state,
        colony_ids=[
            "white_001",
            "white_002",
            "white_003",
            "white_004",
            "white_005",
            "white_006",
        ],
    )
    assert result["status"] == "screened"
    assert result["screening_strategy"] == "white_only"
    assert result["cumulative_screened_white_colony_count"] == 6
    assert result["cumulative_confidence_pct"] >= 95.0
    assert set(result["confirmed_recombinant_ids_cumulative"]).issuperset({"white_002", "white_005"})


def test_run_colony_pcr_flags_blue_colony_as_includes_blue():
    state = create_lab_state(sample_id="screen-blue", seed=1)
    inspect_screening_plate(state=state)
    result = run_colony_pcr(state=state, colony_ids=["blue_001"])
    assert result["screening_strategy"] == "includes_blue"
    assert result["confirmed_recombinant_ids_in_batch"] == []
    assert result["cumulative_screened_white_colony_count"] == 0


def test_run_colony_pcr_is_deterministic_on_same_seed():
    first_state = create_lab_state(sample_id="screen-det-a", seed=42)
    second_state = create_lab_state(sample_id="screen-det-b", seed=42)
    inspect_screening_plate(state=first_state)
    inspect_screening_plate(state=second_state)
    first = run_colony_pcr(state=first_state, colony_ids=["white_002", "white_005"])
    second = run_colony_pcr(state=second_state, colony_ids=["white_002", "white_005"])
    assert first == second


async def _run_screen_tool_sequence(sample_id, seed):
    set_active_sample(sample_id, seed=seed)
    try:
        plate_info = json.loads(await inspect_screening_plate_call())
        white_ids = plate_info["white_colony_ids"][:6]
        screening = json.loads(await run_colony_pcr_call(white_ids))
        return {"plate_info": plate_info, "screening": screening}
    finally:
        cleanup_sample(sample_id)


def test_screen_tool_wrapper_concurrent_sample_isolation():
    async def run_pair():
        return await asyncio.gather(
            _run_screen_tool_sequence("screen-tool-concurrent-a", 71),
            _run_screen_tool_sequence("screen-tool-concurrent-b", 82),
        )

    concurrent_a, concurrent_b = asyncio.run(run_pair())
    sequential_a = asyncio.run(_run_screen_tool_sequence("screen-tool-sequential-a", 71))
    sequential_b = asyncio.run(_run_screen_tool_sequence("screen-tool-sequential-b", 82))
    assert concurrent_a == sequential_a
    assert concurrent_b == sequential_b
