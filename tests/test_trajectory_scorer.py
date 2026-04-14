"""Trajectory-scorer tests for Transform-01."""

from __future__ import annotations

import json
from pathlib import Path

from src.trajectory_scorer import (
    score_clone_task_success,
    score_clone_trajectory,
    score_express_task_success,
    score_express_trajectory,
    score_gibson_task_success,
    score_gibson_trajectory,
    score_golden_gate_task_success,
    score_golden_gate_trajectory,
    score_growth_task_success,
    score_growth_trajectory,
    score_miniprep_task_success,
    score_miniprep_trajectory,
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
CLONE_GROUND_TRUTH_PATH = Path(__file__).resolve().parents[1] / "task_data" / "clone_01" / "ground_truth.json"
GOLDEN_GATE_GROUND_TRUTH_PATH = (
    Path(__file__).resolve().parents[1] / "task_data" / "golden_gate_01" / "ground_truth.json"
)
GIBSON_GROUND_TRUTH_PATH = (
    Path(__file__).resolve().parents[1] / "task_data" / "gibson_01" / "ground_truth.json"
)
MINIPREP_GROUND_TRUTH_PATH = (
    Path(__file__).resolve().parents[1] / "task_data" / "miniprep_01" / "ground_truth.json"
)
EXPRESS_GROUND_TRUTH_PATH = (
    Path(__file__).resolve().parents[1] / "task_data" / "express_01" / "ground_truth.json"
)
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


def _good_clone_transcript():
    digest_vector = {
        "type": "tool_call",
        "tool_name": "restriction_digest",
        "arguments": {
            "digest_id": "digest_001",
            "substrate_fragment_id": "puc19_vector",
            "enzyme_names": ["EcoRI", "BamHI"],
            "enzymes_key": "bamhi+ecori",
            "buffer": "CutSmart",
            "buffer_normalized": "cutsmart",
            "temperature_c": 37.0,
            "duration_minutes": 60,
            "heat_inactivate_after": True,
            "output_fragment_ids": ["fragment_003"],
            "status": "digested",
        },
    }
    digest_insert = dict(digest_vector)
    digest_insert = {
        "type": "tool_call",
        "tool_name": "restriction_digest",
        "arguments": {
            "digest_id": "digest_002",
            "substrate_fragment_id": "insert_raw",
            "enzyme_names": ["EcoRI", "BamHI"],
            "enzymes_key": "bamhi+ecori",
            "buffer": "CutSmart",
            "buffer_normalized": "cutsmart",
            "temperature_c": 37.0,
            "duration_minutes": 60,
            "heat_inactivate_after": True,
            "output_fragment_ids": ["fragment_004"],
            "status": "digested",
        },
    }
    ligation = {
        "type": "tool_call",
        "tool_name": "ligate",
        "arguments": {
            "ligation_id": "ligation_001",
            "vector_fragment_id": "fragment_003",
            "insert_fragment_ids": ["fragment_004"],
            "ligase_name": "T4 DNA ligase",
            "ligase_normalized": "t4 dna ligase",
            "vector_to_insert_molar_ratio": 3.0,
            "temperature_c": 16.0,
            "duration_minutes": 960,
            "status": "ligated",
        },
    }
    prepare = {
        "type": "tool_call",
        "tool_name": "prepare_media",
        "arguments": {
            "medium": "LB agar",
            "antibiotic": "ampicillin",
            "antibiotic_concentration_ug_ml": 100,
            "plate_count": 1,
        },
    }
    transform_call = {
        "type": "tool_call",
        "tool_name": "transform_ligation",
        "arguments": {
            "ligation_id": "ligation_001",
            "culture_id": "culture_001",
            "heat_shock_seconds": 30,
            "recovery_minutes": 60,
            "outgrowth_media": "SOC",
            "status": "transformed",
            "expected_transformants": 400.0,
        },
    }
    plate_call = {
        "type": "tool_call",
        "tool_name": "plate",
        "arguments": {
            "culture_id": "culture_001",
            "plate_id": "plate_001",
            "dilution_factor": 1.0,
            "volume_ul": 100,
        },
    }
    count = {
        "type": "tool_call",
        "tool_name": "count_colonies",
        "arguments": {
            "plating_id": "plating_001",
            "observed_colonies": 200,
            "status": "plated",
        },
    }
    inspect_plate = {
        "type": "tool_call",
        "tool_name": "inspect_screening_plate",
        "arguments": {
            "status": "screening_plate_ready",
            "plate_id": "screen_plate_001",
            "white_colony_count": 12,
            "blue_colony_count": 18,
        },
    }
    colony_pcr = {
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
    }
    return [
        digest_vector,
        digest_insert,
        ligation,
        prepare,
        transform_call,
        plate_call,
        count,
        inspect_plate,
        colony_pcr,
    ]


def _good_clone_answer() -> str:
    return (
        "Digest enzymes: EcoRI, BamHI\n"
        "Digest buffer: CutSmart\n"
        "Ligase: T4 DNA ligase\n"
        "Vector:insert molar ratio: 1:3\n"
        "Ligation temperature: 16 C\n"
        "Transformants observed: 200\n"
        "White colonies screened: 6\n"
        "Confirmed recombinant colonies: white_002, white_005\n"
        "Confidence achieved: 95.3%\n"
        "Interpretation: Two recombinant colonies confirmed; cloning succeeded."
    )


def test_good_clone_trajectory_scores_high():
    scores = score_clone_trajectory(
        final_answer=_good_clone_answer(),
        transcript=_good_clone_transcript(),
        ground_truth_path=str(CLONE_GROUND_TRUTH_PATH),
    )
    assert scores["task_success"] == 1.0
    assert scores["decision_quality"] == 1.0
    assert scores["troubleshooting"] == 1.0
    assert scores["efficiency"] >= 0.5
    assert scores["overall"] >= 0.9


def test_clone_wrong_buffer_fails_decision_quality():
    transcript = _good_clone_transcript()
    transcript[0]["arguments"]["buffer_normalized"] = "neb1.1"
    transcript[0]["arguments"]["status"] = "wrong_buffer"
    scores = score_clone_trajectory(
        final_answer=_good_clone_answer(),
        transcript=transcript,
        ground_truth_path=str(CLONE_GROUND_TRUTH_PATH),
    )
    assert scores["decision_scores"]["digest_uses_compatible_buffer"] == 0.0
    assert scores["troubleshooting"] < 1.0


def test_clone_wrong_ligase_fails_decision_quality():
    transcript = _good_clone_transcript()
    transcript[2]["arguments"]["ligase_normalized"] = "e. coli dna ligase"
    transcript[2]["arguments"]["status"] = "wrong_ligase"
    answer = _good_clone_answer().replace("T4 DNA ligase", "E. coli DNA ligase")
    scores = score_clone_trajectory(
        final_answer=answer,
        transcript=transcript,
        ground_truth_path=str(CLONE_GROUND_TRUTH_PATH),
    )
    assert scores["decision_scores"]["uses_t4_dna_ligase"] == 0.0
    assert score_clone_task_success(answer, transcript) == 0.0


def test_clone_extreme_ratio_without_diagnosis_fails_troubleshooting():
    transcript = _good_clone_transcript()
    transcript[2]["arguments"]["vector_to_insert_molar_ratio"] = 50.0
    transcript[2]["arguments"]["status"] = "wrong_ratio"
    scores = score_clone_trajectory(
        final_answer=_good_clone_answer(),
        transcript=transcript,
        ground_truth_path=str(CLONE_GROUND_TRUTH_PATH),
    )
    assert scores["decision_scores"]["uses_reasonable_molar_ratio"] == 0.0
    assert scores["troubleshooting"] == 0.0


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


def _good_golden_gate_transcript():
    assembly_call = {
        "type": "tool_call",
        "tool_name": "golden_gate_assembly",
        "arguments": {
            "assembly_id": "assembly_001",
            "fragment_ids": [
                "gg_backbone",
                "gg_insert_promoter",
                "gg_insert_cds",
                "gg_insert_terminator",
            ],
            "fragment_count": 4,
            "enzyme_name": "BsaI",
            "enzyme_normalized": "bsai",
            "ligase_name": "T4 DNA ligase",
            "ligase_normalized": "t4 dna ligase",
            "buffer": "T4 DNA ligase buffer",
            "cycle_count": 30,
            "digest_temperature_c": 37.0,
            "ligate_temperature_c": 16.0,
            "final_digest_minutes": 5,
            "heat_kill_temperature_c": 60.0,
            "output_fragment_id": "fragment_010",
            "status": "assembled",
            "effective_assembly_efficiency": 0.85,
            "expected_transformant_yield": 600.0,
        },
    }
    prepare = {
        "type": "tool_call",
        "tool_name": "prepare_media",
        "arguments": {
            "medium": "LB agar",
            "antibiotic": "ampicillin",
            "antibiotic_concentration_ug_ml": 100,
            "plate_count": 1,
        },
    }
    transform_call = {
        "type": "tool_call",
        "tool_name": "transform_assembly",
        "arguments": {
            "assembly_id": "assembly_001",
            "culture_id": "culture_001",
            "status": "transformed",
            "effective_assembly_efficiency": 0.85,
        },
    }
    plate_call = {
        "type": "tool_call",
        "tool_name": "plate",
        "arguments": {
            "culture_id": "culture_001",
            "plate_id": "plate_001",
            "dilution_factor": 1.0,
            "volume_ul": 100,
        },
    }
    count = {
        "type": "tool_call",
        "tool_name": "count_colonies",
        "arguments": {
            "plating_id": "plating_001",
            "observed_colonies": 300,
            "status": "plated",
        },
    }
    return [assembly_call, prepare, transform_call, plate_call, count]


def _good_golden_gate_answer() -> str:
    return (
        "Type IIS enzyme: BsaI\n"
        "Ligase: T4 DNA ligase\n"
        "Digest temperature: 37 C\n"
        "Ligate temperature: 16 C\n"
        "Cycle count: 30\n"
        "Fragment count: 4\n"
        "Transformants observed: 300\n"
        "Interpretation: Four-fragment Golden Gate assembly completed and transformed successfully."
    )


def test_good_golden_gate_trajectory_scores_high():
    scores = score_golden_gate_trajectory(
        final_answer=_good_golden_gate_answer(),
        transcript=_good_golden_gate_transcript(),
        ground_truth_path=str(GOLDEN_GATE_GROUND_TRUTH_PATH),
    )
    assert scores["task_success"] == 1.0
    assert scores["decision_quality"] == 1.0
    assert scores["troubleshooting"] == 1.0
    assert scores["overall"] >= 0.9


def test_golden_gate_wrong_enzyme_fails_decision_quality():
    transcript = _good_golden_gate_transcript()
    transcript[0]["arguments"]["enzyme_normalized"] = "ecori"
    transcript[0]["arguments"]["status"] = "wrong_enzyme"
    scores = score_golden_gate_trajectory(
        final_answer=_good_golden_gate_answer(),
        transcript=transcript,
        ground_truth_path=str(GOLDEN_GATE_GROUND_TRUTH_PATH),
    )
    assert scores["decision_scores"]["uses_type_iis_enzyme"] == 0.0
    assert scores["task_success"] == 0.0


def test_golden_gate_wrong_ligase_fails_decision_quality():
    transcript = _good_golden_gate_transcript()
    transcript[0]["arguments"]["ligase_normalized"] = "e. coli dna ligase"
    transcript[0]["arguments"]["status"] = "wrong_ligase"
    answer = _good_golden_gate_answer().replace("T4 DNA ligase", "E. coli DNA ligase")
    assert score_golden_gate_task_success(answer, transcript) == 0.0
    scores = score_golden_gate_trajectory(
        final_answer=answer,
        transcript=transcript,
        ground_truth_path=str(GOLDEN_GATE_GROUND_TRUTH_PATH),
    )
    assert scores["decision_scores"]["uses_t4_dna_ligase"] == 0.0


def _good_gibson_transcript():
    gibson_call = {
        "type": "tool_call",
        "tool_name": "gibson_assembly",
        "arguments": {
            "gibson_id": "gibson_001",
            "fragment_ids": ["gibson_backbone_linear", "gibson_insert_pcr"],
            "fragment_count": 2,
            "master_mix_name": "Gibson Assembly Master Mix",
            "master_mix_normalized": "gibson assembly master mix",
            "temperature_c": 50.0,
            "duration_minutes": 15,
            "overlap_length_bp": 20,
            "output_fragment_id": "fragment_020",
            "status": "assembled",
            "effective_assembly_efficiency": 0.80,
            "expected_transformant_yield": 500.0,
        },
    }
    prepare = {
        "type": "tool_call",
        "tool_name": "prepare_media",
        "arguments": {
            "medium": "LB agar",
            "antibiotic": "ampicillin",
            "antibiotic_concentration_ug_ml": 100,
            "plate_count": 1,
        },
    }
    transform_call = {
        "type": "tool_call",
        "tool_name": "transform_gibson",
        "arguments": {
            "gibson_id": "gibson_001",
            "culture_id": "culture_001",
            "status": "transformed",
        },
    }
    plate_call = {
        "type": "tool_call",
        "tool_name": "plate",
        "arguments": {
            "culture_id": "culture_001",
            "plate_id": "plate_001",
            "dilution_factor": 1.0,
            "volume_ul": 100,
        },
    }
    count = {
        "type": "tool_call",
        "tool_name": "count_colonies",
        "arguments": {
            "plating_id": "plating_001",
            "observed_colonies": 250,
            "status": "plated",
        },
    }
    return [gibson_call, prepare, transform_call, plate_call, count]


def _good_gibson_answer() -> str:
    return (
        "Assembly method: Gibson\n"
        "Master mix: Gibson Assembly Master Mix\n"
        "Temperature: 50 C\n"
        "Duration: 15 min\n"
        "Fragment count: 2\n"
        "Overlap length: 20 bp\n"
        "Transformants observed: 250\n"
        "Interpretation: Gibson assembly completed successfully."
    )


def test_good_gibson_trajectory_scores_high():
    scores = score_gibson_trajectory(
        final_answer=_good_gibson_answer(),
        transcript=_good_gibson_transcript(),
        ground_truth_path=str(GIBSON_GROUND_TRUTH_PATH),
    )
    assert scores["task_success"] == 1.0
    assert scores["decision_quality"] == 1.0
    assert scores["overall"] >= 0.9


def test_gibson_wrong_master_mix_triggers_troubleshooting_requirement():
    transcript = _good_gibson_transcript()
    transcript[0]["arguments"]["master_mix_normalized"] = "t4 dna ligase buffer"
    transcript[0]["arguments"]["status"] = "wrong_master_mix"
    scores = score_gibson_trajectory(
        final_answer=_good_gibson_answer(),
        transcript=transcript,
        ground_truth_path=str(GIBSON_GROUND_TRUTH_PATH),
    )
    assert scores["troubleshooting"] < 1.0
    assert scores["task_success"] == 0.0


def _good_miniprep_transcript():
    return [
        {
            "type": "tool_call",
            "tool_name": "perform_miniprep",
            "arguments": {
                "miniprep_id": "miniprep_001",
                "culture_volume_ml": 5.0,
                "lysis_buffer_sequence": "P1,P2,P3",
                "lysis_buffer_sequence_normalized": "p1,p2,p3",
                "lysis_duration_min": 3,
                "purification_method": "silica column",
                "purification_method_normalized": "silica column",
                "elution_volume_ul": 50.0,
                "final_concentration_ng_ul": 200.0,
                "a260_a280_ratio": 1.9,
                "total_yield_ug": 10.0,
                "status": "prepared",
            },
        }
    ]


def _good_miniprep_answer() -> str:
    return (
        "Culture volume: 5 mL\n"
        "Lysis buffer sequence: P1,P2,P3\n"
        "Lysis duration: 3 min\n"
        "Purification method: silica column\n"
        "Elution volume: 50 uL\n"
        "Plasmid concentration: 200.0 ng/uL\n"
        "A260/A280: 1.90\n"
        "Total yield: 10.0 ug\n"
        "Interpretation: Plasmid is pure and ready for downstream use."
    )


def test_good_miniprep_trajectory_scores_high():
    scores = score_miniprep_trajectory(
        final_answer=_good_miniprep_answer(),
        transcript=_good_miniprep_transcript(),
        ground_truth_path=str(MINIPREP_GROUND_TRUTH_PATH),
    )
    assert scores["task_success"] == 1.0
    assert scores["decision_quality"] == 1.0
    assert scores["overall"] >= 0.9


def test_miniprep_wrong_buffer_triggers_troubleshooting():
    transcript = _good_miniprep_transcript()
    transcript[0]["arguments"]["lysis_buffer_sequence_normalized"] = "p3,p2,p1"
    transcript[0]["arguments"]["status"] = "wrong_buffer_sequence"
    scores = score_miniprep_trajectory(
        final_answer=_good_miniprep_answer(),
        transcript=transcript,
        ground_truth_path=str(MINIPREP_GROUND_TRUTH_PATH),
    )
    assert scores["troubleshooting"] < 1.0
    assert scores["task_success"] == 0.0


def _good_express_transcript():
    return [
        {
            "type": "tool_call",
            "tool_name": "run_protein_expression",
            "arguments": {
                "expression_id": "expression_001",
                "host_strain": "BL21(DE3)",
                "host_strain_normalized": "bl21(de3)",
                "protein_name": "MBP-GFP fusion",
                "expected_molecular_weight_kda": 72.0,
                "iptg_concentration_mm": 1.0,
                "induction_od600": 0.6,
                "induction_temperature_c": 18,
                "induction_hours": 16,
                "lysis_buffer_ph": 8.0,
                "culture_volume_ml": 500.0,
                "soluble_yield_mg_per_l": 36.8,
                "insoluble_fraction": 0.08,
                "total_soluble_mg": 18.4,
                "status": "induced",
            },
        }
    ]


def _good_express_answer() -> str:
    return (
        "Host strain: BL21(DE3)\n"
        "IPTG concentration: 1.0 mM\n"
        "Induction OD600: 0.6\n"
        "Induction temperature: 18 C\n"
        "Induction duration: 16 h\n"
        "Lysis buffer pH: 8.0\n"
        "Expected soluble yield: 36.8 mg/L\n"
        "Interpretation: Expression succeeded at low-temperature overnight induction with high solubility."
    )


def test_good_express_trajectory_scores_high():
    scores = score_express_trajectory(
        final_answer=_good_express_answer(),
        transcript=_good_express_transcript(),
        ground_truth_path=str(EXPRESS_GROUND_TRUTH_PATH),
    )
    assert scores["task_success"] == 1.0
    assert scores["decision_quality"] == 1.0
    assert scores["overall"] >= 0.9


def test_express_wrong_host_triggers_troubleshooting():
    transcript = _good_express_transcript()
    transcript[0]["arguments"]["host_strain_normalized"] = "dh5alpha"
    transcript[0]["arguments"]["status"] = "wrong_host_strain"
    scores = score_express_trajectory(
        final_answer=_good_express_answer(),
        transcript=transcript,
        ground_truth_path=str(EXPRESS_GROUND_TRUTH_PATH),
    )
    assert scores["troubleshooting"] < 1.0
    assert scores["decision_scores"]["uses_t7_expression_host"] == 0.0
