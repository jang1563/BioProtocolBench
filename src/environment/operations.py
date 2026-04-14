"""Minimal LabCraft operations for the Transform-01 task."""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Dict, List

from .observations import render_observation
from .state import (
    DigestReaction,
    DnaFragment,
    GelRun,
    GrowthCulture,
    GrowthMeasurement,
    LabState,
    LigationReaction,
    PcrReaction,
    PlatedSample,
    PreparedPlate,
    ScreeningColony,
    ScreeningPlate,
    TransformationCulture,
)
from .stochastic import (
    load_cloning_parameters,
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
_CLONING_PARAMETERS_PATH = Path(__file__).resolve().parents[2] / "data" / "parameters" / "cloning.json"
_CLONING_BUNDLE = None


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


def _cloning_bundle():
    global _CLONING_BUNDLE
    if _CLONING_BUNDLE is None:
        _CLONING_BUNDLE = load_cloning_parameters(_CLONING_PARAMETERS_PATH)
    return _CLONING_BUNDLE


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


def _normalize_enzyme_pair(enzyme_names: List[str]) -> List[str]:
    return sorted(_normalize_choice(name).replace(" ", "").lower() for name in enzyme_names)


def _ensure_cloning_substrates(state: LabState) -> None:
    if state.cloning_substrates_initialized:
        return
    bundle = _cloning_bundle()
    vector = DnaFragment(
        fragment_id="puc19_vector",
        name="pUC19 vector",
        length_bp=bundle.integer("vector_plasmid_length_bp"),
        concentration_ng_ul=50.0,
        is_circular=True,
        end_5_prime="circular",
        end_3_prime="circular",
        recognition_sites=["EcoRI", "BamHI", "HindIII"],
        notes=["Circular pUC19 cloning vector with EcoRI, BamHI, and HindIII sites in the MCS."],
    )
    insert = DnaFragment(
        fragment_id="insert_raw",
        name="Benign 950 bp PCR insert",
        length_bp=bundle.integer("insert_length_bp"),
        concentration_ng_ul=20.0,
        is_circular=False,
        end_5_prime="flanking_EcoRI_site",
        end_3_prime="flanking_BamHI_site",
        recognition_sites=["EcoRI", "BamHI"],
        notes=[
            "Linear PCR product with EcoRI and BamHI recognition sequences in the flanking primers."
        ],
    )
    state.dna_fragments[vector.fragment_id] = vector
    state.dna_fragments[insert.fragment_id] = insert
    state.cloning_substrates_initialized = True


def list_cloning_substrates(state: LabState) -> Dict[str, object]:
    _ensure_cloning_substrates(state)
    fragments = [
        {
            "fragment_id": fragment.fragment_id,
            "name": fragment.name,
            "length_bp": int(fragment.length_bp),
            "concentration_ng_ul": float(fragment.concentration_ng_ul),
            "is_circular": bool(fragment.is_circular),
            "end_5_prime": fragment.end_5_prime,
            "end_3_prime": fragment.end_3_prime,
            "recognition_sites": list(fragment.recognition_sites),
        }
        for fragment in state.dna_fragments.values()
    ]
    payload = {
        "status": "cloning_substrates_ready",
        "fragments": fragments,
    }
    state.log_event("list_cloning_substrates", payload)
    return payload


def restriction_digest(
    state: LabState,
    fragment_id: str,
    enzyme_names: List[str],
    buffer: str,
    temperature_c: float,
    duration_minutes: int,
    heat_inactivate_after: bool,
    heat_inactivation_temperature_c: float = 65.0,
) -> Dict[str, object]:
    """Simulate a restriction digest on a DNA fragment."""
    _ensure_cloning_substrates(state)
    if fragment_id not in state.dna_fragments:
        raise ValueError(
            "Unknown fragment_id '{:s}'. Available fragment IDs: {:s}".format(
                fragment_id, ", ".join(sorted(state.dna_fragments))
            )
        )
    bundle = _cloning_bundle()
    substrate = state.dna_fragments[fragment_id]
    compatible_buffers = {b.lower() for b in bundle.choices("compatible_double_digest_buffers")}
    normalized_enzymes = _normalize_enzyme_pair(enzyme_names)
    optimal_duration = bundle.integer("digest_minimum_duration_minutes")
    optimal_temperature = bundle.value("digest_temperature_c")
    heat_inactivation_target = bundle.value("digest_heat_inactivation_temperature_c")

    notes: List[str] = []
    status = "digested"

    if len(enzyme_names) != 2 or normalized_enzymes != ["bamhi", "ecori"]:
        status = "wrong_enzyme_pair"
        notes.append(
            "Digest did not use the EcoRI + BamHI pair required for this directional cloning workflow."
        )
    if buffer.lower() not in compatible_buffers:
        status = "wrong_buffer"
        notes.append("Digest buffer is not compatible with simultaneous EcoRI + BamHI activity.")
    if abs(float(temperature_c) - optimal_temperature) > 2.0:
        notes.append("Digest temperature deviated from the 37 C optimum.")
    if int(duration_minutes) < optimal_duration:
        notes.append(
            "Digest duration was shorter than the {} min minimum recommended for complete plasmid digestion.".format(
                optimal_duration
            )
        )
        if status == "digested":
            status = "incomplete_digest"

    if heat_inactivate_after and abs(float(heat_inactivation_temperature_c) - heat_inactivation_target) > 2.0:
        notes.append(
            "Heat inactivation temperature deviated from the {:.0f} C recommendation.".format(
                heat_inactivation_target
            )
        )

    digest_id = state.next_digest_id()
    output_fragment_ids: List[str] = []
    if status in {"digested", "incomplete_digest"}:
        output_id = state.next_fragment_id()
        is_vector = substrate.is_circular
        end_5 = "EcoRI_overhang"
        end_3 = "BamHI_overhang"
        length_bp = substrate.length_bp
        if is_vector:
            length_bp = substrate.length_bp
        output_fragment = DnaFragment(
            fragment_id=output_id,
            name="{} (EcoRI+BamHI digested)".format(substrate.name),
            length_bp=int(length_bp),
            concentration_ng_ul=float(substrate.concentration_ng_ul) * 0.9,
            is_circular=False,
            end_5_prime=end_5,
            end_3_prime=end_3,
            recognition_sites=["EcoRI", "BamHI"],
            parent_fragment_id=substrate.fragment_id,
            notes=[
                "Linearized fragment with compatible EcoRI (5' overhang: AATT) and BamHI (5' overhang: GATC) ends."
            ],
        )
        state.dna_fragments[output_id] = output_fragment
        output_fragment_ids.append(output_id)

    reaction = DigestReaction(
        digest_id=digest_id,
        substrate_fragment_id=fragment_id,
        enzyme_names=list(enzyme_names),
        buffer=buffer,
        temperature_c=float(temperature_c),
        duration_minutes=int(duration_minutes),
        heat_inactivate_after=bool(heat_inactivate_after),
        status=status,
        output_fragment_ids=list(output_fragment_ids),
        notes=list(notes),
    )
    state.digest_reactions[digest_id] = reaction
    enzymes_key = "+".join(normalized_enzymes)
    payload = {
        "status": status,
        "digest_id": digest_id,
        "substrate_fragment_id": fragment_id,
        "enzyme_names": list(enzyme_names),
        "enzymes_key": enzymes_key,
        "buffer": buffer,
        "buffer_normalized": _normalize_choice(buffer).replace(" ", "").lower(),
        "temperature_c": float(temperature_c),
        "duration_minutes": int(duration_minutes),
        "heat_inactivate_after": bool(heat_inactivate_after),
        "output_fragment_ids": list(output_fragment_ids),
        "notes": list(notes),
    }
    state.log_event("restriction_digest", payload)
    return payload


def _resolve_ligation_fragment_id(state: LabState, fragment_id: str) -> str:
    """Resolve a fragment reference that may be a fragment_id or a digest_id shorthand."""
    requested = str(fragment_id).strip()
    if requested in state.dna_fragments:
        return requested
    if requested in state.digest_reactions:
        outputs = state.digest_reactions[requested].output_fragment_ids
        if outputs:
            return outputs[0]
    suffix_match = re.search(r"(\d+)$", requested)
    if suffix_match:
        canonical_digest = "digest_{:03d}".format(int(suffix_match.group(1)))
        if canonical_digest in state.digest_reactions:
            outputs = state.digest_reactions[canonical_digest].output_fragment_ids
            if outputs:
                return outputs[0]
        canonical_fragment = "fragment_{:03d}".format(int(suffix_match.group(1)))
        if canonical_fragment in state.dna_fragments:
            return canonical_fragment
    available_frags = sorted(state.dna_fragments)
    available_digests = sorted(state.digest_reactions)
    raise ValueError(
        "Unknown fragment reference '{:s}'. Available fragment IDs: {:s}. Available digest IDs: {:s}.".format(
            requested,
            ", ".join(available_frags) if available_frags else "none",
            ", ".join(available_digests) if available_digests else "none",
        )
    )


def ligate(
    state: LabState,
    vector_fragment_id: str,
    insert_fragment_ids: List[str],
    ligase_name: str,
    vector_to_insert_molar_ratio: float,
    temperature_c: float,
    duration_minutes: int,
    buffer: str = "T4 DNA ligase buffer",
) -> Dict[str, object]:
    """Simulate a ligation reaction and return a ligation id."""
    _ensure_cloning_substrates(state)
    vector_fragment_id = _resolve_ligation_fragment_id(state, vector_fragment_id)
    insert_fragment_ids = [
        _resolve_ligation_fragment_id(state, insert_id) for insert_id in insert_fragment_ids
    ]

    bundle = _cloning_bundle()
    required_ligase = bundle.text("preferred_ligase_name")
    acceptable_temps = [float(t) for t in bundle.choices("acceptable_ligation_temperatures_c")]
    minimum_duration = bundle.integer("acceptable_ligation_duration_minutes_min")
    base_fraction = bundle.value("base_recombinant_fraction_among_white_colonies")

    vector = state.dna_fragments[vector_fragment_id]
    inserts = [state.dna_fragments[i] for i in insert_fragment_ids]

    notes: List[str] = []
    status = "ligated"
    effective_fraction = base_fraction

    if _normalize_choice(ligase_name) != _normalize_choice(required_ligase):
        status = "wrong_ligase"
        notes.append(
            "Non-T4 ligase used; T4 DNA ligase is required for ATP-dependent cohesive-end ligation in this workflow."
        )
        effective_fraction *= 0.10

    if vector.end_5_prime == "circular" or vector.end_3_prime == "circular":
        notes.append("Vector appears to be an uncut circular plasmid; digest it before ligation.")
        if status == "ligated":
            status = "incompatible_ends"
        effective_fraction *= 0.05

    for insert in inserts:
        if insert.end_5_prime in {"flanking_EcoRI_site", "flanking_BamHI_site", "blunt", "circular"}:
            notes.append(
                "Insert {} has unprocessed ends and may not ligate efficiently without digestion.".format(
                    insert.fragment_id
                )
            )
            if status == "ligated":
                status = "incompatible_ends"
            effective_fraction *= 0.10

    ratio = float(vector_to_insert_molar_ratio)
    if ratio <= 0:
        notes.append("Vector:insert molar ratio must be positive.")
        status = "wrong_ratio"
        effective_fraction *= 0.0
    elif ratio < 0.1 or ratio > 10.0:
        notes.append("Vector:insert molar ratio is outside the standard 1:10 - 10:1 range.")
        if status == "ligated":
            status = "wrong_ratio"
        effective_fraction *= 0.5

    if not any(abs(float(temperature_c) - t) <= 1.0 for t in acceptable_temps):
        notes.append(
            "Ligation temperature {:.1f} C is outside the acceptable set {}.".format(
                float(temperature_c), acceptable_temps
            )
        )
        effective_fraction *= 0.5

    if int(duration_minutes) < minimum_duration:
        notes.append(
            "Ligation duration was shorter than the {} min minimum.".format(minimum_duration)
        )
        effective_fraction *= 0.5

    parent_digests = [
        state.dna_fragments[fragment_id].parent_fragment_id
        for fragment_id in [vector_fragment_id] + list(insert_fragment_ids)
        if state.dna_fragments[fragment_id].parent_fragment_id
    ]
    if not any(
        any(
            reaction.heat_inactivate_after
            for reaction in state.digest_reactions.values()
            if reaction.substrate_fragment_id == parent_id
        )
        for parent_id in parent_digests
    ) and parent_digests:
        notes.append(
            "Digests feeding this ligation were not heat-inactivated; residual nuclease may degrade the ligation."
        )
        effective_fraction *= 0.30

    effective_fraction = max(0.0, min(1.0, float(effective_fraction)))

    yield_multiplier = 1.0 if status == "ligated" else 0.25
    expected_transformant_yield = 400.0 * yield_multiplier * (effective_fraction / base_fraction + 0.1)

    ligation_id = state.next_ligation_id()
    reaction = LigationReaction(
        ligation_id=ligation_id,
        vector_fragment_id=vector_fragment_id,
        insert_fragment_ids=list(insert_fragment_ids),
        ligase_name=ligase_name,
        vector_to_insert_molar_ratio=float(ratio),
        temperature_c=float(temperature_c),
        duration_minutes=int(duration_minutes),
        status=status,
        effective_recombinant_fraction=float(effective_fraction),
        expected_transformant_yield=float(expected_transformant_yield),
        notes=list(notes),
    )
    state.ligation_reactions[ligation_id] = reaction
    payload = {
        "status": status,
        "ligation_id": ligation_id,
        "vector_fragment_id": vector_fragment_id,
        "insert_fragment_ids": list(insert_fragment_ids),
        "ligase_name": ligase_name,
        "ligase_normalized": _normalize_choice(ligase_name),
        "vector_to_insert_molar_ratio": float(ratio),
        "temperature_c": float(temperature_c),
        "duration_minutes": int(duration_minutes),
        "buffer": buffer,
        "notes": list(notes),
    }
    state.log_event("ligate", payload)
    return payload


def _resolve_ligation_id(state: LabState, ligation_id: str) -> str:
    requested = str(ligation_id).strip()
    if requested in state.ligation_reactions:
        return requested
    suffix_match = re.search(r"(\d+)$", requested)
    if suffix_match:
        canonical = "ligation_{:03d}".format(int(suffix_match.group(1)))
        if canonical in state.ligation_reactions:
            return canonical
    available = sorted(state.ligation_reactions)
    raise ValueError(
        "Unknown ligation_id '{:s}'. Available ligation IDs: {:s}".format(
            requested, ", ".join(available) if available else "none"
        )
    )


def transform_ligation(
    state: LabState,
    ligation_id: str,
    heat_shock_seconds: int = 30,
    recovery_minutes: int = 60,
    outgrowth_media: str = "SOC",
    shaking: bool = True,
    ice_incubation_minutes: int = 30,
) -> Dict[str, object]:
    """Transform a ligation reaction into competent E. coli and prepare a screening plate."""
    resolved_id = _resolve_ligation_id(state, ligation_id)
    ligation = state.ligation_reactions[resolved_id]
    screening_bundle = _screening_bundle()

    expected_yield = float(ligation.expected_transformant_yield)
    if int(heat_shock_seconds) != int(
        state.parameters.get("heat_shock_duration_seconds")["parameters"]["optimal"]
    ):
        expected_yield *= 0.5
    if outgrowth_media.upper() != "SOC":
        expected_yield *= 0.5
    if not shaking:
        expected_yield *= 0.7

    culture_id = state.next_culture_id()
    notes = list(ligation.notes)
    culture = TransformationCulture(
        culture_id=culture_id,
        plasmid_mass_pg=float(expected_yield * 1000.0),
        base_efficiency_cfu_per_ug=state.base_efficiency_cfu_per_ug,
        adjusted_efficiency_cfu_per_ug=state.base_efficiency_cfu_per_ug,
        recovery_minutes=int(recovery_minutes),
        outgrowth_media=outgrowth_media,
        shaking=bool(shaking),
        heat_shock_seconds=int(heat_shock_seconds),
        ice_incubation_minutes=int(ice_incubation_minutes),
        expected_total_transformants=expected_yield,
        notes=notes,
    )
    state.cultures[culture_id] = culture

    if not state.screening_plates:
        plate_id = state.next_screening_plate_id()
        recombinant_band_bp = screening_bundle.integer("screening_recombinant_colony_pcr_band_bp")
        empty_vector_band_bp = screening_bundle.integer("screening_empty_vector_colony_pcr_band_bp")
        plate = ScreeningPlate(
            plate_id=plate_id,
            historical_positive_rate_among_white=float(ligation.effective_recombinant_fraction),
            target_confidence=screening_bundle.value("screening_target_confidence"),
            recombinant_band_bp=recombinant_band_bp,
            empty_vector_band_bp=empty_vector_band_bp,
        )
        recombinant_whites: set = set()
        for idx in range(1, 13):
            if state.rng.random() < ligation.effective_recombinant_fraction:
                recombinant_whites.add("white_{:03d}".format(idx))
        for idx in range(1, 13):
            colony_id = "white_{:03d}".format(idx)
            is_recombinant = colony_id in recombinant_whites
            plate.colonies[colony_id] = ScreeningColony(
                colony_id=colony_id,
                color="white",
                is_recombinant=is_recombinant,
                expected_band_bp=recombinant_band_bp if is_recombinant else empty_vector_band_bp,
                notes=[
                    "White colony from Clone-01 transformation.",
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

    payload = {
        "status": "transformed",
        "culture_id": culture_id,
        "ligation_id": resolved_id,
        "ligation_status": ligation.status,
        "expected_transformants": float(expected_yield),
        "heat_shock_seconds": int(heat_shock_seconds),
        "recovery_minutes": int(recovery_minutes),
        "outgrowth_media": outgrowth_media,
        "notes": notes,
    }
    state.log_event("transform_ligation", payload)
    return payload
