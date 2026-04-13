"""Minimal LabCraft operations for the Transform-01 task."""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Dict, List

from .observations import render_observation
from .state import (
    GelRun,
    GrowthCulture,
    GrowthMeasurement,
    LabState,
    PcrReaction,
    PlatedSample,
    PreparedPlate,
    ScreeningColony,
    ScreeningPlate,
    TransformationCulture,
)
from .stochastic import (
    load_growth_parameters,
    load_pcr_parameters,
    load_screening_parameters,
    sample_poisson,
)

_GROWTH_PARAMETERS_PATH = Path(__file__).resolve().parents[2] / "data" / "parameters" / "growth.json"
_GROWTH_BUNDLE = None
_PCR_PARAMETERS_PATH = Path(__file__).resolve().parents[2] / "data" / "parameters" / "pcr.json"
_PCR_BUNDLE = None
_SCREENING_PARAMETERS_PATH = Path(__file__).resolve().parents[2] / "data" / "parameters" / "screening.json"
_SCREENING_BUNDLE = None


def _growth_bundle():
    global _GROWTH_BUNDLE
    if _GROWTH_BUNDLE is None:
        _GROWTH_BUNDLE = load_growth_parameters(_GROWTH_PARAMETERS_PATH)
    return _GROWTH_BUNDLE


def _pcr_bundle():
    global _PCR_BUNDLE
    if _PCR_BUNDLE is None:
        _PCR_BUNDLE = load_pcr_parameters(_PCR_PARAMETERS_PATH)
    return _PCR_BUNDLE


def _screening_bundle():
    global _SCREENING_BUNDLE
    if _SCREENING_BUNDLE is None:
        _SCREENING_BUNDLE = load_screening_parameters(_SCREENING_PARAMETERS_PATH)
    return _SCREENING_BUNDLE


