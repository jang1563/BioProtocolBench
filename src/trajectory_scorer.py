"""Trajectory scoring for LabCraft tasks."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List

TARGET_MASSES_PG = (10, 100, 1000, 10000)
TASK_SUCCESS_RELATIVE_TOLERANCE = 0.2
GROWTH_CONDITIONS = (
    "LB",
    "M9 + glucose",
    "LB + chloramphenicol (1.8 uM)",
)
GROWTH_TASK_SUCCESS_RELATIVE_TOLERANCE = 0.15
PCR_TARGET_BAND_REGEX = re.compile(r"(single\s+clean[\s\S]{0,40}(?:2(?:\.0)?\s*kb|2000\s*bp))|((?:2(?:\.0)?\s*kb|2000\s*bp)[\s\S]{0,40}single\s+clean)", re.IGNORECASE)
SCREEN_CONFIDENCE_ABSOLUTE_TOLERANCE = 0.2


def load_ground_truth(path: str) -> Dict[str, Any]:
    with open(path) as handle:
        return json.load(handle)


def _extract_tool_calls(transcript: Iterable[Any]) -> List[Dict[str, Any]]:
    calls: List[Dict[str, Any]] = []
    calls_by_id: Dict[str, Dict[str, Any]] = {}

    def append_or_merge(call: Dict[str, Any]) -> None:
        call_id = call.get("call_id")
        if call_id and call_id in calls_by_id:
            existing = calls_by_id[call_id]
            existing_args = _coerce_arguments(existing.get("arguments"))
            incoming_args = _coerce_arguments(call.get("arguments"))
            incoming_content = _coerce_content_dict(call.get("content"))
            existing["arguments"] = {**incoming_content, **existing_args, **incoming_args}
            if call.get("tool_name"):
                existing["tool_name"] = call["tool_name"]
            if call.get("content") is not None:
                existing["content"] = call.get("content")
            return

        calls.append(call)
        if call_id:
            calls_by_id[call_id] = call

    for item in transcript:
        if isinstance(item, dict) and item.get("type") == "tool_call":
            append_or_merge(item)
            continue

        if isinstance(item, dict) and item.get("tool_calls"):
            for call in item.get("tool_calls", []):
                append_or_merge(
                    {
                        "type": "tool_call",
                        "tool_name": call.get("function"),
                        "arguments": call.get("arguments", {}) or {},
                        "content": item.get("content"),
                        "call_id": call.get("id"),
                    }
                )
            continue

        if isinstance(item, dict) and item.get("role") == "tool":
            append_or_merge(
                {
                    "type": "tool_call",
                    "tool_name": item.get("function") or item.get("name"),
                    "arguments": item.get("arguments", {}) or {},
                    "content": item.get("content"),
                    "call_id": item.get("tool_call_id"),
                }
            )
            continue

        role = getattr(item, "role", None)
        if role == "tool":
            append_or_merge(
                {
                    "type": "tool_call",
                    "tool_name": getattr(item, "name", None),
                    "arguments": getattr(item, "arguments", {}) or {},
                    "content": getattr(item, "content", None),
                    "call_id": getattr(item, "tool_call_id", None),
                }
            )
            continue

        tool_calls = getattr(item, "tool_calls", None)
        if tool_calls:
            for call in tool_calls:
                append_or_merge(
                    {
                        "type": "tool_call",
                        "tool_name": getattr(call, "function", getattr(call, "name", None)),
                        "arguments": getattr(call, "arguments", {}) or {},
                        "content": getattr(call, "content", None),
                        "call_id": getattr(call, "id", None),
                    }
                )
    return calls


def _normalize_tool_name(name: Any) -> str:
    if name is None:
        return ""
    if not isinstance(name, str):
        name = str(name)
    if name.endswith("_tool_impl"):
        return name[: -len("_tool_impl")]
    return name


def _coerce_arguments(arguments: Any) -> Dict[str, Any]:
    if isinstance(arguments, dict):
        return arguments
    if isinstance(arguments, str):
        try:
            return json.loads(arguments)
        except Exception:
            return {}
    return {}


def _coerce_content_dict(content: Any) -> Dict[str, Any]:
    if isinstance(content, dict):
        return content
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _matches_filters(arguments: Dict[str, Any], filters: Dict[str, Any]) -> bool:
    for key, expected in filters.items():
        if arguments.get(key) != expected:
            return False
    return True


def _observed_values(call: Dict[str, Any]) -> Dict[str, Any]:
    arguments = _coerce_arguments(call.get("arguments"))
    content_values = _coerce_content_dict(call.get("content"))
    return {**content_values, **arguments}


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.replace(",", "").strip()
    try:
        return float(value)
    except Exception:
        return None


def _coerce_int(value: Any) -> int | None:
    as_float = _coerce_float(value)
    if as_float is None:
        return None
    return int(round(as_float))


def _parse_scientific_number(value: str) -> float | None:
    normalized = value.replace(",", "").strip()
    normalized = re.sub(r"\s*[x×]\s*10\^?\s*([+-]?\d+)", r"e\1", normalized, flags=re.IGNORECASE)
    try:
        return float(normalized)
    except Exception:
        return None


def _extract_reported_efficiencies(final_answer: str) -> Dict[int, float]:
    reported: Dict[int, float] = {}
    unit_pattern = r"cfu\s*(?:/|per)\s*(?:u|μ|µ|\\mu)?g|cfu\s+per\s+microgram"
    numeric_pattern = r"([-+]?\d[\d,]*(?:\.\d+)?(?:\s*[x×]\s*10\^?\s*[+-]?\d+|e[+-]?\d+)?)"
    mass_patterns = {
        10: r"10\s*pg",
        100: r"100\s*pg",
        1000: r"1,?000\s*pg",
        10000: r"10,?000\s*pg",
    }

    for mass_pg, mass_pattern in mass_patterns.items():
        matches = list(
            re.finditer(
                rf"{mass_pattern}[\s\S]{{0,160}}?{numeric_pattern}\s*(?:{unit_pattern})",
                final_answer,
                flags=re.IGNORECASE,
            )
        )
        if not matches:
            continue
        parsed = _parse_scientific_number(matches[-1].group(1))
        if parsed is not None:
            reported[mass_pg] = parsed
    return reported


def _calculate_cfu_per_ug(observed_colonies: Any, dilution_factor: Any, volume_ul: Any, plasmid_mass_pg: Any) -> float | None:
    observed = _coerce_float(observed_colonies)
    dilution = _coerce_float(dilution_factor)
    volume = _coerce_float(volume_ul)
    mass_pg = _coerce_float(plasmid_mass_pg)
    if observed is None or dilution is None or volume is None or mass_pg is None:
        return None
    if observed < 0 or dilution <= 0 or volume <= 0 or mass_pg <= 0:
        return None
    mass_ug = mass_pg / 1_000_000.0
    return observed * dilution / (volume / 1000.0) / mass_ug


def _reconstruct_measurements(tool_calls: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    culture_to_mass: Dict[str, int] = {}
    plating_to_context: Dict[str, Dict[str, Any]] = {}
    measurements: Dict[int, Dict[str, Any]] = {}

    for call in tool_calls:
        observed = _observed_values(call)
        tool_name = _normalize_tool_name(call.get("tool_name", ""))

        if tool_name == "transform":
            culture_id = observed.get("culture_id")
            mass_pg = _coerce_int(observed.get("plasmid_mass_pg"))
            if culture_id and mass_pg is not None:
                culture_to_mass[culture_id] = mass_pg

        if tool_name == "plate":
            plating_id = observed.get("plating_id")
            if plating_id:
                plating_to_context[plating_id] = observed

    for call in tool_calls:
        if _normalize_tool_name(call.get("tool_name", "")) != "count_colonies":
            continue

        observed = _observed_values(call)
        plating_id = observed.get("plating_id")
        if not plating_id:
            continue
        plating_context = plating_to_context.get(plating_id, {})
        culture_id = observed.get("culture_id") or plating_context.get("culture_id")
        if not culture_id:
            continue
        mass_pg = culture_to_mass.get(culture_id)
        if mass_pg is None:
            continue

        status = observed.get("status") or plating_context.get("status")
        warnings = list(observed.get("warnings") or plating_context.get("warnings") or [])
        dilution_factor = observed.get("dilution_factor", plating_context.get("dilution_factor"))
        volume_ul = observed.get("volume_ul", plating_context.get("volume_ul"))
        measurements[mass_pg] = {
            "status": status,
            "warnings": warnings,
            "observed_colonies": observed.get("observed_colonies"),
            "dilution_factor": dilution_factor,
            "volume_ul": volume_ul,
            "plasmid_mass_pg": mass_pg,
            "calculated_cfu_per_ug": _calculate_cfu_per_ug(
                observed_colonies=observed.get("observed_colonies"),
                dilution_factor=dilution_factor,
                volume_ul=volume_ul,
                plasmid_mass_pg=mass_pg,
            ),
        }

    return measurements


def _is_within_relative_tolerance(expected: float, observed: float, tolerance: float) -> bool:
    if expected == 0:
        return observed == 0
    return abs(observed - expected) / abs(expected) <= tolerance


def _value_matches(value: Any, acceptable_values: Dict[str, Any]) -> bool:
    value_type = acceptable_values["type"]
    if value_type == "exact":
        return value == acceptable_values["value"]
    if value_type == "one_of":
        return value in acceptable_values["values"]
    if value_type == "range":
        return acceptable_values["min"] <= float(value) <= acceptable_values["max"]
    return False


def _score_decision_point(tool_calls: List[Dict[str, Any]], decision_point: Dict[str, Any]) -> float:
    matcher = decision_point["matcher"]
    matched_calls = []
    for call in tool_calls:
        if _normalize_tool_name(call.get("tool_name", "")) != matcher["tool_name"]:
            continue
        observed_values = _observed_values(call)
        filters = matcher.get("filters", {})
        if not _matches_filters(observed_values, filters):
            continue
        matched_calls.append(observed_values)

    if not matched_calls:
        return 0.0

    occurrence = matcher.get("occurrence", "all")
    argument_name = matcher["argument"]
    if occurrence == "first":
        values = [matched_calls[0].get(argument_name)]
    elif occurrence == "last":
        values = [matched_calls[-1].get(argument_name)]
    elif occurrence == "any":
        values = [arguments.get(argument_name) for arguments in matched_calls]
        return 1.0 if any(_value_matches(value, decision_point["acceptable_values"]) for value in values) else 0.0
    else:
        values = [arguments.get(argument_name) for arguments in matched_calls]

    return 1.0 if all(_value_matches(value, decision_point["acceptable_values"]) for value in values) else 0.0


def score_decision_quality(tool_calls: List[Dict[str, Any]], ground_truth: Dict[str, Any]) -> Dict[str, float]:
    scores = {}
    for decision_point in ground_truth["decision_points"]:
        scores[decision_point["id"]] = _score_decision_point(tool_calls, decision_point)
    mean_score = sum(scores.values()) / len(scores) if scores else 0.0
    return {"mean": mean_score, "by_decision": scores}


def score_efficiency(tool_calls: List[Dict[str, Any]], ground_truth: Dict[str, Any]) -> float:
    reference = ground_truth["efficiency_reference"]
    total_calls = len(tool_calls)
    if total_calls <= reference["optimal_tool_calls"]:
        return 1.0
    if total_calls <= reference["max_reasonable_tool_calls"]:
        return 0.5
    return 0.0


def score_troubleshooting(final_answer: str, tool_calls: List[Dict[str, Any]], ground_truth: Dict[str, Any]) -> float:
    failure_markers = []
    for call in tool_calls:
        content = str(call.get("content", ""))
        if "selection_failed" in content:
            failure_markers.append("wrong_selection_pressure")
    if not failure_markers:
        return 1.0

    final_answer_lower = final_answer.lower()
    resolved = 0
    for marker in failure_markers:
        diagnosis = ground_truth["failure_diagnosis_map"][marker]
        acceptable = [diagnosis["canonical_diagnosis"]] + diagnosis.get("acceptable_variants", [])
        if any(candidate.lower() in final_answer_lower for candidate in acceptable):
            resolved += 1
    return float(resolved) / float(len(failure_markers))


def score_task_success(final_answer: str, tool_calls: List[Dict[str, Any]]) -> float:
    reported_efficiencies = _extract_reported_efficiencies(final_answer)
    measurements = _reconstruct_measurements(tool_calls)
    transform_calls = [
        call for call in tool_calls if _normalize_tool_name(call.get("tool_name", "")) == "transform"
    ]
    plate_calls = [
        call for call in tool_calls if _normalize_tool_name(call.get("tool_name", "")) == "plate"
    ]
    count_calls = [
        call for call in tool_calls if _normalize_tool_name(call.get("tool_name", "")) == "count_colonies"
    ]
    if len(transform_calls) < 4 or len(plate_calls) < 4 or len(count_calls) < 4:
        return 0.0
    if set(reported_efficiencies) != set(TARGET_MASSES_PG):
        return 0.0
    if set(measurements) != set(TARGET_MASSES_PG):
        return 0.0

    for mass_pg in TARGET_MASSES_PG:
        measurement = measurements[mass_pg]
        calculated = measurement["calculated_cfu_per_ug"]
        if calculated is None:
            return 0.0
        if measurement["status"] != "plated":
            return 0.0
        if measurement["warnings"]:
            return 0.0
        if not _is_within_relative_tolerance(
            expected=calculated,
            observed=reported_efficiencies[mass_pg],
            tolerance=TASK_SUCCESS_RELATIVE_TOLERANCE,
        ):
            return 0.0

    final_answer_lower = final_answer.lower()
    if not re.search(r"\bconsistent\b", final_answer_lower):
        return 0.0
    return 1.0


def score_transform_trajectory(
    final_answer: str,
    transcript: Iterable[Any],
    ground_truth_path: str,
) -> Dict[str, Any]:
    ground_truth = load_ground_truth(ground_truth_path)
    tool_calls = _extract_tool_calls(transcript)
    decision_quality = score_decision_quality(tool_calls, ground_truth)
    task_success = score_task_success(final_answer, tool_calls)
    troubleshooting = score_troubleshooting(final_answer, tool_calls, ground_truth)
    efficiency = score_efficiency(tool_calls, ground_truth)
    overall = (
        0.4 * task_success
        + 0.3 * decision_quality["mean"]
        + 0.2 * troubleshooting
        + 0.1 * efficiency
    )
    return {
        "overall": overall,
        "task_success": task_success,
        "decision_quality": decision_quality["mean"],
        "troubleshooting": troubleshooting,
        "efficiency": efficiency,
        "decision_scores": decision_quality["by_decision"],
    }


def _extract_reported_growth_doubling_times(final_answer: str) -> Dict[str, float]:
    patterns = {
        "LB + chloramphenicol (1.8 uM)": r"LB\s*\+\s*chloramphenicol\s*\(1\.8\s*[uµμ]M\)\s*:",
        "M9 + glucose": r"M9\s*\+\s*glucose\s*:",
        "LB": r"\bLB\b\s*:",
    }
    reported: Dict[str, float] = {}
    for condition, label_pattern in patterns.items():
        matches = list(
            re.finditer(
                rf"{label_pattern}[\s\S]{{0,120}}?([-+]?\d[\d,]*(?:\.\d+)?)\s*(?:min|minutes)",
                final_answer,
                flags=re.IGNORECASE,
            )
        )
        if not matches:
            continue
        parsed = _parse_scientific_number(matches[-1].group(1))
        if parsed is not None:
            reported[condition] = parsed
    return reported


def _reconstruct_growth_fit_results(tool_calls: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    fits: Dict[str, Dict[str, Any]] = {}
    for call in tool_calls:
        if _normalize_tool_name(call.get("tool_name", "")) != "fit_growth_curve":
            continue
        observed = _observed_values(call)
        condition = observed.get("condition")
        if not condition:
            continue
        fits[condition] = {
            "status": observed.get("status"),
            "estimated_doubling_time_minutes": _coerce_float(
                observed.get("estimated_doubling_time_minutes")
            ),
            "qualifying_points": _coerce_int(observed.get("qualifying_points")),
            "warnings": list(observed.get("warnings") or []),
        }
    return fits


def score_growth_task_success(final_answer: str, tool_calls: List[Dict[str, Any]]) -> float:
    reported = _extract_reported_growth_doubling_times(final_answer)
    fitted = _reconstruct_growth_fit_results(tool_calls)
    inoculate_calls = [
        call for call in tool_calls if _normalize_tool_name(call.get("tool_name", "")) == "inoculate_growth"
    ]
    measure_calls = [
        call for call in tool_calls if _normalize_tool_name(call.get("tool_name", "")) == "measure_od600"
    ]
    fit_calls = [
        call for call in tool_calls if _normalize_tool_name(call.get("tool_name", "")) == "fit_growth_curve"
    ]
    if len(inoculate_calls) < 3 or len(measure_calls) < 9 or len(fit_calls) < 3:
        return 0.0
    if set(reported) != set(GROWTH_CONDITIONS):
        return 0.0
    if set(fitted) != set(GROWTH_CONDITIONS):
        return 0.0

    for condition in GROWTH_CONDITIONS:
        fit_result = fitted[condition]
        estimated = fit_result["estimated_doubling_time_minutes"]
        if fit_result["status"] != "analyzable" or estimated is None:
            return 0.0
        if not _is_within_relative_tolerance(
            expected=estimated,
            observed=reported[condition],
            tolerance=GROWTH_TASK_SUCCESS_RELATIVE_TOLERANCE,
        ):
            return 0.0
    return 1.0


def score_growth_troubleshooting(final_answer: str, tool_calls: List[Dict[str, Any]], ground_truth: Dict[str, Any]) -> float:
    failure_markers = []
    for call in tool_calls:
        if _normalize_tool_name(call.get("tool_name", "")) != "fit_growth_curve":
            continue
        observed = _observed_values(call)
        if observed.get("status") == "insufficient_points":
            failure_markers.append("insufficient_growth_points")
    if not failure_markers:
        return 1.0

    final_answer_lower = final_answer.lower()
    resolved = 0
    for marker in failure_markers:
        diagnosis = ground_truth["failure_diagnosis_map"][marker]
        acceptable = [diagnosis["canonical_diagnosis"]] + diagnosis.get("acceptable_variants", [])
        if any(candidate.lower() in final_answer_lower for candidate in acceptable):
            resolved += 1
        elif "insufficient" in final_answer_lower or "not enough" in final_answer_lower:
            resolved += 1
    return float(resolved) / float(len(failure_markers))


def score_growth_trajectory(
    final_answer: str,
    transcript: Iterable[Any],
    ground_truth_path: str,
) -> Dict[str, Any]:
    ground_truth = load_ground_truth(ground_truth_path)
    tool_calls = _extract_tool_calls(transcript)
    decision_quality = score_decision_quality(tool_calls, ground_truth)
    task_success = score_growth_task_success(final_answer, tool_calls)
    troubleshooting = score_growth_troubleshooting(final_answer, tool_calls, ground_truth)
    efficiency = score_efficiency(tool_calls, ground_truth)
    overall = (
        0.4 * task_success
        + 0.3 * decision_quality["mean"]
        + 0.2 * troubleshooting
        + 0.1 * efficiency
    )
    return {
        "overall": overall,
        "task_success": task_success,
        "decision_quality": decision_quality["mean"],
        "troubleshooting": troubleshooting,
        "efficiency": efficiency,
        "decision_scores": decision_quality["by_decision"],
    }


def _normalize_polymerase_label(value: str) -> str:
    normalized = value.strip().lower()
    if "q5" in normalized:
        return "Q5 High-Fidelity DNA polymerase"
    if "phusion" in normalized:
        return "Phusion High-Fidelity DNA polymerase"
    if re.search(r"\btaq\b", normalized):
        return "Taq DNA polymerase"
    return value.strip()


def _normalize_additive_label(value: str) -> str:
    normalized = value.strip().lower()
    if "dmso" in normalized:
        return "DMSO"
    if "betaine" in normalized:
        return "Betaine"
    if normalized in {"none", "no additive", "not used"}:
        return "none"
    return value.strip()


def _extract_reported_pcr_summary(final_answer: str) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}
    polymerase_match = re.search(r"(?im)^Polymerase:\s*(.+)$", final_answer)
    additive_match = re.search(r"(?im)^Additive:\s*(.+)$", final_answer)
    extension_match = re.search(r"(?im)^Extension:\s*(\d+)\s*seconds?\s*$", final_answer)
    cycles_match = re.search(r"(?im)^Cycles:\s*(\d+)\s*$", final_answer)
    result_match = re.search(r"(?im)^Result:\s*(.+)$", final_answer)

    if polymerase_match:
        summary["polymerase_name"] = _normalize_polymerase_label(polymerase_match.group(1))
    if additive_match:
        summary["additive"] = _normalize_additive_label(additive_match.group(1))
    if extension_match:
        summary["extension_seconds"] = int(extension_match.group(1))
    if cycles_match:
        summary["cycle_count"] = int(cycles_match.group(1))
    if result_match:
        summary["result"] = result_match.group(1).strip()
    return summary


def _reconstruct_pcr_gel_results(tool_calls: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    gels: Dict[str, Dict[str, Any]] = {}
    for call in tool_calls:
        if _normalize_tool_name(call.get("tool_name", "")) != "run_gel":
            continue
        observed = _observed_values(call)
        reaction_id = observed.get("reaction_id")
        if not reaction_id:
            continue
        gels[reaction_id] = {
            "status": observed.get("status"),
            "polymerase_name": _normalize_polymerase_label(str(observed.get("polymerase_name", ""))),
            "additive": _normalize_additive_label(str(observed.get("additive", ""))),
            "extension_seconds": _coerce_int(observed.get("extension_seconds")),
            "cycle_count": _coerce_int(observed.get("cycle_count")),
            "target_size_bp": _coerce_int(observed.get("target_size_bp")),
            "visible_bands_bp": list(observed.get("visible_bands_bp") or []),
            "smear_present": bool(observed.get("smear_present")),
        }
    return gels


def score_pcr_task_success(final_answer: str, tool_calls: List[Dict[str, Any]]) -> float:
    reported = _extract_reported_pcr_summary(final_answer)
    if {
        "polymerase_name",
        "additive",
        "extension_seconds",
        "cycle_count",
        "result",
    } - set(reported):
        return 0.0

    gels = _reconstruct_pcr_gel_results(tool_calls)
    successful = [
        gel
        for gel in gels.values()
        if gel["status"] == "single_clean_target_band"
        and gel["target_size_bp"] == 2000
        and gel["visible_bands_bp"] == [2000]
        and not gel["smear_present"]
    ]
    if not successful:
        return 0.0
    if not PCR_TARGET_BAND_REGEX.search(reported["result"]):
        return 0.0

    for gel in successful:
        if (
            gel["polymerase_name"] == reported["polymerase_name"]
            and gel["additive"] == reported["additive"]
            and gel["extension_seconds"] == reported["extension_seconds"]
            and gel["cycle_count"] == reported["cycle_count"]
        ):
            return 1.0
    return 0.0


def score_pcr_troubleshooting(final_answer: str, tool_calls: List[Dict[str, Any]], ground_truth: Dict[str, Any]) -> float:
    gels = _reconstruct_pcr_gel_results(tool_calls)
    if any(gel["status"] == "single_clean_target_band" for gel in gels.values()):
        return 1.0

    failure_markers = []
    for call in tool_calls:
        if _normalize_tool_name(call.get("tool_name", "")) != "run_pcr":
            continue
        observed = _observed_values(call)
        status = observed.get("status")
        polymerase_name = _normalize_polymerase_label(str(observed.get("polymerase_name", "")))
        if status == "gc_rich_failure":
            failure_markers.append("missing_gc_additive")
        elif status == "truncated_product":
            failure_markers.append("short_extension_time")
        elif status == "low_yield_target_band":
            failure_markers.append("insufficient_cycle_count")
        elif status == "nonspecific_amplification":
            if polymerase_name == "Taq DNA polymerase":
                failure_markers.append("low_fidelity_polymerase")
            else:
                failure_markers.append("overcycled_pcr")

    if not failure_markers:
        return 1.0

    final_answer_lower = final_answer.lower()
    resolved = 0
    for marker in failure_markers:
        diagnosis = ground_truth["failure_diagnosis_map"][marker]
        acceptable = [diagnosis["canonical_diagnosis"]] + diagnosis.get("acceptable_variants", [])
        if any(candidate.lower() in final_answer_lower for candidate in acceptable):
            resolved += 1
    return float(resolved) / float(len(failure_markers))


def score_pcr_trajectory(
    final_answer: str,
    transcript: Iterable[Any],
    ground_truth_path: str,
) -> Dict[str, Any]:
    ground_truth = load_ground_truth(ground_truth_path)
    tool_calls = _extract_tool_calls(transcript)
    decision_quality = score_decision_quality(tool_calls, ground_truth)
    task_success = score_pcr_task_success(final_answer, tool_calls)
    troubleshooting = score_pcr_troubleshooting(final_answer, tool_calls, ground_truth)
    efficiency = score_efficiency(tool_calls, ground_truth)
    overall = (
        0.4 * task_success
        + 0.3 * decision_quality["mean"]
        + 0.2 * troubleshooting
        + 0.1 * efficiency
    )
    return {
        "overall": overall,
        "task_success": task_success,
        "decision_quality": decision_quality["mean"],
        "troubleshooting": troubleshooting,
        "efficiency": efficiency,
        "decision_scores": decision_quality["by_decision"],
    }


def _parse_colony_id_list(value: str) -> List[str]:
    return re.findall(r"\b(?:white|blue)_\d{3}\b", value, flags=re.IGNORECASE)


def _extract_reported_screen_summary(final_answer: str) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}
    screened_match = re.search(r"(?im)^White colonies screened:\s*(.+)$", final_answer)
    confirmed_match = re.search(r"(?im)^Confirmed recombinant colonies:\s*(.+)$", final_answer)
    confidence_match = re.search(r"(?im)^Confidence achieved:\s*([0-9]+(?:\.[0-9]+)?)\s*%\s*$", final_answer)
    interpretation_match = re.search(r"(?im)^Interpretation:\s*(.+)$", final_answer)

    if screened_match:
        screened_value = screened_match.group(1).strip()
        screened_count_match = re.search(r"\d+", screened_value)
        if screened_count_match:
            summary["white_colonies_screened"] = int(screened_count_match.group(0))
        else:
            summary["white_colonies_screened"] = len(_parse_colony_id_list(screened_value))
    if confirmed_match:
        confirmed_value = confirmed_match.group(1).strip()
        if re.fullmatch(r"none", confirmed_value, flags=re.IGNORECASE):
            summary["confirmed_recombinant_ids"] = []
        else:
            summary["confirmed_recombinant_ids"] = sorted(
                colony_id.lower() for colony_id in _parse_colony_id_list(confirmed_value)
            )
    if confidence_match:
        summary["confidence_pct"] = float(confidence_match.group(1))
    if interpretation_match:
        summary["interpretation"] = interpretation_match.group(1).strip()
    return summary


def _reconstruct_screening_results(tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
    latest = {
        "confirmed_recombinant_ids": [],
        "cumulative_screened_white_colony_count": 0,
        "cumulative_confidence_pct": 0.0,
        "screening_strategy": None,
    }
    any_colony_pcr = False
    for call in tool_calls:
        if _normalize_tool_name(call.get("tool_name", "")) != "run_colony_pcr":
            continue
        any_colony_pcr = True
        observed = _observed_values(call)
        latest = {
            "confirmed_recombinant_ids": sorted(
                colony_id.lower()
                for colony_id in observed.get("confirmed_recombinant_ids_cumulative", []) or []
            ),
            "cumulative_screened_white_colony_count": _coerce_int(
                observed.get("cumulative_screened_white_colony_count")
            )
            or 0,
            "cumulative_confidence_pct": _coerce_float(observed.get("cumulative_confidence_pct")) or 0.0,
            "screening_strategy": observed.get("screening_strategy"),
        }
    latest["any_colony_pcr"] = any_colony_pcr
    return latest


def score_screen_task_success(final_answer: str, tool_calls: List[Dict[str, Any]]) -> float:
    reported = _extract_reported_screen_summary(final_answer)
    if {
        "white_colonies_screened",
        "confirmed_recombinant_ids",
        "confidence_pct",
        "interpretation",
    } - set(reported):
        return 0.0

    reconstructed = _reconstruct_screening_results(tool_calls)
    if not reconstructed["any_colony_pcr"]:
        return 0.0
    if not reconstructed["confirmed_recombinant_ids"]:
        return 0.0
    if reported["white_colonies_screened"] != reconstructed["cumulative_screened_white_colony_count"]:
        return 0.0
    if sorted(reported["confirmed_recombinant_ids"]) != reconstructed["confirmed_recombinant_ids"]:
        return 0.0
    if abs(reported["confidence_pct"] - reconstructed["cumulative_confidence_pct"]) > SCREEN_CONFIDENCE_ABSOLUTE_TOLERANCE:
        return 0.0
    if "recombinant" not in reported["interpretation"].lower():
        return 0.0
    return 1.0


def score_screen_troubleshooting(final_answer: str, tool_calls: List[Dict[str, Any]], ground_truth: Dict[str, Any]) -> float:
    reconstructed = _reconstruct_screening_results(tool_calls)
    if reconstructed["confirmed_recombinant_ids"]:
        return 1.0

    failure_markers = []
    for call in tool_calls:
        if _normalize_tool_name(call.get("tool_name", "")) != "run_colony_pcr":
            continue
        observed = _observed_values(call)
        if observed.get("screening_strategy") == "includes_blue":
            failure_markers.append("screened_blue_background")
        confidence_pct = _coerce_float(observed.get("cumulative_confidence_pct")) or 0.0
        if confidence_pct < 95.0:
            failure_markers.append("undersampled_white_colonies")

    if not failure_markers:
        return 1.0

    final_answer_lower = final_answer.lower()
    resolved = 0
    for marker in failure_markers:
        diagnosis = ground_truth["failure_diagnosis_map"][marker]
        acceptable = [diagnosis["canonical_diagnosis"]] + diagnosis.get("acceptable_variants", [])
        if any(candidate.lower() in final_answer_lower for candidate in acceptable):
            resolved += 1
    return float(resolved) / float(len(failure_markers))


def score_screen_trajectory(
    final_answer: str,
    transcript: Iterable[Any],
    ground_truth_path: str,
) -> Dict[str, Any]:
    ground_truth = load_ground_truth(ground_truth_path)
    tool_calls = _extract_tool_calls(transcript)
    decision_quality = score_decision_quality(tool_calls, ground_truth)
    task_success = score_screen_task_success(final_answer, tool_calls)
    troubleshooting = score_screen_troubleshooting(final_answer, tool_calls, ground_truth)
    efficiency = score_efficiency(tool_calls, ground_truth)
    overall = (
        0.4 * task_success
        + 0.3 * decision_quality["mean"]
        + 0.2 * troubleshooting
        + 0.1 * efficiency
    )
    return {
        "overall": overall,
        "task_success": task_success,
        "decision_quality": decision_quality["mean"],
        "troubleshooting": troubleshooting,
        "efficiency": efficiency,
        "decision_scores": decision_quality["by_decision"],
    }


def build_transform_trajectory_scorer():
    from inspect_ai.scorer import Score, Target, mean, scorer

    @scorer(
        metrics={
            "overall": [mean()],
            "task_success": [mean()],
            "decision_quality": [mean()],
            "troubleshooting": [mean()],
            "efficiency": [mean()],
        }
    )
    def _scorer():
        async def score(state, target: Target):
            ground_truth_path = target.text
            final_answer = ""
            if getattr(state, "output", None) is not None:
                final_answer = getattr(state.output, "completion", "") or ""
            values = score_transform_trajectory(
                final_answer=final_answer,
                transcript=getattr(state, "messages", []),
                ground_truth_path=ground_truth_path,
            )
            return Score(
                value={
                    "overall": values["overall"],
                    "task_success": values["task_success"],
                    "decision_quality": values["decision_quality"],
                    "troubleshooting": values["troubleshooting"],
                    "efficiency": values["efficiency"],
                },
                answer=final_answer[:500],
                explanation=json.dumps(values["decision_scores"], indent=2, sort_keys=True),
                metadata=values,
            )

        return score

    return _scorer()


def build_growth_trajectory_scorer():
    from inspect_ai.scorer import Score, Target, mean, scorer

    @scorer(
        metrics={
            "overall": [mean()],
            "task_success": [mean()],
            "decision_quality": [mean()],
            "troubleshooting": [mean()],
            "efficiency": [mean()],
        }
    )
    def _scorer():
        async def score(state, target: Target):
            ground_truth_path = target.text
            final_answer = ""
            if getattr(state, "output", None) is not None:
                final_answer = getattr(state.output, "completion", "") or ""
            values = score_growth_trajectory(
                final_answer=final_answer,
                transcript=getattr(state, "messages", []),
                ground_truth_path=ground_truth_path,
            )
            return Score(
                value={
                    "overall": values["overall"],
                    "task_success": values["task_success"],
                    "decision_quality": values["decision_quality"],
                    "troubleshooting": values["troubleshooting"],
                    "efficiency": values["efficiency"],
                },
                answer=final_answer[:500],
                explanation=json.dumps(values["decision_scores"], indent=2, sort_keys=True),
                metadata=values,
            )

        return score

    return _scorer()


def build_pcr_trajectory_scorer():
    from inspect_ai.scorer import Score, Target, mean, scorer

    @scorer(
        metrics={
            "overall": [mean()],
            "task_success": [mean()],
            "decision_quality": [mean()],
            "troubleshooting": [mean()],
            "efficiency": [mean()],
        }
    )
    def _scorer():
        async def score(state, target: Target):
            ground_truth_path = target.text
            final_answer = ""
            if getattr(state, "output", None) is not None:
                final_answer = getattr(state.output, "completion", "") or ""
            values = score_pcr_trajectory(
                final_answer=final_answer,
                transcript=getattr(state, "messages", []),
                ground_truth_path=ground_truth_path,
            )
            return Score(
                value={
                    "overall": values["overall"],
                    "task_success": values["task_success"],
                    "decision_quality": values["decision_quality"],
                    "troubleshooting": values["troubleshooting"],
                    "efficiency": values["efficiency"],
                },
                answer=final_answer[:500],
                explanation=json.dumps(values["decision_scores"], indent=2, sort_keys=True),
                metadata=values,
            )

        return score

    return _scorer()


def build_screen_trajectory_scorer():
    from inspect_ai.scorer import Score, Target, mean, scorer

    @scorer(
        metrics={
            "overall": [mean()],
            "task_success": [mean()],
            "decision_quality": [mean()],
            "troubleshooting": [mean()],
            "efficiency": [mean()],
        }
    )
    def _scorer():
        async def score(state, target: Target):
            ground_truth_path = target.text
            final_answer = ""
            if getattr(state, "output", None) is not None:
                final_answer = getattr(state.output, "completion", "") or ""
            values = score_screen_trajectory(
                final_answer=final_answer,
                transcript=getattr(state, "messages", []),
                ground_truth_path=ground_truth_path,
            )
            return Score(
                value={
                    "overall": values["overall"],
                    "task_success": values["task_success"],
                    "decision_quality": values["decision_quality"],
                    "troubleshooting": values["troubleshooting"],
                    "efficiency": values["efficiency"],
                },
                answer=final_answer[:500],
                explanation=json.dumps(values["decision_scores"], indent=2, sort_keys=True),
                metadata=values,
            )

        return score

    return _scorer()


CLONE_CONFIDENCE_ABSOLUTE_TOLERANCE = 2.0


def _extract_reported_clone_summary(final_answer: str) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}

    enzymes_match = re.search(r"(?im)^Digest enzymes:\s*(.+)$", final_answer)
    if enzymes_match:
        parts = re.findall(r"[A-Za-z0-9]+", enzymes_match.group(1))
        summary["digest_enzymes"] = sorted({p.lower() for p in parts})

    ligase_match = re.search(r"(?im)^Ligase:\s*(.+)$", final_answer)
    if ligase_match:
        summary["ligase"] = ligase_match.group(1).strip()

    transformants_match = re.search(r"(?im)^Transformants observed:\s*([0-9]+)\b", final_answer)
    if transformants_match:
        summary["transformants_observed"] = int(transformants_match.group(1))

    screened_match = re.search(r"(?im)^White colonies screened:\s*([0-9]+)", final_answer)
    if screened_match:
        summary["white_colonies_screened"] = int(screened_match.group(1))

    confirmed_match = re.search(r"(?im)^Confirmed recombinant colonies:\s*(.+)$", final_answer)
    if confirmed_match:
        confirmed_value = confirmed_match.group(1).strip()
        if re.fullmatch(r"none", confirmed_value, flags=re.IGNORECASE):
            summary["confirmed_recombinant_ids"] = []
        else:
            summary["confirmed_recombinant_ids"] = sorted(
                colony_id.lower() for colony_id in _parse_colony_id_list(confirmed_value)
            )

    confidence_match = re.search(r"(?im)^Confidence achieved:\s*([0-9]+(?:\.[0-9]+)?)\s*%", final_answer)
    if confidence_match:
        summary["confidence_pct"] = float(confidence_match.group(1))

    interpretation_match = re.search(r"(?im)^Interpretation:\s*(.+)$", final_answer)
    if interpretation_match:
        summary["interpretation"] = interpretation_match.group(1).strip()

    return summary


def _reconstruct_clone_results(tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
    digest_count = 0
    ligate_count = 0
    transform_ligation_count = 0
    digest_statuses: List[str] = []
    ligate_statuses: List[str] = []
    any_non_heat_inactivated_digest = False
    any_blue_screening = False
    final_screen = {
        "confirmed_recombinant_ids": [],
        "cumulative_screened_white_colony_count": 0,
        "cumulative_confidence_pct": 0.0,
    }
    transformants_observed = 0

    for call in tool_calls:
        name = _normalize_tool_name(call.get("tool_name", ""))
        observed = _observed_values(call)
        if name == "restriction_digest":
            digest_count += 1
            digest_statuses.append(str(observed.get("status", "")))
            if observed.get("heat_inactivate_after") is False:
                any_non_heat_inactivated_digest = True
        elif name == "ligate":
            ligate_count += 1
            ligate_statuses.append(str(observed.get("status", "")))
        elif name == "transform_ligation":
            transform_ligation_count += 1
        elif name == "run_colony_pcr":
            if observed.get("screening_strategy") == "includes_blue":
                any_blue_screening = True
            final_screen = {
                "confirmed_recombinant_ids": sorted(
                    colony_id.lower()
                    for colony_id in observed.get("confirmed_recombinant_ids_cumulative", []) or []
                ),
                "cumulative_screened_white_colony_count": _coerce_int(
                    observed.get("cumulative_screened_white_colony_count")
                )
                or 0,
                "cumulative_confidence_pct": _coerce_float(
                    observed.get("cumulative_confidence_pct")
                )
                or 0.0,
            }
        elif name == "count_colonies":
            observed_value = _coerce_int(observed.get("observed_colonies"))
            if observed_value is not None and observed_value > transformants_observed:
                transformants_observed = observed_value

    return {
        "digest_count": digest_count,
        "ligate_count": ligate_count,
        "transform_ligation_count": transform_ligation_count,
        "digest_statuses": digest_statuses,
        "ligate_statuses": ligate_statuses,
        "any_non_heat_inactivated_digest": any_non_heat_inactivated_digest,
        "any_blue_screening": any_blue_screening,
        "final_screen": final_screen,
        "transformants_observed": transformants_observed,
    }


def score_clone_task_success(final_answer: str, tool_calls: List[Dict[str, Any]]) -> float:
    reported = _extract_reported_clone_summary(final_answer)
    required = {
        "digest_enzymes",
        "ligase",
        "transformants_observed",
        "white_colonies_screened",
        "confirmed_recombinant_ids",
        "confidence_pct",
        "interpretation",
    }
    if required - set(reported):
        return 0.0
    if sorted(reported["digest_enzymes"]) != ["bamhi", "ecori"]:
        return 0.0
    if "t4" not in reported["ligase"].lower():
        return 0.0

    reconstructed = _reconstruct_clone_results(tool_calls)
    if reconstructed["digest_count"] < 2:
        return 0.0
    if reconstructed["ligate_count"] < 1:
        return 0.0
    if reconstructed["transform_ligation_count"] < 1:
        return 0.0
    if not reconstructed["final_screen"]["confirmed_recombinant_ids"]:
        return 0.0
    if (
        reported["white_colonies_screened"]
        != reconstructed["final_screen"]["cumulative_screened_white_colony_count"]
    ):
        return 0.0
    if (
        sorted(reported["confirmed_recombinant_ids"])
        != reconstructed["final_screen"]["confirmed_recombinant_ids"]
    ):
        return 0.0
    if (
        abs(
            reported["confidence_pct"]
            - reconstructed["final_screen"]["cumulative_confidence_pct"]
        )
        > CLONE_CONFIDENCE_ABSOLUTE_TOLERANCE
    ):
        return 0.0
    if "recombinant" not in reported["interpretation"].lower():
        return 0.0
    return 1.0


def score_clone_troubleshooting(
    final_answer: str, tool_calls: List[Dict[str, Any]], ground_truth: Dict[str, Any]
) -> float:
    reconstructed = _reconstruct_clone_results(tool_calls)
    failure_markers: List[str] = []

    for status in reconstructed["digest_statuses"]:
        if status in {"wrong_buffer", "incomplete_digest", "wrong_enzyme_pair"}:
            failure_markers.append("wrong_digest_buffer")
            break
    for status in reconstructed["ligate_statuses"]:
        if status == "wrong_ligase":
            failure_markers.append("wrong_ligase")
        if status == "wrong_ratio":
            failure_markers.append("extreme_molar_ratio")
    if reconstructed["any_non_heat_inactivated_digest"]:
        failure_markers.append("no_heat_inactivation")
    if reconstructed["any_blue_screening"]:
        failure_markers.append("screened_blue_background")

    if not failure_markers:
        return 1.0

    final_answer_lower = final_answer.lower()
    resolved = 0
    for marker in failure_markers:
        diagnosis = ground_truth["failure_diagnosis_map"].get(marker)
        if diagnosis is None:
            continue
        acceptable = [diagnosis["canonical_diagnosis"]] + diagnosis.get("acceptable_variants", [])
        if any(candidate.lower() in final_answer_lower for candidate in acceptable):
            resolved += 1
    return float(resolved) / float(len(failure_markers))


def score_clone_trajectory(
    final_answer: str,
    transcript: Iterable[Any],
    ground_truth_path: str,
) -> Dict[str, Any]:
    ground_truth = load_ground_truth(ground_truth_path)
    tool_calls = _extract_tool_calls(transcript)
    decision_quality = score_decision_quality(tool_calls, ground_truth)
    task_success = score_clone_task_success(final_answer, tool_calls)
    troubleshooting = score_clone_troubleshooting(final_answer, tool_calls, ground_truth)
    efficiency = score_efficiency(tool_calls, ground_truth)
    overall = (
        0.4 * task_success
        + 0.3 * decision_quality["mean"]
        + 0.2 * troubleshooting
        + 0.1 * efficiency
    )
    return {
        "overall": overall,
        "task_success": task_success,
        "decision_quality": decision_quality["mean"],
        "troubleshooting": troubleshooting,
        "efficiency": efficiency,
        "decision_scores": decision_quality["by_decision"],
    }


def build_clone_trajectory_scorer():
    from inspect_ai.scorer import Score, Target, mean, scorer

    @scorer(
        metrics={
            "overall": [mean()],
            "task_success": [mean()],
            "decision_quality": [mean()],
            "troubleshooting": [mean()],
            "efficiency": [mean()],
        }
    )
    def _scorer():
        async def score(state, target: Target):
            ground_truth_path = target.text
            final_answer = ""
            if getattr(state, "output", None) is not None:
                final_answer = getattr(state.output, "completion", "") or ""
            values = score_clone_trajectory(
                final_answer=final_answer,
                transcript=getattr(state, "messages", []),
                ground_truth_path=ground_truth_path,
            )
            return Score(
                value={
                    "overall": values["overall"],
                    "task_success": values["task_success"],
                    "decision_quality": values["decision_quality"],
                    "troubleshooting": values["troubleshooting"],
                    "efficiency": values["efficiency"],
                },
                answer=final_answer[:500],
                explanation=json.dumps(values["decision_scores"], indent=2, sort_keys=True),
                metadata=values,
            )

        return score

    return _scorer()


# ---------------------------------------------------------------------------
# Golden Gate-01 scorer (Phase 1a)
# ---------------------------------------------------------------------------


def _extract_reported_golden_gate_summary(final_answer: str) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}
    enzyme_match = re.search(r"(?im)^Type IIS enzyme:\s*(.+)$", final_answer)
    if enzyme_match:
        summary["enzyme"] = enzyme_match.group(1).strip().lower()
    ligase_match = re.search(r"(?im)^Ligase:\s*(.+)$", final_answer)
    if ligase_match:
        summary["ligase"] = ligase_match.group(1).strip()
    digest_match = re.search(r"(?im)^Digest temperature:\s*([0-9]+(?:\.[0-9]+)?)\s*C", final_answer)
    if digest_match:
        summary["digest_temperature_c"] = float(digest_match.group(1))
    ligate_match = re.search(r"(?im)^Ligate temperature:\s*([0-9]+(?:\.[0-9]+)?)\s*C", final_answer)
    if ligate_match:
        summary["ligate_temperature_c"] = float(ligate_match.group(1))
    cycles_match = re.search(r"(?im)^Cycle count:\s*([0-9]+)", final_answer)
    if cycles_match:
        summary["cycle_count"] = int(cycles_match.group(1))
    fragment_match = re.search(r"(?im)^Fragment count:\s*([0-9]+)", final_answer)
    if fragment_match:
        summary["fragment_count"] = int(fragment_match.group(1))
    transformants_match = re.search(r"(?im)^Transformants observed:\s*([0-9]+)\b", final_answer)
    if transformants_match:
        summary["transformants_observed"] = int(transformants_match.group(1))
    interpretation_match = re.search(r"(?im)^Interpretation:\s*(.+)$", final_answer)
    if interpretation_match:
        summary["interpretation"] = interpretation_match.group(1).strip()
    return summary


def _reconstruct_golden_gate_results(tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
    assembly_count = 0
    transform_assembly_count = 0
    assembly_statuses: List[str] = []
    latest_efficiency = 0.0
    transformants_observed = 0
    last_assembly = None

    for call in tool_calls:
        name = _normalize_tool_name(call.get("tool_name", ""))
        observed = _observed_values(call)
        if name == "golden_gate_assembly":
            assembly_count += 1
            assembly_statuses.append(str(observed.get("status", "")))
            latest_efficiency = _coerce_float(observed.get("effective_assembly_efficiency")) or 0.0
            last_assembly = observed
        elif name == "transform_assembly":
            transform_assembly_count += 1
        elif name == "count_colonies":
            value = _coerce_int(observed.get("observed_colonies"))
            if value is not None and value > transformants_observed:
                transformants_observed = value

    return {
        "assembly_count": assembly_count,
        "transform_assembly_count": transform_assembly_count,
        "assembly_statuses": assembly_statuses,
        "last_assembly": last_assembly,
        "latest_efficiency": latest_efficiency,
        "transformants_observed": transformants_observed,
    }


def score_golden_gate_task_success(final_answer: str, tool_calls: List[Dict[str, Any]]) -> float:
    reported = _extract_reported_golden_gate_summary(final_answer)
    required = {
        "enzyme",
        "ligase",
        "digest_temperature_c",
        "ligate_temperature_c",
        "cycle_count",
        "fragment_count",
        "transformants_observed",
        "interpretation",
    }
    if required - set(reported):
        return 0.0
    enzyme_token = reported["enzyme"].replace(" ", "").replace("-hfv2", "").replace("-v2", "")
    if enzyme_token not in {"bsai", "bsmbi"}:
        return 0.0
    if "t4" not in reported["ligase"].lower():
        return 0.0
    if reported["fragment_count"] != 4:
        return 0.0
    reconstructed = _reconstruct_golden_gate_results(tool_calls)
    if reconstructed["assembly_count"] < 1 or reconstructed["transform_assembly_count"] < 1:
        return 0.0
    last = reconstructed["last_assembly"] or {}
    if str(last.get("status")) != "assembled":
        return 0.0
    if reported["transformants_observed"] != reconstructed["transformants_observed"]:
        return 0.0
    if "assembl" not in reported["interpretation"].lower():
        return 0.0
    return 1.0


def score_golden_gate_troubleshooting(
    final_answer: str, tool_calls: List[Dict[str, Any]], ground_truth: Dict[str, Any]
) -> float:
    reconstructed = _reconstruct_golden_gate_results(tool_calls)
    failure_markers: List[str] = []
    for status in reconstructed["assembly_statuses"]:
        if status == "wrong_enzyme":
            failure_markers.append("wrong_enzyme")
        elif status == "wrong_ligase":
            failure_markers.append("wrong_ligase")
        elif status == "wrong_fragment_count":
            failure_markers.append("wrong_fragment_count")
    if not failure_markers:
        return 1.0
    final_answer_lower = final_answer.lower()
    resolved = 0
    for marker in failure_markers:
        diagnosis = ground_truth["failure_diagnosis_map"].get(marker)
        if diagnosis is None:
            continue
        acceptable = [diagnosis["canonical_diagnosis"]] + diagnosis.get("acceptable_variants", [])
        if any(candidate.lower() in final_answer_lower for candidate in acceptable):
            resolved += 1
    return float(resolved) / float(len(failure_markers))


def score_golden_gate_trajectory(
    final_answer: str,
    transcript: Iterable[Any],
    ground_truth_path: str,
) -> Dict[str, Any]:
    ground_truth = load_ground_truth(ground_truth_path)
    tool_calls = _extract_tool_calls(transcript)
    decision_quality = score_decision_quality(tool_calls, ground_truth)
    task_success = score_golden_gate_task_success(final_answer, tool_calls)
    troubleshooting = score_golden_gate_troubleshooting(final_answer, tool_calls, ground_truth)
    efficiency = score_efficiency(tool_calls, ground_truth)
    overall = (
        0.4 * task_success
        + 0.3 * decision_quality["mean"]
        + 0.2 * troubleshooting
        + 0.1 * efficiency
    )
    return {
        "overall": overall,
        "task_success": task_success,
        "decision_quality": decision_quality["mean"],
        "troubleshooting": troubleshooting,
        "efficiency": efficiency,
        "decision_scores": decision_quality["by_decision"],
    }


def build_golden_gate_trajectory_scorer():
    from inspect_ai.scorer import Score, Target, mean, scorer

    @scorer(
        metrics={
            "overall": [mean()],
            "task_success": [mean()],
            "decision_quality": [mean()],
            "troubleshooting": [mean()],
            "efficiency": [mean()],
        }
    )
    def _scorer():
        async def score(state, target: Target):
            ground_truth_path = target.text
            final_answer = ""
            if getattr(state, "output", None) is not None:
                final_answer = getattr(state.output, "completion", "") or ""
            values = score_golden_gate_trajectory(
                final_answer=final_answer,
                transcript=getattr(state, "messages", []),
                ground_truth_path=ground_truth_path,
            )
            return Score(
                value={
                    "overall": values["overall"],
                    "task_success": values["task_success"],
                    "decision_quality": values["decision_quality"],
                    "troubleshooting": values["troubleshooting"],
                    "efficiency": values["efficiency"],
                },
                answer=final_answer[:500],
                explanation=json.dumps(values["decision_scores"], indent=2, sort_keys=True),
                metadata=values,
            )

        return score

    return _scorer()


# ---------------------------------------------------------------------------
# Gibson-01 scorer (Phase 1b)
# ---------------------------------------------------------------------------


def _extract_reported_gibson_summary(final_answer: str) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}
    master_match = re.search(r"(?im)^Master mix:\s*(.+)$", final_answer)
    if master_match:
        summary["master_mix"] = master_match.group(1).strip().lower()
    temp_match = re.search(r"(?im)^Temperature:\s*([0-9]+(?:\.[0-9]+)?)\s*C", final_answer)
    if temp_match:
        summary["temperature_c"] = float(temp_match.group(1))
    dur_match = re.search(r"(?im)^Duration:\s*([0-9]+)\s*min", final_answer)
    if dur_match:
        summary["duration_minutes"] = int(dur_match.group(1))
    frag_match = re.search(r"(?im)^Fragment count:\s*([0-9]+)", final_answer)
    if frag_match:
        summary["fragment_count"] = int(frag_match.group(1))
    overlap_match = re.search(r"(?im)^Overlap length:\s*([0-9]+)\s*bp", final_answer)
    if overlap_match:
        summary["overlap_length_bp"] = int(overlap_match.group(1))
    transformants_match = re.search(r"(?im)^Transformants observed:\s*([0-9]+)\b", final_answer)
    if transformants_match:
        summary["transformants_observed"] = int(transformants_match.group(1))
    interp_match = re.search(r"(?im)^Interpretation:\s*(.+)$", final_answer)
    if interp_match:
        summary["interpretation"] = interp_match.group(1).strip()
    return summary


def _reconstruct_gibson_results(tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
    gibson_count = 0
    transform_gibson_count = 0
    statuses: List[str] = []
    last_gibson = None
    transformants_observed = 0
    for call in tool_calls:
        name = _normalize_tool_name(call.get("tool_name", ""))
        observed = _observed_values(call)
        if name == "gibson_assembly":
            gibson_count += 1
            statuses.append(str(observed.get("status", "")))
            last_gibson = observed
        elif name == "transform_gibson":
            transform_gibson_count += 1
        elif name == "count_colonies":
            value = _coerce_int(observed.get("observed_colonies"))
            if value is not None and value > transformants_observed:
                transformants_observed = value
    return {
        "gibson_count": gibson_count,
        "transform_gibson_count": transform_gibson_count,
        "statuses": statuses,
        "last_gibson": last_gibson,
        "transformants_observed": transformants_observed,
    }


def score_gibson_task_success(final_answer: str, tool_calls: List[Dict[str, Any]]) -> float:
    reported = _extract_reported_gibson_summary(final_answer)
    required = {
        "master_mix",
        "temperature_c",
        "duration_minutes",
        "fragment_count",
        "overlap_length_bp",
        "transformants_observed",
        "interpretation",
    }
    if required - set(reported):
        return 0.0
    if reported["fragment_count"] != 2:
        return 0.0
    reconstructed = _reconstruct_gibson_results(tool_calls)
    if reconstructed["gibson_count"] < 1 or reconstructed["transform_gibson_count"] < 1:
        return 0.0
    last = reconstructed["last_gibson"] or {}
    if str(last.get("status")) != "assembled":
        return 0.0
    if reported["transformants_observed"] != reconstructed["transformants_observed"]:
        return 0.0
    if "assembl" not in reported["interpretation"].lower():
        return 0.0
    return 1.0


def score_gibson_troubleshooting(
    final_answer: str, tool_calls: List[Dict[str, Any]], ground_truth: Dict[str, Any]
) -> float:
    reconstructed = _reconstruct_gibson_results(tool_calls)
    failure_markers: List[str] = []
    for status in reconstructed["statuses"]:
        if status == "wrong_master_mix":
            failure_markers.append("wrong_master_mix")
    if not failure_markers:
        return 1.0
    final_answer_lower = final_answer.lower()
    resolved = 0
    for marker in failure_markers:
        diagnosis = ground_truth["failure_diagnosis_map"].get(marker)
        if diagnosis is None:
            continue
        acceptable = [diagnosis["canonical_diagnosis"]] + diagnosis.get("acceptable_variants", [])
        if any(candidate.lower() in final_answer_lower for candidate in acceptable):
            resolved += 1
    return float(resolved) / float(len(failure_markers))


def score_gibson_trajectory(
    final_answer: str,
    transcript: Iterable[Any],
    ground_truth_path: str,
) -> Dict[str, Any]:
    ground_truth = load_ground_truth(ground_truth_path)
    tool_calls = _extract_tool_calls(transcript)
    decision_quality = score_decision_quality(tool_calls, ground_truth)
    task_success = score_gibson_task_success(final_answer, tool_calls)
    troubleshooting = score_gibson_troubleshooting(final_answer, tool_calls, ground_truth)
    efficiency = score_efficiency(tool_calls, ground_truth)
    overall = (
        0.4 * task_success
        + 0.3 * decision_quality["mean"]
        + 0.2 * troubleshooting
        + 0.1 * efficiency
    )
    return {
        "overall": overall,
        "task_success": task_success,
        "decision_quality": decision_quality["mean"],
        "troubleshooting": troubleshooting,
        "efficiency": efficiency,
        "decision_scores": decision_quality["by_decision"],
    }


def build_gibson_trajectory_scorer():
    from inspect_ai.scorer import Score, Target, mean, scorer

    @scorer(
        metrics={
            "overall": [mean()],
            "task_success": [mean()],
            "decision_quality": [mean()],
            "troubleshooting": [mean()],
            "efficiency": [mean()],
        }
    )
    def _scorer():
        async def score(state, target: Target):
            ground_truth_path = target.text
            final_answer = ""
            if getattr(state, "output", None) is not None:
                final_answer = getattr(state.output, "completion", "") or ""
            values = score_gibson_trajectory(
                final_answer=final_answer,
                transcript=getattr(state, "messages", []),
                ground_truth_path=ground_truth_path,
            )
            return Score(
                value={
                    "overall": values["overall"],
                    "task_success": values["task_success"],
                    "decision_quality": values["decision_quality"],
                    "troubleshooting": values["troubleshooting"],
                    "efficiency": values["efficiency"],
                },
                answer=final_answer[:500],
                explanation=json.dumps(values["decision_scores"], indent=2, sort_keys=True),
                metadata=values,
            )

        return score

    return _scorer()


# ---------------------------------------------------------------------------
# Miniprep-01 scorer (Phase 1c)
# ---------------------------------------------------------------------------


def _extract_reported_miniprep_summary(final_answer: str) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}
    vol = re.search(r"(?im)^Culture volume:\s*([0-9]+(?:\.[0-9]+)?)\s*mL", final_answer)
    if vol:
        summary["culture_volume_ml"] = float(vol.group(1))
    buf = re.search(r"(?im)^Lysis buffer sequence:\s*(.+)$", final_answer)
    if buf:
        summary["lysis_buffer_sequence"] = buf.group(1).strip().lower()
    dur = re.search(r"(?im)^Lysis duration:\s*([0-9]+)\s*min", final_answer)
    if dur:
        summary["lysis_duration_min"] = int(dur.group(1))
    method = re.search(r"(?im)^Purification method:\s*(.+)$", final_answer)
    if method:
        summary["purification_method"] = method.group(1).strip().lower()
    elu = re.search(r"(?im)^Elution volume:\s*([0-9]+(?:\.[0-9]+)?)\s*uL", final_answer)
    if elu:
        summary["elution_volume_ul"] = float(elu.group(1))
    conc = re.search(r"(?im)^Plasmid concentration:\s*([0-9]+(?:\.[0-9]+)?)\s*ng/uL", final_answer)
    if conc:
        summary["final_concentration_ng_ul"] = float(conc.group(1))
    ratio = re.search(r"(?im)^A260/A280:\s*([0-9]+(?:\.[0-9]+)?)", final_answer)
    if ratio:
        summary["a260_a280_ratio"] = float(ratio.group(1))
    yld = re.search(r"(?im)^Total yield:\s*([0-9]+(?:\.[0-9]+)?)\s*ug", final_answer)
    if yld:
        summary["total_yield_ug"] = float(yld.group(1))
    interp = re.search(r"(?im)^Interpretation:\s*(.+)$", final_answer)
    if interp:
        summary["interpretation"] = interp.group(1).strip()
    return summary


def _reconstruct_miniprep_results(tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
    last = None
    call_count = 0
    statuses: List[str] = []
    for call in tool_calls:
        if _normalize_tool_name(call.get("tool_name", "")) != "perform_miniprep":
            continue
        call_count += 1
        observed = _observed_values(call)
        statuses.append(str(observed.get("status", "")))
        last = observed
    return {"last": last, "call_count": call_count, "statuses": statuses}


MINIPREP_CONCENTRATION_TOLERANCE = 2.0  # ng/uL
MINIPREP_RATIO_TOLERANCE = 0.05


def score_miniprep_task_success(final_answer: str, tool_calls: List[Dict[str, Any]]) -> float:
    reported = _extract_reported_miniprep_summary(final_answer)
    required = {
        "culture_volume_ml",
        "lysis_buffer_sequence",
        "lysis_duration_min",
        "purification_method",
        "elution_volume_ul",
        "final_concentration_ng_ul",
        "a260_a280_ratio",
        "total_yield_ug",
        "interpretation",
    }
    if required - set(reported):
        return 0.0
    reconstructed = _reconstruct_miniprep_results(tool_calls)
    if reconstructed["call_count"] != 1 or reconstructed["last"] is None:
        return 0.0
    last = reconstructed["last"]
    if str(last.get("status")) != "prepared":
        return 0.0
    if (
        abs(float(last.get("final_concentration_ng_ul", 0.0)) - reported["final_concentration_ng_ul"])
        > MINIPREP_CONCENTRATION_TOLERANCE
    ):
        return 0.0
    if abs(float(last.get("a260_a280_ratio", 0.0)) - reported["a260_a280_ratio"]) > MINIPREP_RATIO_TOLERANCE:
        return 0.0
    if "pur" not in reported["interpretation"].lower():
        return 0.0
    return 1.0


def score_miniprep_troubleshooting(
    final_answer: str, tool_calls: List[Dict[str, Any]], ground_truth: Dict[str, Any]
) -> float:
    reconstructed = _reconstruct_miniprep_results(tool_calls)
    failure_markers: List[str] = []
    for status in reconstructed["statuses"]:
        if status in {
            "wrong_buffer_sequence",
            "overlysis_genomic_contamination",
            "wrong_purification_method",
        }:
            failure_markers.append(status)
    if not failure_markers:
        return 1.0
    final_answer_lower = final_answer.lower()
    resolved = 0
    for marker in failure_markers:
        diagnosis = ground_truth["failure_diagnosis_map"].get(marker)
        if diagnosis is None:
            continue
        acceptable = [diagnosis["canonical_diagnosis"]] + diagnosis.get("acceptable_variants", [])
        if any(candidate.lower() in final_answer_lower for candidate in acceptable):
            resolved += 1
    return float(resolved) / float(len(failure_markers))


def score_miniprep_trajectory(
    final_answer: str,
    transcript: Iterable[Any],
    ground_truth_path: str,
) -> Dict[str, Any]:
    ground_truth = load_ground_truth(ground_truth_path)
    tool_calls = _extract_tool_calls(transcript)
    decision_quality = score_decision_quality(tool_calls, ground_truth)
    task_success = score_miniprep_task_success(final_answer, tool_calls)
    troubleshooting = score_miniprep_troubleshooting(final_answer, tool_calls, ground_truth)
    efficiency = score_efficiency(tool_calls, ground_truth)
    overall = (
        0.4 * task_success
        + 0.3 * decision_quality["mean"]
        + 0.2 * troubleshooting
        + 0.1 * efficiency
    )
    return {
        "overall": overall,
        "task_success": task_success,
        "decision_quality": decision_quality["mean"],
        "troubleshooting": troubleshooting,
        "efficiency": efficiency,
        "decision_scores": decision_quality["by_decision"],
    }


def build_miniprep_trajectory_scorer():
    from inspect_ai.scorer import Score, Target, mean, scorer

    @scorer(
        metrics={
            "overall": [mean()],
            "task_success": [mean()],
            "decision_quality": [mean()],
            "troubleshooting": [mean()],
            "efficiency": [mean()],
        }
    )
    def _scorer():
        async def score(state, target: Target):
            ground_truth_path = target.text
            final_answer = ""
            if getattr(state, "output", None) is not None:
                final_answer = getattr(state.output, "completion", "") or ""
            values = score_miniprep_trajectory(
                final_answer=final_answer,
                transcript=getattr(state, "messages", []),
                ground_truth_path=ground_truth_path,
            )
            return Score(
                value={
                    "overall": values["overall"],
                    "task_success": values["task_success"],
                    "decision_quality": values["decision_quality"],
                    "troubleshooting": values["troubleshooting"],
                    "efficiency": values["efficiency"],
                },
                answer=final_answer[:500],
                explanation=json.dumps(values["decision_scores"], indent=2, sort_keys=True),
                metadata=values,
            )

        return score

    return _scorer()


# ---------------------------------------------------------------------------
# Express-01 scorer (Phase 2a)
# ---------------------------------------------------------------------------

EXPRESS_YIELD_TOLERANCE_MG_PER_L = 3.0


def _extract_reported_express_summary(final_answer: str) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}
    host = re.search(r"(?im)^Host strain:\s*(.+)$", final_answer)
    if host:
        summary["host_strain"] = host.group(1).strip().lower()
    iptg = re.search(r"(?im)^IPTG concentration:\s*([0-9]+(?:\.[0-9]+)?)\s*mM", final_answer)
    if iptg:
        summary["iptg_concentration_mm"] = float(iptg.group(1))
    od = re.search(r"(?im)^Induction OD600:\s*([0-9]+(?:\.[0-9]+)?)", final_answer)
    if od:
        summary["induction_od600"] = float(od.group(1))
    temp = re.search(r"(?im)^Induction temperature:\s*([0-9]+(?:\.[0-9]+)?)\s*C", final_answer)
    if temp:
        summary["induction_temperature_c"] = float(temp.group(1))
    dur = re.search(r"(?im)^Induction duration:\s*([0-9]+(?:\.[0-9]+)?)\s*h", final_answer)
    if dur:
        summary["induction_hours"] = float(dur.group(1))
    ph = re.search(r"(?im)^Lysis buffer pH:\s*([0-9]+(?:\.[0-9]+)?)", final_answer)
    if ph:
        summary["lysis_buffer_ph"] = float(ph.group(1))
    yld = re.search(r"(?im)^Expected soluble yield:\s*([0-9]+(?:\.[0-9]+)?)\s*mg/L", final_answer)
    if yld:
        summary["soluble_yield_mg_per_l"] = float(yld.group(1))
    interp = re.search(r"(?im)^Interpretation:\s*(.+)$", final_answer)
    if interp:
        summary["interpretation"] = interp.group(1).strip()
    return summary


def _reconstruct_express_results(tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
    last = None
    call_count = 0
    statuses: List[str] = []
    for call in tool_calls:
        if _normalize_tool_name(call.get("tool_name", "")) != "run_protein_expression":
            continue
        call_count += 1
        observed = _observed_values(call)
        statuses.append(str(observed.get("status", "")))
        last = observed
    return {"last": last, "call_count": call_count, "statuses": statuses}


def score_express_task_success(final_answer: str, tool_calls: List[Dict[str, Any]]) -> float:
    reported = _extract_reported_express_summary(final_answer)
    required = {
        "host_strain",
        "iptg_concentration_mm",
        "induction_od600",
        "induction_temperature_c",
        "induction_hours",
        "lysis_buffer_ph",
        "soluble_yield_mg_per_l",
        "interpretation",
    }
    if required - set(reported):
        return 0.0
    reconstructed = _reconstruct_express_results(tool_calls)
    if reconstructed["call_count"] != 1 or reconstructed["last"] is None:
        return 0.0
    last = reconstructed["last"]
    if str(last.get("status")) != "induced":
        return 0.0
    if (
        abs(float(last.get("soluble_yield_mg_per_l", 0.0)) - reported["soluble_yield_mg_per_l"])
        > EXPRESS_YIELD_TOLERANCE_MG_PER_L
    ):
        return 0.0
    if "express" not in reported["interpretation"].lower():
        return 0.0
    return 1.0


def score_express_troubleshooting(
    final_answer: str, tool_calls: List[Dict[str, Any]], ground_truth: Dict[str, Any]
) -> float:
    reconstructed = _reconstruct_express_results(tool_calls)
    failure_markers: List[str] = []
    for status in reconstructed["statuses"]:
        if status in {"wrong_host_strain", "wrong_induction_temperature", "wrong_lysis_ph"}:
            failure_markers.append(status)
    if not failure_markers:
        return 1.0
    final_answer_lower = final_answer.lower()
    resolved = 0
    for marker in failure_markers:
        diagnosis = ground_truth["failure_diagnosis_map"].get(marker)
        if diagnosis is None:
            continue
        acceptable = [diagnosis["canonical_diagnosis"]] + diagnosis.get("acceptable_variants", [])
        if any(candidate.lower() in final_answer_lower for candidate in acceptable):
            resolved += 1
    return float(resolved) / float(len(failure_markers))


def score_express_trajectory(
    final_answer: str,
    transcript: Iterable[Any],
    ground_truth_path: str,
) -> Dict[str, Any]:
    ground_truth = load_ground_truth(ground_truth_path)
    tool_calls = _extract_tool_calls(transcript)
    decision_quality = score_decision_quality(tool_calls, ground_truth)
    task_success = score_express_task_success(final_answer, tool_calls)
    troubleshooting = score_express_troubleshooting(final_answer, tool_calls, ground_truth)
    efficiency = score_efficiency(tool_calls, ground_truth)
    overall = (
        0.4 * task_success
        + 0.3 * decision_quality["mean"]
        + 0.2 * troubleshooting
        + 0.1 * efficiency
    )
    return {
        "overall": overall,
        "task_success": task_success,
        "decision_quality": decision_quality["mean"],
        "troubleshooting": troubleshooting,
        "efficiency": efficiency,
        "decision_scores": decision_quality["by_decision"],
    }


def build_express_trajectory_scorer():
    from inspect_ai.scorer import Score, Target, mean, scorer

    @scorer(
        metrics={
            "overall": [mean()],
            "task_success": [mean()],
            "decision_quality": [mean()],
            "troubleshooting": [mean()],
            "efficiency": [mean()],
        }
    )
    def _scorer():
        async def score(state, target: Target):
            ground_truth_path = target.text
            final_answer = ""
            if getattr(state, "output", None) is not None:
                final_answer = getattr(state.output, "completion", "") or ""
            values = score_express_trajectory(
                final_answer=final_answer,
                transcript=getattr(state, "messages", []),
                ground_truth_path=ground_truth_path,
            )
            return Score(
                value={
                    "overall": values["overall"],
                    "task_success": values["task_success"],
                    "decision_quality": values["decision_quality"],
                    "troubleshooting": values["troubleshooting"],
                    "efficiency": values["efficiency"],
                },
                answer=final_answer[:500],
                explanation=json.dumps(values["decision_scores"], indent=2, sort_keys=True),
                metadata=values,
            )

        return score

    return _scorer()
