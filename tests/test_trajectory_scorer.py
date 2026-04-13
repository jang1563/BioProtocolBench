"""Trajectory-scorer tests for Transform-01."""

from __future__ import annotations

import json
from pathlib import Path

from src.trajectory_scorer import (
    score_growth_task_success,
    score_growth_trajectory,
    score_pcr_task_success,
    score_pcr_trajectory,
    score_screen_task_success,
    score_screen_trajectory,
    score_task_success,
    score_transform_trajectory,
)


TRANSFORM_GROUND_TRUTH_PATH = Path(__file__).resolve().parents[1] / "task_data" / "transform_01" / "ground_truth.json"
GROWTH_GROUND_TRUTH_PATH = Path(__file__).resolve().parents[1] / "task_data" / "growth_01" / "ground_truth.json"
PCR_GROUND_TRUTH_PATH = Path(__file__).resolve().parents[1] / "task_data" / "pcr_01" / "ground_truth.json"
SCREEN_GROUND_TRUTH_PATH = Path(__file__).resolve().parents[1] / "task_data" / "screen_01" / "ground_truth.json"
TARGET_MASSES = [10, 100, 1000, 10000]


def _good_transcript():
    transcript = [
        {
            "type": "tool_call",
            "tool_name": "prepare_media",
            "arguments": {
                "medium": "LB agar",
                "antibiotic": "ampicillin",
                "antibiotic_concentration_ug_ml": 100,
                "plate_count": 4,
            },
        }
    ]
    for idx, mass in enumerate(TARGET_MASSES, start=1):
        culture_id = "culture_{:03d}".format(idx)
        plate_id = "plate_{:03d}".format(idx)
        plating_id = "plating_{:03d}".format(idx)
        dilution_factor = mass
        transcript.extend(
            [
                {
                    "type": "tool_call",
                    "tool_name": "transform",
                    "arguments": {
                        "culture_id": culture_id,
                        "plasmid_mass_pg": mass,
                        "heat_shock_seconds": 30,
                        "recovery_minutes": 60,
                        "outgrowth_media": "SOC",
                        "shaking": True,
                    },
                },
                {
                    "type": "tool_call",
                    "tool_name": "plate",
                    "arguments": {
                        "culture_id": culture_id,
                        "plate_id": plate_id,
                        "plating_id": plating_id,
                        "dilution_factor": dilution_factor,
                        "volume_ul": 100,
                        "status": "plated",
                        "warnings": [],
                    },
                },
                {
                    "type": "tool_call",
                    "tool_name": "count_colonies",
                    "arguments": {
                        "plating_id": plating_id,
                        "observed_colonies": 100,
                        "dilution_factor": dilution_factor,
                        "volume_ul": 100,
                        "status": "plated",
                        "warnings": [],
                    },
                },
            ]
        )
    return transcript


def _good_answer(with_commas: bool = True) -> str:
    thousand = "1,000" if with_commas else "1000"
    ten_thousand = "10,000" if with_commas else "10000"
    return (
        "10 pg: 1.0e9 CFU/ug; "
        "100 pg: 1.0e9 CFU/ug; "
        "{:s} pg: 1.0e9 CFU/ug; "
        "{:s} pg: 1.0e9 CFU/ug. "
        "The runs were internally consistent."
    ).format(thousand, ten_thousand)


def test_good_trajectory_scores_high():
    scores = score_transform_trajectory(
        final_answer=_good_answer(),
        transcript=_good_transcript(),
        ground_truth_path=str(TRANSFORM_GROUND_TRUTH_PATH),
    )
    assert scores["decision_quality"] == 1.0
    assert scores["task_success"] == 1.0
    assert scores["overall"] > 0.9


def test_wrong_heat_shock_reduces_decision_score():
    transcript = _good_transcript()
    transcript[1]["arguments"]["heat_shock_seconds"] = 45
    scores = score_transform_trajectory(
        final_answer=_good_answer(),
        transcript=transcript,
        ground_truth_path=str(TRANSFORM_GROUND_TRUTH_PATH),
    )
    assert scores["decision_scores"]["heat_shock_duration_seconds"] == 0.0
    assert scores["decision_quality"] < 1.0


