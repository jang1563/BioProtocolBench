"""Tests for discovery-decision tools."""

from __future__ import annotations

import asyncio
import json

from src.tools.discovery import (
    assay_primary_readout,
    list_candidate_targets_call,
    load_assay_catalog,
    load_target_catalog,
    lookup_target_profile_call,
    simulate_validation_assay,
    validation_result_label,
)


def test_list_candidate_targets_returns_all_targets():
    payload = json.loads(asyncio.run(list_candidate_targets_call()))

    assert sorted(target["target_id"] for target in payload["targets"]) == [
        "TGT_A",
        "TGT_B",
        "TGT_C",
        "TGT_D",
    ]


def test_lookup_target_profile_returns_expected_public_fields():
    payload = json.loads(asyncio.run(lookup_target_profile_call("TGT_A")))

    assert set(payload) == {
        "target_id",
        "disease_context",
        "perturbation_score",
        "viability_risk",
        "context_consistency",
        "genetic_support",
        "patient_signal",
        "literature_support",
        "summary",
    }
    assert payload["target_id"] == "TGT_A"


def test_simulate_validation_assay_is_deterministic_per_sample():
    first = simulate_validation_assay("sample_alpha", target_id="TGT_A", assay_id="ASY_CYTOKINE")
    second = simulate_validation_assay("sample_alpha", target_id="TGT_A", assay_id="ASY_CYTOKINE")
    third = simulate_validation_assay("sample_beta", target_id="TGT_A", assay_id="ASY_CYTOKINE")

    assert first == second
    assert first["effect_size"] != third["effect_size"]


def test_assay_catalog_and_result_label_helpers():
    targets = load_target_catalog()
    assays = load_assay_catalog()
    result = simulate_validation_assay("sample_alpha", target_id="TGT_C", assay_id="ASY_PATHWAY")

    assert "TGT_A" in targets
    assert "ASY_CYTOKINE" in assays
    assert assay_primary_readout("ASY_CYTOKINE") == "change in inflammatory cytokine program"
    assert validation_result_label(result) == "fail"
