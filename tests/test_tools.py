"""Tests for agent tools."""

import json

import pytest

from src.tools.reference import _search_database, _DATA_DIR


class TestSearchDatabase:
    def test_search_reagent_by_name(self):
        db_path = _DATA_DIR / "reagent_database.json"
        if not db_path.exists():
            pytest.skip("Reagent database not available")
        results = _search_database(db_path, "Tris")
        assert len(results) > 0
        names = [r["name"] for r in results]
        assert any("Tris" in name for name in names)

    def test_search_enzyme_by_name(self):
        db_path = _DATA_DIR / "enzyme_database.json"
        if not db_path.exists():
            pytest.skip("Enzyme database not available")
        results = _search_database(db_path, "EcoRI")
        assert len(results) > 0
        assert results[0]["name"] == "EcoRI"

    def test_search_safety_by_name(self):
        db_path = _DATA_DIR / "safety_database.json"
        if not db_path.exists():
            pytest.skip("Safety database not available")
        results = _search_database(db_path, "phenol")
        assert len(results) > 0

    def test_no_results(self):
        db_path = _DATA_DIR / "reagent_database.json"
        if not db_path.exists():
            pytest.skip("Reagent database not available")
        results = _search_database(db_path, "nonexistent_xyz_reagent_12345")
        assert len(results) == 0

    def test_case_insensitive(self):
        db_path = _DATA_DIR / "enzyme_database.json"
        if not db_path.exists():
            pytest.skip("Enzyme database not available")
        results_upper = _search_database(db_path, "ECORI")
        results_lower = _search_database(db_path, "ecori")
        assert len(results_upper) == len(results_lower)


class TestDatabaseContent:
    def test_reagent_database_not_empty(self):
        db_path = _DATA_DIR / "reagent_database.json"
        if not db_path.exists():
            pytest.skip("Reagent database not available")
        with open(db_path) as f:
            data = json.load(f)
        assert len(data) >= 50

    def test_enzyme_database_not_empty(self):
        db_path = _DATA_DIR / "enzyme_database.json"
        if not db_path.exists():
            pytest.skip("Enzyme database not available")
        with open(db_path) as f:
            data = json.load(f)
        assert len(data) >= 30

    def test_safety_database_not_empty(self):
        db_path = _DATA_DIR / "safety_database.json"
        if not db_path.exists():
            pytest.skip("Safety database not available")
        with open(db_path) as f:
            data = json.load(f)
        assert len(data) >= 30

    def test_enzyme_has_required_fields(self):
        db_path = _DATA_DIR / "enzyme_database.json"
        if not db_path.exists():
            pytest.skip("Enzyme database not available")
        with open(db_path) as f:
            data = json.load(f)
        for entry in data:
            assert "name" in entry
            assert "optimal_temperature_c" in entry or "optimal_temperature" in entry

    def test_t4_ligase_temperature(self):
        """T4 DNA Ligase optimal temp should be 16°C (or 25°C for quick ligation)."""
        db_path = _DATA_DIR / "enzyme_database.json"
        if not db_path.exists():
            pytest.skip("Enzyme database not available")
        results = _search_database(db_path, "T4 DNA Ligase")
        assert len(results) > 0
        temp = results[0].get("optimal_temperature_c", results[0].get("optimal_temperature"))
        assert temp in [16, 25, "16", "25"]