def test_task_success_requires_numeric_values_matching_transcript():
    answer = (
        "10 pg: reported CFU/ug; 100 pg: reported CFU/ug; 1,000 pg: reported CFU/ug; "
        "10,000 pg: reported CFU/ug. The runs were internally consistent."
    )
    assert score_task_success(answer, _good_transcript()) == 0.0


def test_task_success_accepts_uncommaed_mass_labels():
    assert score_task_success(_good_answer(with_commas=False), _good_transcript()) == 1.0


def test_uncountable_counts_zero_out_task_success_and_countability_decision():
    transcript = _good_transcript()
    transcript[-1]["arguments"]["observed_colonies"] = 1200
    transcript[-1]["arguments"]["status"] = "count_out_of_range"
    transcript[-1]["arguments"]["warnings"] = [
        "Observed colonies fall outside the cited countable range of 25-250 colonies per plate."
    ]

    scores = score_transform_trajectory(
        final_answer=_good_answer(),
        transcript=transcript,
        ground_truth_path=str(TRANSFORM_GROUND_TRUTH_PATH),
    )

    assert scores["task_success"] == 0.0
    assert scores["decision_scores"]["countable_colony_range"] == 0.0


def test_inspect_style_tool_messages_score_soc_default_correctly():
    transcript = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call_prepare",
                    "function": "prepare_media",
                    "arguments": {
                        "medium": "LB agar",
                        "antibiotic": "ampicillin",
                        "antibiotic_concentration_ug_ml": 100,
                        "plate_count": 4,
                    },
                }
            ],
        }
    ]
    for idx, mass in enumerate(TARGET_MASSES, start=1):
        transcript.append(
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "call_transform_{:d}".format(idx),
                        "function": "transform",
                        "arguments": {
                            "plasmid_mass_pg": mass,
                            "heat_shock_seconds": 30,
                            "recovery_minutes": 60,
                        },
                    }
                ],
            }
        )
        transcript.append(
            {
                "role": "tool",
                "tool_call_id": "call_transform_{:d}".format(idx),
                "function": "transform",
                "content": json.dumps(
                    {
                        "culture_id": "culture_{:03d}".format(idx),
                        "heat_shock_seconds": 30,
                        "recovery_minutes": 60,
                        "outgrowth_media": "SOC",
                    }
                ),
            }
        )

    scores = score_transform_trajectory(
        final_answer=_good_answer(),
        transcript=transcript,
        ground_truth_path=str(TRANSFORM_GROUND_TRUTH_PATH),
    )

    assert scores["decision_scores"]["soc_outgrowth"] == 1.0


def _good_growth_transcript():
    transcript = []
    expected_doubling_times = {
        "LB": 20.0,
        "M9 + glucose": 57.0,
        "LB + chloramphenicol (1.8 uM)": 40.0,
    }
    for condition, doubling_time in expected_doubling_times.items():
        growth_id = "growth_" + condition.lower().replace(" ", "_").replace("+", "plus").replace("(", "").replace(")", "").replace(".", "")
        transcript.append(
            {
                "type": "tool_call",
                "tool_name": "inoculate_growth",
                "arguments": {
                    "growth_id": growth_id,
                    "condition": condition,
                    "starting_od600": 0.05,
                },
            }
        )
        od_values = {
            "LB": [0.05, 0.084, 0.141, 0.237, 0.4, 0.672, 1.131, 1.902, 3.2],
            "M9 + glucose": [0.05, 0.06, 0.072, 0.086, 0.104, 0.124, 0.149, 0.179, 0.214],
            "LB + chloramphenicol (1.8 uM)": [0.05, 0.065, 0.084, 0.109, 0.141, 0.183, 0.237, 0.308, 0.4],
        }[condition]
        for idx, value in enumerate(od_values):
            if idx > 0:
                transcript.append(
                    {
                        "type": "tool_call",
                        "tool_name": "incubate",
                        "arguments": {
                            "growth_id": growth_id,
                            "condition": condition,
                            "duration_minutes": 15,
                            "elapsed_minutes": idx * 15,
                        },
                    }
                )
            dilution = 10.0 if condition == "LB" and idx >= 6 else 1.0
            transcript.append(
                {
                    "type": "tool_call",
                    "tool_name": "measure_od600",
                    "arguments": {
                        "growth_id": growth_id,
                        "condition": condition,
                        "elapsed_minutes": idx * 15,
                        "dilution_factor": dilution,
                        "observed_od600": value / dilution,
                        "estimated_undiluted_od600": value,
                    },
                }
            )
        transcript.append(
            {
                "type": "tool_call",
                "tool_name": "fit_growth_curve",
                "arguments": {
                    "growth_id": growth_id,
                    "condition": condition,
                    "status": "analyzable",
                    "qualifying_points": 4,
                    "estimated_doubling_time_minutes": doubling_time,
                },
            }
        )
    return transcript


