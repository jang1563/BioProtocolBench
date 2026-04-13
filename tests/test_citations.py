"""Citation-policy enforcement tests for LabCraft."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PARAMETER_FILES = sorted((ROOT / "data" / "parameters").glob("*.json"))
GROUND_TRUTH_FILES = sorted((ROOT / "task_data").glob("*/ground_truth.json"))
ALLOWED_TIERS = {"Gold", "Silver", "Bronze", "Copper"}
TIER_RANK = {"Copper": 1, "Bronze": 2, "Silver": 3, "Gold": 4}


def _load_json(path: Path):
    with open(path) as handle:
        return json.load(handle)


def _assert_citation_shape(citation):
    assert citation["tier"] in ALLOWED_TIERS
    assert citation["tier_justification"].strip()
    assert citation.get("doi") or citation.get("canonical_url")
    if citation["tier"] == "Gold":
        assert citation.get("citation_count_approx", 0) >= 100


def _tier_satisfies(citation, minimum_tier_required):
    return TIER_RANK[citation["tier"]] >= TIER_RANK[minimum_tier_required]


def test_parameter_files_exist():
    assert PARAMETER_FILES


def test_parameter_records_have_valid_citations():
    for path in PARAMETER_FILES:
        payload = _load_json(path)
        for parameter in payload.get("parameters", []):
            citations = parameter.get("citations", [])
            assert citations, "{} missing citations".format(parameter["parameter_name"])
            for citation in citations:
                _assert_citation_shape(citation)
            minimum = parameter["minimum_tier_required"]
            assert any(_tier_satisfies(citation, minimum) for citation in citations)
            assert parameter.get("tier_satisfied") is True


def test_ground_truth_decision_points_have_citations():
    assert GROUND_TRUTH_FILES
    for path in GROUND_TRUTH_FILES:
        payload = _load_json(path)
        for decision_point in payload.get("decision_points", []):
            citations = decision_point.get("citations", [])
            assert citations, "{} missing citations".format(decision_point["id"])
            for citation in citations:
                _assert_citation_shape(citation)
            minimum = decision_point["minimum_tier_required"]
            assert any(_tier_satisfies(citation, minimum) for citation in citations)


def test_failure_maps_have_citations():
    for path in GROUND_TRUTH_FILES:
        payload = _load_json(path)
        for failure_id, failure_item in payload.get("failure_diagnosis_map", {}).items():
            citations = failure_item.get("citations", [])
            assert citations, "{} missing citations".format(failure_id)
            for citation in citations:
                _assert_citation_shape(citation)


def test_sources_file_documents_rejected_sources():
    for task_dir in sorted((ROOT / "task_data").glob("*")):
        sources_path = task_dir / "SOURCES.md"
        assert sources_path.exists()
        content = sources_path.read_text()
        assert "Rejected Sources" in content
