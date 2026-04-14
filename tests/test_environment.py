"""Environment tests for Transform-01."""

from __future__ import annotations

import asyncio
import json

import pytest

from pathlib import Path

from src.environment.operations import (
    count_colonies,
    fit_growth_curve,
    golden_gate_assembly,
    incubate,
    inoculate_growth,
    inspect_screening_plate,
    ligate,
    list_cloning_substrates,
    list_golden_gate_substrates,
    measure_od600,
    plate,
    prepare_media,
    restriction_digest,
    run_colony_pcr,
    run_gel,
    run_pcr,
    transform,
    transform_assembly,
    transform_ligation,
)
from src.environment.state import create_lab_state
from src.environment.stochastic import (
    load_cloning_parameters,
    load_golden_gate_parameters,
    load_screening_parameters,
)
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


CLONING_PARAMETERS_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "parameters" / "cloning.json"
)


def test_cloning_parameter_bundle_exposes_required_values():
    bundle = load_cloning_parameters(CLONING_PARAMETERS_PATH)
    assert bundle.integer("vector_plasmid_length_bp") == 2686
    assert bundle.integer("insert_length_bp") == 950
    assert bundle.value("optimal_vector_to_insert_molar_ratio") == pytest.approx(3.0)
    assert "CutSmart" in bundle.choices("compatible_double_digest_buffers")
    assert bundle.text("preferred_ligase_name") == "T4 DNA ligase"
    assert bundle.integer("digest_minimum_duration_minutes") == 60
    assert 16.0 in [float(t) for t in bundle.choices("acceptable_ligation_temperatures_c")]


def test_list_cloning_substrates_creates_vector_and_insert():
    state = create_lab_state(sample_id="clone-substrates", seed=1)
    observation = list_cloning_substrates(state=state)
    fragment_ids = {f["fragment_id"] for f in observation["fragments"]}
    assert {"puc19_vector", "insert_raw"} <= fragment_ids
    assert observation["status"] == "cloning_substrates_ready"


def _run_good_clone_core(sample_id: str, seed: int):
    state = create_lab_state(sample_id=sample_id, seed=seed)
    list_cloning_substrates(state=state)
    vector_digest = restriction_digest(
        state=state,
        fragment_id="puc19_vector",
        enzyme_names=["EcoRI", "BamHI"],
        buffer="CutSmart",
        temperature_c=37.0,
        duration_minutes=60,
        heat_inactivate_after=True,
    )
    insert_digest = restriction_digest(
        state=state,
        fragment_id="insert_raw",
        enzyme_names=["EcoRI", "BamHI"],
        buffer="CutSmart",
        temperature_c=37.0,
        duration_minutes=60,
        heat_inactivate_after=True,
    )
    ligation = ligate(
        state=state,
        vector_fragment_id=vector_digest["output_fragment_ids"][0],
        insert_fragment_ids=[insert_digest["output_fragment_ids"][0]],
        ligase_name="T4 DNA ligase",
        vector_to_insert_molar_ratio=3.0,
        temperature_c=16.0,
        duration_minutes=960,
    )
    transform_result = transform_ligation(
        state=state,
        ligation_id=ligation["ligation_id"],
    )
    return state, vector_digest, insert_digest, ligation, transform_result


def test_restriction_digest_ecori_bamhi_linearizes_vector():
    state, vector_digest, _, _, _ = _run_good_clone_core("clone-good-digest", 1)
    assert vector_digest["status"] == "digested"
    assert vector_digest["enzymes_key"] == "bamhi+ecori"
    assert vector_digest["buffer_normalized"] == "cutsmart"
    assert vector_digest["output_fragment_ids"]


def test_restriction_digest_wrong_buffer_is_flagged():
    state = create_lab_state(sample_id="clone-wrong-buffer", seed=1)
    list_cloning_substrates(state=state)
    result = restriction_digest(
        state=state,
        fragment_id="puc19_vector",
        enzyme_names=["EcoRI", "BamHI"],
        buffer="NEB 1.1",
        temperature_c=37.0,
        duration_minutes=60,
        heat_inactivate_after=True,
    )
    assert result["status"] == "wrong_buffer"


def test_ligate_with_t4_yields_ligated_status():
    _, _, _, ligation, _ = _run_good_clone_core("clone-good-ligate", 1)
    assert ligation["status"] == "ligated"
    assert ligation["ligase_normalized"] == "t4 dna ligase"


def test_ligate_with_wrong_ligase_reports_wrong_ligase():
    state, vector_digest, insert_digest, _, _ = _run_good_clone_core("clone-wrong-ligase", 1)
    bad_ligation = ligate(
        state=state,
        vector_fragment_id=vector_digest["output_fragment_ids"][0],
        insert_fragment_ids=[insert_digest["output_fragment_ids"][0]],
        ligase_name="E. coli DNA ligase",
        vector_to_insert_molar_ratio=3.0,
        temperature_c=16.0,
        duration_minutes=960,
    )
    assert bad_ligation["status"] == "wrong_ligase"