def _good_growth_answer() -> str:
    return (
        "LB: 20 minutes; "
        "M9 + glucose: 57 minutes; "
        "LB + chloramphenicol (1.8 uM): 40 minutes. "
        "Fastest to slowest: LB, LB + chloramphenicol (1.8 uM), M9 + glucose."
    )


def test_good_growth_trajectory_scores_high():
    scores = score_growth_trajectory(
        final_answer=_good_growth_answer(),
        transcript=_good_growth_transcript(),
        ground_truth_path=str(GROWTH_GROUND_TRUTH_PATH),
    )
    assert scores["decision_quality"] == 1.0
    assert scores["task_success"] == 1.0
    assert scores["overall"] > 0.9


def test_growth_task_success_requires_matching_doubling_times():
    answer = (
        "LB: about 20 minutes; M9 + glucose: about 30 minutes; "
        "LB + chloramphenicol (1.8 uM): about 40 minutes."
    )
    assert score_growth_task_success(answer, _good_growth_transcript()) == 0.0


def test_growth_fit_failure_reduces_decision_quality_and_task_success():
    transcript = _good_growth_transcript()
    transcript[-1]["arguments"]["status"] = "insufficient_points"
    transcript[-1]["arguments"]["qualifying_points"] = 2
    transcript[-1]["arguments"].pop("estimated_doubling_time_minutes")
    scores = score_growth_trajectory(
        final_answer=_good_growth_answer(),
        transcript=transcript,
        ground_truth_path=str(GROWTH_GROUND_TRUTH_PATH),
    )
    assert scores["task_success"] == 0.0
    assert scores["decision_scores"]["growth_curve_analyzable"] == 0.0


def _good_pcr_transcript():
    return [
        {
            "type": "tool_call",
            "tool_name": "run_pcr",
            "arguments": {
                "reaction_id": "pcr_001",
                "polymerase_name": "Q5 High-Fidelity DNA polymerase",
                "normalized_polymerase_name": "Q5 High-Fidelity DNA polymerase",
                "additive": "DMSO",
                "normalized_additive": "DMSO",
                "extension_seconds": 60,
                "cycle_count": 32,
                "target_size_bp": 2000,
                "status": "clean_target_band",
                "visible_bands_bp": [2000],
                "smear_present": False,
            },
        },
        {
            "type": "tool_call",
            "tool_name": "run_gel",
            "arguments": {
                "gel_id": "gel_001",
                "reaction_id": "pcr_001",
                "polymerase_name": "Q5 High-Fidelity DNA polymerase",
                "normalized_polymerase_name": "Q5 High-Fidelity DNA polymerase",
                "additive": "DMSO",
                "normalized_additive": "DMSO",
                "extension_seconds": 60,
                "cycle_count": 32,
                "target_size_bp": 2000,
                "status": "single_clean_target_band",
                "visible_bands_bp": [2000],
                "smear_present": False,
            },
        },
    ]


def _good_pcr_answer() -> str:
    return (
        "Polymerase: Q5 High-Fidelity DNA polymerase\n"
        "Additive: DMSO\n"
        "Extension: 60 seconds\n"
        "Cycles: 32\n"
        "Result: single clean 2 kb band"
    )


def test_good_pcr_trajectory_scores_high():
    scores = score_pcr_trajectory(
        final_answer=_good_pcr_answer(),
        transcript=_good_pcr_transcript(),
        ground_truth_path=str(PCR_GROUND_TRUTH_PATH),
    )
    assert scores["decision_quality"] == 1.0
    assert scores["task_success"] == 1.0
    assert scores["overall"] > 0.9


def test_pcr_task_success_requires_matching_reported_condition():
    answer = (
        "Polymerase: Phusion High-Fidelity DNA polymerase\n"
        "Additive: DMSO\n"
        "Extension: 60 seconds\n"
        "Cycles: 32\n"
        "Result: single clean 2 kb band"
    )
    assert score_pcr_task_success(answer, _good_pcr_transcript()) == 0.0