def _normalize_choice(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def _resolve_pcr_reaction_id(state: LabState, reaction_id: str) -> str:
    """Resolve exact or shorthand PCR reaction identifiers to a canonical id."""
    requested = str(reaction_id).strip()
    if requested in state.pcr_reactions:
        return requested

    candidates: List[str] = []
    normalized_requested = _normalize_choice(requested)
    if normalized_requested:
        candidates.extend(
            existing_id
            for existing_id in state.pcr_reactions
            if _normalize_choice(existing_id) == normalized_requested
        )

    suffix_match = re.search(r"(\d+)$", requested)
    if suffix_match:
        suffix = int(suffix_match.group(1))
        canonical = "pcr_{:03d}".format(suffix)
        if canonical in state.pcr_reactions and canonical not in candidates:
            candidates.append(canonical)

    if len(candidates) == 1:
        return candidates[0]

    available = sorted(state.pcr_reactions)
    if not candidates:
        raise ValueError(
            "Unknown reaction_id '{:s}'. Available reaction IDs: {:s}".format(
                requested,
                ", ".join(available) if available else "none",
            )
        )
    raise ValueError(
        "Ambiguous reaction_id '{:s}'. Matching reaction IDs: {:s}".format(
            requested,
            ", ".join(sorted(candidates)),
        )
    )


def _ensure_screening_plate(state: LabState) -> ScreeningPlate:
    existing = next(iter(state.screening_plates.values()), None)
    if existing is not None:
        return existing

    bundle = _screening_bundle()
    plate_id = state.next_screening_plate_id()
    recombinant_band_bp = bundle.integer("screening_recombinant_colony_pcr_band_bp")
    empty_vector_band_bp = bundle.integer("screening_empty_vector_colony_pcr_band_bp")
    plate = ScreeningPlate(
        plate_id=plate_id,
        historical_positive_rate_among_white=bundle.value("historical_positive_rate_among_white_colonies"),
        target_confidence=bundle.value("screening_target_confidence"),
        recombinant_band_bp=recombinant_band_bp,
        empty_vector_band_bp=empty_vector_band_bp,
    )

    recombinant_white_ids = {"white_002", "white_005", "white_006", "white_011"}
    for idx in range(1, 13):
        colony_id = "white_{:03d}".format(idx)
        is_recombinant = colony_id in recombinant_white_ids
        plate.colonies[colony_id] = ScreeningColony(
            colony_id=colony_id,
            color="white",
            is_recombinant=is_recombinant,
            expected_band_bp=recombinant_band_bp if is_recombinant else empty_vector_band_bp,
            notes=[
                "White colony from blue-white screening.",
                "Expected insert-positive band near {:d} bp.".format(recombinant_band_bp)
                if is_recombinant
                else "White false positive with empty-vector-like colony PCR band.",
            ],
        )
    for idx in range(1, 19):
        colony_id = "blue_{:03d}".format(idx)
        plate.colonies[colony_id] = ScreeningColony(
            colony_id=colony_id,
            color="blue",
            is_recombinant=False,
            expected_band_bp=empty_vector_band_bp,
            notes=["Blue colony retaining lacZ alpha activity; treat as vector-only background."],
        )

    state.screening_plates[plate_id] = plate
    return plate


def prepare_media(
    state: LabState,
    medium: str,
    antibiotic: str,
    antibiotic_concentration_ug_ml: float,
    plate_count: int = 1,
) -> Dict[str, object]:
    """Prepare one or more selection plates."""
    plates = []
    for _ in range(plate_count):
        plate_id = state.next_plate_id()
        plate = PreparedPlate(
            plate_id=plate_id,
            medium=medium,
            antibiotic=antibiotic,
            antibiotic_concentration_ug_ml=float(antibiotic_concentration_ug_ml),
        )
        state.prepared_plates[plate_id] = plate
        plates.append(
            {
                "plate_id": plate_id,
                "medium": medium,
                "antibiotic": antibiotic,
                "antibiotic_concentration_ug_ml": float(antibiotic_concentration_ug_ml),
            }
        )
    payload = {
        "status": "prepared",
        "plates": plates,
    }
    state.log_event("prepare_media", payload)
    return payload


def transform(
    state: LabState,
    plasmid_mass_pg: float,
    heat_shock_seconds: int,
    recovery_minutes: int,
    outgrowth_media: str = "SOC",
    shaking: bool = True,
    ice_incubation_minutes: int = 30,
) -> Dict[str, object]:
    """Simulate a chemical transformation and return a culture identifier."""
    notes: List[str] = []
    efficiency = state.base_efficiency_cfu_per_ug
    efficiency *= state.parameters.ice_incubation_penalty(ice_incubation_minutes)
    efficiency *= state.parameters.recovery_penalty(recovery_minutes)
    if outgrowth_media.upper() == "SOC":
        efficiency *= state.parameters.soc_multiplier()
    else:
        efficiency *= state.parameters.lb_multiplier()
        notes.append("SOC was not used for outgrowth.")
    if shaking:
        efficiency *= state.parameters.shaking_multiplier()
    else:
        efficiency *= state.parameters.static_multiplier()
        notes.append("Outgrowth was not shaken.")
    if int(heat_shock_seconds) != int(state.parameters.get("heat_shock_duration_seconds")["parameters"]["optimal"]):
        notes.append("Heat shock duration deviated from the protocol optimum.")

    expected_total_transformants = efficiency * (float(plasmid_mass_pg) / 1_000_000.0)
    culture_id = state.next_culture_id()
    culture = TransformationCulture(
        culture_id=culture_id,
        plasmid_mass_pg=float(plasmid_mass_pg),
        base_efficiency_cfu_per_ug=state.base_efficiency_cfu_per_ug,
        adjusted_efficiency_cfu_per_ug=efficiency,
        recovery_minutes=int(recovery_minutes),
        outgrowth_media=outgrowth_media,
        shaking=bool(shaking),
        heat_shock_seconds=int(heat_shock_seconds),
        ice_incubation_minutes=int(ice_incubation_minutes),
        expected_total_transformants=expected_total_transformants,
        notes=notes,
    )
    state.cultures[culture_id] = culture
    payload = {
        "status": "transformed",
        "culture_id": culture_id,
        "plasmid_mass_pg": float(plasmid_mass_pg),
        "heat_shock_seconds": int(heat_shock_seconds),
        "recovery_minutes": int(recovery_minutes),
        "outgrowth_media": outgrowth_media,
        "notes": notes,
    }
    state.log_event("transform", payload)
    return payload


def plate(
    state: LabState,
    culture_id: str,
    plate_id: str,
    dilution_factor: float,
    volume_ul: float,
) -> Dict[str, object]:
    """Plate a transformed culture onto a prepared plate."""
    culture = state.cultures[culture_id]
    prepared_plate = state.prepared_plates[plate_id]
    warnings: List[str] = []
    countable_min, countable_max = state.parameters.countable_colony_range()
    recommended = state.parameters.recommended_antibiotic_concentration(prepared_plate.antibiotic or "")
    if recommended is None:
        status = "plated_without_reference"
        expected = culture.expected_total_transformants * (float(volume_ul) / 1000.0) / float(dilution_factor)
        observed = sample_poisson(state.rng, expected)
    elif float(prepared_plate.antibiotic_concentration_ug_ml) != float(recommended):
        status = "selection_failed"
        expected = None
        observed = None
        warnings.append("Selection plate concentration does not match the cited working concentration.")
    else:
        status = "plated"
        expected = culture.expected_total_transformants * (float(volume_ul) / 1000.0) / float(dilution_factor)
        observed = sample_poisson(state.rng, expected)
        if observed < countable_min or observed > countable_max:
            status = "count_out_of_range"
            warnings.append(
                "Observed colonies fall outside the cited countable range of "
                "{:d}-{:d} colonies per plate.".format(countable_min, countable_max)
            )

    plating_id = state.next_plating_id()
    plated_sample = PlatedSample(
        plating_id=plating_id,
        culture_id=culture_id,
        plate_id=plate_id,
        dilution_factor=float(dilution_factor),
        volume_ul=float(volume_ul),
        expected_colonies=expected,
        observed_colonies=observed,
        status=status,
        warnings=warnings,
    )
    state.plated_samples[plating_id] = plated_sample
    payload = {
        "status": status,
        "plating_id": plating_id,
        "plate_id": plate_id,
        "culture_id": culture_id,
        "dilution_factor": float(dilution_factor),
        "volume_ul": float(volume_ul),
        "countable_range_colonies": {"min": countable_min, "max": countable_max},
        "warnings": warnings,
    }
    state.log_event("plate", payload)
    return payload


def count_colonies(state: LabState, plating_id: str) -> Dict[str, object]:
    """Return the observed colony count for a plated sample."""
    plated_sample = state.plated_samples[plating_id]
    countable_min, countable_max = state.parameters.countable_colony_range()
    payload = {
        "status": plated_sample.status,
        "plating_id": plating_id,
        "observed_colonies": plated_sample.observed_colonies,
        "dilution_factor": plated_sample.dilution_factor,
        "volume_ul": plated_sample.volume_ul,
        "countable_range_colonies": {"min": countable_min, "max": countable_max},
        "warnings": plated_sample.warnings,
    }
    state.log_event("count_colonies", payload)
    return payload


def inoculate_growth(
    state: LabState,
    condition: str,
    starting_od600: float,
) -> Dict[str, object]:
    """Start a growth-characterization culture under a named condition."""
    bundle = _growth_bundle()
    doubling_time_map = {
        "LB": bundle.value("lb_doubling_time_minutes"),
        "M9 + glucose": bundle.value("m9_glucose_doubling_time_minutes"),
        "LB + chloramphenicol (1.8 uM)": (
            bundle.value("lb_doubling_time_minutes")
            / bundle.fraction("chloramphenicol_1_8uM_relative_growth_rate")
        ),
    }
    medium_map = {
        "LB": "LB",
        "M9 + glucose": "M9 + glucose",
        "LB + chloramphenicol (1.8 uM)": "LB + chloramphenicol (1.8 uM)",
    }
    if condition not in doubling_time_map:
        raise ValueError("Unknown growth condition: {:s}".format(condition))

    growth_id = state.next_growth_id()
    culture = GrowthCulture(
        growth_id=growth_id,
        condition=condition,
        medium=medium_map[condition],
        starting_od600=float(starting_od600),
        doubling_time_minutes=float(doubling_time_map[condition]),
    )
    state.growth_cultures[growth_id] = culture
    payload = {
        "status": "inoculated",
        "growth_id": growth_id,
        "condition": condition,
        "starting_od600": float(starting_od600),
        "doubling_time_minutes": float(doubling_time_map[condition]),
    }
    state.log_event("inoculate_growth", payload)
    return payload


def incubate(
    state: LabState,
    growth_id: str,
    duration_minutes: int,
) -> Dict[str, object]:
    """Advance a growth culture in time."""
    culture = state.growth_cultures[growth_id]
    culture.current_time_minutes += int(duration_minutes)
    payload = {
        "status": "incubated",
        "growth_id": growth_id,
        "condition": culture.condition,
        "duration_minutes": int(duration_minutes),
        "elapsed_minutes": int(culture.current_time_minutes),
    }
    state.log_event("incubate", payload)
    return payload


def _true_growth_od600(culture: GrowthCulture) -> float:
    return culture.starting_od600 * math.pow(2.0, culture.current_time_minutes / culture.doubling_time_minutes)


def measure_od600(
    state: LabState,
    growth_id: str,
    dilution_factor: float = 1.0,
) -> Dict[str, object]:
    """Measure OD600 for a growth culture, optionally after dilution."""
    culture = state.growth_cultures[growth_id]
    true_od600 = _true_growth_od600(culture)
    observed_od600 = true_od600 / float(dilution_factor)
    measurement = GrowthMeasurement(
        elapsed_minutes=int(culture.current_time_minutes),
        dilution_factor=float(dilution_factor),
        observed_od600=float(observed_od600),
        estimated_undiluted_od600=float(observed_od600 * float(dilution_factor)),
    )
    culture.measurements.append(measurement)
    payload = {
        "status": "measured",
        "growth_id": growth_id,
        "condition": culture.condition,
        "elapsed_minutes": int(culture.current_time_minutes),
        "dilution_factor": float(dilution_factor),
        "observed_od600": float(observed_od600),
        "estimated_undiluted_od600": float(measurement.estimated_undiluted_od600),
    }
    state.log_event("measure_od600", payload)
    return payload


def fit_growth_curve(
    state: LabState,
    growth_id: str,
) -> Dict[str, object]:
    """Estimate doubling time from the measured OD600 trajectory."""
    bundle = _growth_bundle()
    culture = state.growth_cultures[growth_id]
    lower_fraction = bundle.fraction("growth_fit_lower_fraction_of_max_observed_od600")
    upper_fraction = bundle.fraction("growth_fit_upper_fraction_of_max_observed_od600")
    if not culture.measurements:
        payload = {
            "status": "insufficient_points",
            "growth_id": growth_id,
            "condition": culture.condition,
            "qualifying_points": 0,
            "warnings": ["No OD600 measurements were collected before attempting the fit."],
        }
        state.log_event("fit_growth_curve", payload)
        return payload

    max_observed = max(m.estimated_undiluted_od600 for m in culture.measurements)
    lower_bound = lower_fraction * max_observed
    upper_bound = upper_fraction * max_observed
    qualifying = [
        m for m in culture.measurements if lower_bound <= m.estimated_undiluted_od600 <= upper_bound
    ]

    if len(qualifying) < 3:
        payload = {
            "status": "insufficient_points",
            "growth_id": growth_id,
            "condition": culture.condition,
            "qualifying_points": len(qualifying),
            "lower_bound_od600": float(lower_bound),
            "upper_bound_od600": float(upper_bound),
            "warnings": [
                "Fewer than three OD600 measurements fell inside the cited fitting window."
            ],
        }
        state.log_event("fit_growth_curve", payload)
        return payload

    first = qualifying[0]
    last = qualifying[-1]
    slope_per_minute = (
        math.log(last.estimated_undiluted_od600) - math.log(first.estimated_undiluted_od600)
    ) / float(last.elapsed_minutes - first.elapsed_minutes)
    estimated_doubling_time = math.log(2.0) / slope_per_minute
    payload = {
        "status": "analyzable",
        "growth_id": growth_id,
        "condition": culture.condition,
        "qualifying_points": len(qualifying),
        "lower_bound_od600": float(lower_bound),
        "upper_bound_od600": float(upper_bound),
        "estimated_doubling_time_minutes": float(estimated_doubling_time),
        "max_observed_od600": float(max_observed),
        "warnings": [],
    }
    state.log_event("fit_growth_curve", payload)
    return payload


def run_pcr(
    state: LabState,
    polymerase_name: str,
    additive: str,
    extension_seconds: int,
    cycle_count: int,
) -> Dict[str, object]:
    """Run a single PCR attempt for the GC-rich LabCraft PCR task."""
    bundle = _pcr_bundle()
    target_size_bp = 2000
    high_fidelity_polymerases = {
        _normalize_choice(name) for name in bundle.values("gc_rich_high_fidelity_polymerases")
    }
    helpful_additives = {_normalize_choice(name) for name in bundle.values("gc_rich_additives")}
    extension_min, extension_max = bundle.range("gc_rich_extension_seconds_for_2kb_amplicon")
    cycles_min, cycles_max = bundle.range("genomic_pcr_cycle_count_range")

    normalized_polymerase = _normalize_choice(polymerase_name)
    normalized_additive = _normalize_choice(additive)
    status = "clean_target_band"
    visible_bands_bp = [target_size_bp]
    smear_present = False
    notes: List[str] = []

    if normalized_polymerase not in high_fidelity_polymerases:
        status = "nonspecific_amplification"
        visible_bands_bp = [850, target_size_bp]
        smear_present = True
        notes.append("A non-proofreading polymerase was used for a GC-rich genomic amplicon.")
    elif normalized_additive not in helpful_additives:
        status = "gc_rich_failure"
        visible_bands_bp = []
        notes.append("No GC-resolving additive was used for the GC-rich template.")
    elif float(extension_seconds) < extension_min:
        status = "truncated_product"
        visible_bands_bp = [1200]
        notes.append("Extension time was shorter than the cited range for a 2 kb amplicon.")
    elif float(cycle_count) < cycles_min:
        status = "low_yield_target_band"
        visible_bands_bp = [target_size_bp]
        notes.append("Cycle count was below the recommended range for genomic PCR.")
    elif float(cycle_count) > cycles_max:
        status = "nonspecific_amplification"
        visible_bands_bp = [1400, target_size_bp]
        smear_present = True
        notes.append("Cycle count exceeded the recommended range for genomic PCR.")
    elif float(extension_seconds) > extension_max * 2.0:
        status = "nonspecific_amplification"
        visible_bands_bp = [target_size_bp]
        smear_present = True
        notes.append("Extension time was excessively long for the 2 kb target.")

    reaction_id = state.next_pcr_id()
    reaction = PcrReaction(
        reaction_id=reaction_id,
        polymerase_name=polymerase_name,
        additive=additive,
        extension_seconds=int(extension_seconds),
        cycle_count=int(cycle_count),
        target_size_bp=target_size_bp,
        status=status,
        visible_bands_bp=visible_bands_bp,
        smear_present=smear_present,
        notes=notes,
    )
    state.pcr_reactions[reaction_id] = reaction
    payload = {
        "status": status,
        "reaction_id": reaction_id,
        "polymerase_name": polymerase_name,
        "normalized_polymerase_name": (
            "Q5 High-Fidelity DNA polymerase"
            if "q5" in normalized_polymerase
            else "Phusion High-Fidelity DNA polymerase"
            if "phusion" in normalized_polymerase
            else "Taq DNA polymerase"
            if "taq" in normalized_polymerase
            else polymerase_name
        ),
        "additive": additive,
        "normalized_additive": (
            "DMSO"
            if "dmso" in normalized_additive
            else "Betaine"
            if "betaine" in normalized_additive
            else "none"
            if normalized_additive in {"none", "no additive", "not used"}
            else additive
        ),
        "extension_seconds": int(extension_seconds),
        "cycle_count": int(cycle_count),
        "target_size_bp": target_size_bp,
        "visible_bands_bp": visible_bands_bp,
        "smear_present": smear_present,
        "notes": notes,
    }
    state.log_event("run_pcr", payload)
    return payload


def run_gel(
    state: LabState,
    reaction_id: str,
    agarose_percent: float = 1.0,
    ladder_name: str = "1 kb DNA Ladder",
) -> Dict[str, object]:
    """Run a simple agarose-gel readout for a PCR reaction."""
    canonical_reaction_id = _resolve_pcr_reaction_id(state, reaction_id)
    reaction = state.pcr_reactions[canonical_reaction_id]
    status_map = {
        "clean_target_band": "single_clean_target_band",
        "low_yield_target_band": "faint_target_band",
        "truncated_product": "wrong_size_band",
        "gc_rich_failure": "no_visible_product",
        "nonspecific_amplification": "multiple_bands_or_smear",
    }
    status = status_map[reaction.status]
    notes = list(reaction.notes)
    if reaction.status == "clean_target_band":
        notes.append("A single strong band is visible near 2 kb.")
    elif reaction.status == "low_yield_target_band":
        notes.append("A faint band is visible near 2 kb.")
    elif reaction.status == "truncated_product":
        notes.append("A shorter-than-expected band is visible.")
    elif reaction.status == "gc_rich_failure":
        notes.append("No visible PCR product is present.")
    elif reaction.status == "nonspecific_amplification":
        notes.append("Multiple bands and/or smear are visible.")

    gel_id = state.next_gel_id()
    gel = GelRun(
        gel_id=gel_id,
        reaction_id=canonical_reaction_id,
        ladder_name=ladder_name,
        agarose_percent=float(agarose_percent),
        status=status,
        visible_bands_bp=list(reaction.visible_bands_bp),
        smear_present=bool(reaction.smear_present),
        notes=notes,
    )
    state.gel_runs[gel_id] = gel
    payload = {
        "status": status,
        "gel_id": gel_id,
        "reaction_id": canonical_reaction_id,
        "polymerase_name": reaction.polymerase_name,
        "normalized_polymerase_name": (
            "Q5 High-Fidelity DNA polymerase"
            if "q5" in _normalize_choice(reaction.polymerase_name)
            else "Phusion High-Fidelity DNA polymerase"
            if "phusion" in _normalize_choice(reaction.polymerase_name)
            else "Taq DNA polymerase"
            if "taq" in _normalize_choice(reaction.polymerase_name)
            else reaction.polymerase_name
        ),
        "additive": reaction.additive,
        "normalized_additive": (
            "DMSO"
            if "dmso" in _normalize_choice(reaction.additive)
            else "Betaine"
            if "betaine" in _normalize_choice(reaction.additive)
            else "none"
            if _normalize_choice(reaction.additive) in {"none", "no additive", "not used"}
            else reaction.additive
        ),
        "extension_seconds": int(reaction.extension_seconds),
        "cycle_count": int(reaction.cycle_count),
        "target_size_bp": int(reaction.target_size_bp),
        "visible_bands_bp": list(reaction.visible_bands_bp),
        "smear_present": bool(reaction.smear_present),
        "agarose_percent": float(agarose_percent),
        "ladder_name": ladder_name,
        "notes": notes,
    }
    state.log_event("run_gel", payload)
    return payload


def inspect_screening_plate(state: LabState) -> Dict[str, object]:
    """Return the fixed blue-white screening plate for Screen-01."""
    plate = _ensure_screening_plate(state)
    white_ids = sorted(colony_id for colony_id, colony in plate.colonies.items() if colony.color == "white")
    blue_ids = sorted(colony_id for colony_id, colony in plate.colonies.items() if colony.color == "blue")
    payload = {
        "status": "screening_plate_ready",
        "plate_id": plate.plate_id,
        "white_colony_ids": white_ids,
        "blue_colony_ids": blue_ids,
        "white_colony_count": len(white_ids),
        "blue_colony_count": len(blue_ids),
        "historical_positive_rate_among_white": float(plate.historical_positive_rate_among_white),
        "target_confidence": float(plate.target_confidence),
        "recombinant_band_bp": int(plate.recombinant_band_bp),
        "empty_vector_band_bp": int(plate.empty_vector_band_bp),
        "notes": [
            "White colonies are enriched for inserts but may include false positives.",
            "Blue colonies should be treated as vector-only background in this task.",
        ],
    }
    state.log_event("inspect_screening_plate", payload)
    return payload


def run_colony_pcr(
    state: LabState,
    colony_ids: List[str],
    primer_pair: str = "M13/pUC flank primers",
) -> Dict[str, object]:
    """Run colony PCR on the requested blue-white screening colonies."""
    if not colony_ids:
        raise ValueError("run_colony_pcr requires at least one colony_id.")

    plate = _ensure_screening_plate(state)
    results = []
    batch_screening_strategy = "white_only"
    batch_confirmed = []
    for colony_id in colony_ids:
        if colony_id not in plate.colonies:
            raise ValueError(
                "Unknown colony_id '{:s}'. Available colony IDs: {:s}".format(
                    colony_id,
                    ", ".join(sorted(plate.colonies)),
                )
            )
        colony = plate.colonies[colony_id]
        if colony.color != "white":
            batch_screening_strategy = "includes_blue"
        if colony_id not in plate.screened_colony_ids:
            plate.screened_colony_ids.append(colony_id)
        result = {
            "colony_id": colony.colony_id,
            "color": colony.color,
            "status": "recombinant_positive" if colony.is_recombinant else "empty_vector_or_background",
            "visible_bands_bp": [int(colony.expected_band_bp)],
            "notes": list(colony.notes),
        }
        results.append(result)
        if colony.is_recombinant:
            batch_confirmed.append(colony.colony_id)

    cumulative_white_ids = [
        colony_id
        for colony_id in plate.screened_colony_ids
        if plate.colonies[colony_id].color == "white"
    ]
    confidence = 1.0 - math.pow(
        1.0 - float(plate.historical_positive_rate_among_white),
        len(cumulative_white_ids),
    )
    cumulative_confirmed = sorted(
        colony_id
        for colony_id in plate.screened_colony_ids
        if plate.colonies[colony_id].is_recombinant
    )
    payload = {
        "status": "screened",
        "plate_id": plate.plate_id,
        "primer_pair": primer_pair,
        "screened_colony_ids": list(colony_ids),
        "screened_colony_count": len(colony_ids),
        "screening_strategy": batch_screening_strategy,
        "colony_pcr_used": True,
        "results": results,
        "confirmed_recombinant_ids_in_batch": sorted(batch_confirmed),
        "confirmed_recombinant_ids_cumulative": cumulative_confirmed,
        "cumulative_screened_white_colony_count": len(cumulative_white_ids),
        "cumulative_confidence_pct": round(confidence * 100.0, 1),
        "recombinant_band_bp": int(plate.recombinant_band_bp),
        "empty_vector_band_bp": int(plate.empty_vector_band_bp),
    }
    state.log_event("run_colony_pcr", payload)
    return payload