def test_transform_ligation_produces_culture_and_screening_plate():
    state, _, _, ligation, transform_result = _run_good_clone_core("clone-good-transform", 1)
    assert transform_result["status"] == "transformed"
    assert transform_result["ligation_id"] == ligation["ligation_id"]
    assert state.screening_plates
    plate_id = next(iter(state.screening_plates))
    plate = state.screening_plates[plate_id]
    assert len([c for c in plate.colonies.values() if c.color == "white"]) == 12
    assert len([c for c in plate.colonies.values() if c.color == "blue"]) == 18


def test_clone_workflow_is_deterministic_on_same_seed():
    state_a, _, _, ligation_a, transform_a = _run_good_clone_core("clone-det-a", 42)
    state_b, _, _, ligation_b, transform_b = _run_good_clone_core("clone-det-b", 42)
    assert transform_a == transform_b
    recombinants_a = sorted(
        c.colony_id
        for c in next(iter(state_a.screening_plates.values())).colonies.values()
        if c.is_recombinant
    )
    recombinants_b = sorted(
        c.colony_id
        for c in next(iter(state_b.screening_plates.values())).colonies.values()
        if c.is_recombinant
    )
    assert recombinants_a == recombinants_b


GOLDEN_GATE_PARAMETERS_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "parameters" / "golden_gate.json"
)


def _run_good_golden_gate_core(sample_id: str, seed: int):
    state = create_lab_state(sample_id=sample_id, seed=seed)
    list_golden_gate_substrates(state=state)
    assembly = golden_gate_assembly(
        state=state,
        fragment_ids=[
            "gg_backbone",
            "gg_insert_promoter",
            "gg_insert_cds",
            "gg_insert_terminator",
        ],
        enzyme_name="BsaI",
        ligase_name="T4 DNA ligase",
        cycle_count=30,
        digest_temperature_c=37.0,
        ligate_temperature_c=16.0,
    )
    return state, assembly


def test_golden_gate_parameter_bundle_exposes_required_values():
    bundle = load_golden_gate_parameters(GOLDEN_GATE_PARAMETERS_PATH)
    assert bundle.value("digest_cycling_temperature_c") == pytest.approx(37.0)
    assert bundle.value("ligate_cycling_temperature_c") == pytest.approx(16.0)
    assert bundle.integer("recommended_cycle_count_min") == 25
    assert bundle.integer("fragment_count") == 4
    assert "BsaI" in bundle.choices("accepted_type_iis_enzymes")
    assert bundle.text("preferred_ligase_name") == "T4 DNA ligase"


def test_list_golden_gate_substrates_returns_four_fragments():
    state = create_lab_state(sample_id="gg-list", seed=1)
    observation = list_golden_gate_substrates(state=state)
    assert observation["status"] == "golden_gate_substrates_ready"
    fragment_ids = {f["fragment_id"] for f in observation["fragments"]}
    assert {"gg_backbone", "gg_insert_promoter", "gg_insert_cds", "gg_insert_terminator"} == fragment_ids


def test_golden_gate_assembly_happy_path_status():
    _, assembly = _run_good_golden_gate_core("gg-happy", 1)
    assert assembly["status"] == "assembled"
    assert assembly["enzyme_normalized"] == "bsai"
    assert assembly["ligase_normalized"] == "t4 dna ligase"
    assert assembly["fragment_count"] == 4
    assert assembly["output_fragment_id"] is not None


def test_golden_gate_wrong_enzyme_is_flagged():
    state = create_lab_state(sample_id="gg-wrong-enzyme", seed=1)
    list_golden_gate_substrates(state=state)
    result = golden_gate_assembly(
        state=state,
        fragment_ids=[
            "gg_backbone",
            "gg_insert_promoter",
            "gg_insert_cds",
            "gg_insert_terminator",
        ],
        enzyme_name="EcoRI",
        ligase_name="T4 DNA ligase",
    )
    assert result["status"] == "wrong_enzyme"


def test_golden_gate_wrong_ligase_is_flagged():
    state = create_lab_state(sample_id="gg-wrong-ligase", seed=1)
    list_golden_gate_substrates(state=state)
    result = golden_gate_assembly(
        state=state,
        fragment_ids=[
            "gg_backbone",
            "gg_insert_promoter",
            "gg_insert_cds",
            "gg_insert_terminator",
        ],
        enzyme_name="BsaI",
        ligase_name="E. coli DNA ligase",
    )
    assert result["status"] == "wrong_ligase"


def test_transform_assembly_produces_culture():
    state, assembly = _run_good_golden_gate_core("gg-transform", 42)
    result = transform_assembly(state=state, assembly_id=assembly["assembly_id"])
    assert result["status"] == "transformed"
    assert result["assembly_id"] == assembly["assembly_id"]
    assert result["effective_assembly_efficiency"] > 0.5