def test_failed_pcr_requires_troubleshooting_for_credit():
    transcript = [
        {
            "type": "tool_call",
            "tool_name": "run_pcr",
            "arguments": {
                "reaction_id": "pcr_002",
                "polymerase_name": "Q5 High-Fidelity DNA polymerase",
                "normalized_polymerase_name": "Q5 High-Fidelity DNA polymerase",
                "additive": "none",
                "normalized_additive": "none",
                "extension_seconds": 60,
                "cycle_count": 32,
                "target_size_bp": 2000,
                "status": "gc_rich_failure",
                "visible_bands_bp": [],
                "smear_present": False,
            },
        },
        {
            "type": "tool_call",
            "tool_name": "run_gel",
            "arguments": {
                "gel_id": "gel_002",
                "reaction_id": "pcr_002",
                "polymerase_name": "Q5 High-Fidelity DNA polymerase",
                "normalized_polymerase_name": "Q5 High-Fidelity DNA polymerase",
                "additive": "none",
                "normalized_additive": "none",
                "extension_seconds": 60,
                "cycle_count": 32,
                "target_size_bp": 2000,
                "status": "no_visible_product",
                "visible_bands_bp": [],
                "smear_present": False,
            },
        },
    ]
    scores = score_pcr_trajectory(
        final_answer=(
            "Polymerase: Q5 High-Fidelity DNA polymerase\n"
            "Additive: none\n"
            "Extension: 60 seconds\n"
            "Cycles: 32\n"
            "Result: not achieved"
        ),
        transcript=transcript,
        ground_truth_path=str(PCR_GROUND_TRUTH_PATH),
    )
    assert scores["task_success"] == 0.0
    assert scores["troubleshooting"] == 0.0


def _good_screen_transcript():
    return [
        {
            "type": "tool_call",
            "tool_name": "inspect_screening_plate",
            "arguments": {
                "status": "screening_plate_ready",
                "plate_id": "screen_plate_001",
                "white_colony_count": 12,
                "blue_colony_count": 18,
            },
        },
        {
            "type": "tool_call",
            "tool_name": "run_colony_pcr",
            "arguments": {
                "plate_id": "screen_plate_001",
                "primer_pair": "M13/pUC flank primers",
                "screened_colony_ids": [
                    "white_001",
                    "white_002",
                    "white_003",
                    "white_004",
                    "white_005",
                    "white_006",
                ],
                "screened_colony_count": 6,
                "screening_strategy": "white_only",
                "cumulative_screened_white_colony_count": 6,
                "cumulative_confidence_pct": 95.3,
                "confirmed_recombinant_ids_cumulative": ["white_002", "white_005"],
                "confirmed_recombinant_ids_in_batch": ["white_002", "white_005"],
            },
        },
    ]


def _good_screen_answer() -> str:
    return (
        "White colonies screened: 6\n"
        "Confirmed recombinant colonies: white_002, white_005\n"
        "Confidence achieved: 95.3%\n"
        "Interpretation: Two recombinant colonies confirmed from six white candidates."
    )


def test_good_screen_trajectory_scores_high():
    scores = score_screen_trajectory(
        final_answer=_good_screen_answer(),
        transcript=_good_screen_transcript(),
        ground_truth_path=str(SCREEN_GROUND_TRUTH_PATH),
    )
    assert scores["task_success"] == 1.0
    assert scores["decision_quality"] == 1.0
    assert scores["troubleshooting"] == 1.0
    assert scores["efficiency"] == 1.0
    assert scores["overall"] >= 0.999


def test_screen_task_success_requires_matching_screened_count():
    mismatch = (
        "White colonies screened: 8\n"
        "Confirmed recombinant colonies: white_002, white_005\n"
        "Confidence achieved: 95.3%\n"
        "Interpretation: Two recombinant colonies confirmed."
    )
    assert score_screen_task_success(mismatch, _good_screen_transcript()) == 0.0


def test_screen_task_success_requires_interpretation_keyword():
    answer = (
        "White colonies screened: 6\n"
        "Confirmed recombinant colonies: white_002, white_005\n"
        "Confidence achieved: 95.3%\n"
        "Interpretation: Two positive clones confirmed."
    )
    assert score_screen_task_success(answer, _good_screen_transcript()) == 0.0


def test_screen_includes_blue_colony_fails_decision_quality():
    transcript = _good_screen_transcript()
    transcript.append(
        {
            "type": "tool_call",
            "tool_name": "run_colony_pcr",
            "arguments": {
                "plate_id": "screen_plate_001",
                "primer_pair": "M13/pUC flank primers",
                "screened_colony_ids": ["blue_001"],
                "screened_colony_count": 1,
                "screening_strategy": "includes_blue",
                "cumulative_screened_white_colony_count": 6,
                "cumulative_confidence_pct": 95.3,
                "confirmed_recombinant_ids_cumulative": ["white_002", "white_005"],
                "confirmed_recombinant_ids_in_batch": [],
            },
        }
    )
    scores = score_screen_trajectory(
        final_answer=_good_screen_answer(),
        transcript=transcript,
        ground_truth_path=str(SCREEN_GROUND_TRUTH_PATH),
    )
    assert scores["decision_scores"]["screens_only_white_colonies"] == 0.0


def test_screen_blue_colony_without_recombinants_requires_diagnosis_for_credit():
    transcript = [
        {
            "type": "tool_call",
            "tool_name": "inspect_screening_plate",
            "arguments": {
                "status": "screening_plate_ready",
                "plate_id": "screen_plate_001",
            },
        },
        {
            "type": "tool_call",
            "tool_name": "run_colony_pcr",
            "arguments": {
                "plate_id": "screen_plate_001",
                "primer_pair": "M13/pUC flank primers",
                "screened_colony_ids": ["blue_001", "blue_002"],
                "screened_colony_count": 2,
                "screening_strategy": "includes_blue",
                "cumulative_screened_white_colony_count": 0,
                "cumulative_confidence_pct": 0.0,
                "confirmed_recombinant_ids_cumulative": [],
                "confirmed_recombinant_ids_in_batch": [],
            },
        },
    ]
    bare_answer = (
        "White colonies screened: 0\n"
        "Confirmed recombinant colonies: None\n"
        "Confidence achieved: 0.0%\n"
        "Interpretation: No recombinant colonies confirmed."
    )
    scores_without_diagnosis = score_screen_trajectory(
        final_answer=bare_answer,
        transcript=transcript,
        ground_truth_path=str(SCREEN_GROUND_TRUTH_PATH),
    )
    assert scores_without_diagnosis["troubleshooting"] == 0.0

    diagnosed_answer = bare_answer + (
        "\nBlue colonies should not have been screened because they are empty-vector "
        "background."
    )
    scores_with_diagnosis = score_screen_trajectory(
        final_answer=diagnosed_answer,
        transcript=transcript,
        ground_truth_path=str(SCREEN_GROUND_TRUTH_PATH),
    )
    assert scores_with_diagnosis["troubleshooting"] > 0.0


def test_screen_undersampling_without_diagnosis_scores_zero_troubleshooting():
    transcript = [
        {
            "type": "tool_call",
            "tool_name": "inspect_screening_plate",
            "arguments": {
                "status": "screening_plate_ready",
                "plate_id": "screen_plate_001",
            },
        },
        {
            "type": "tool_call",
            "tool_name": "run_colony_pcr",
            "arguments": {
                "plate_id": "screen_plate_001",
                "primer_pair": "M13/pUC flank primers",
                "screened_colony_ids": ["white_001", "white_003", "white_004"],
                "screened_colony_count": 3,
                "screening_strategy": "white_only",
                "cumulative_screened_white_colony_count": 3,
                "cumulative_confidence_pct": 78.4,
                "confirmed_recombinant_ids_cumulative": [],
                "confirmed_recombinant_ids_in_batch": [],
            },
        },
    ]
    answer = (
        "White colonies screened: 3\n"
        "Confirmed recombinant colonies: None\n"
        "Confidence achieved: 78.4%\n"
        "Interpretation: No recombinant colonies confirmed in this batch."
    )
    scores = score_screen_trajectory(
        final_answer=answer,
        transcript=transcript,
        ground_truth_path=str(SCREEN_GROUND_TRUTH_PATH),
    )
    assert scores["task_success"] == 0.0
    assert scores["decision_scores"]["reaches_confidence_threshold"] == 0.0
    assert scores["decision_scores"]["screens_at_least_six_white_colonies"] == 0.0
    assert scores["troubleshooting"] == 0.0
