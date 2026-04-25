"""Tests for rubric loading and scoring."""
from pathlib import Path

import pytest

from src.rubric_utils import (
    ProtocolRubric,
    RubricNode,
    get_leaf_nodes,
    compute_weighted_score,
    compute_category_scores,
    rubric_to_judge_context,
)

TASK_DATA_DIR = Path(__file__).parent.parent / "task_data"


class TestRubricNode:
    def test_from_dict_leaf(self):
        data = {
            "name": "Test leaf",
            "weight": 1.0,
            "is_leaf": True,
            "requirement": "Test requirement",
            "grading_notes": "Test notes",
            "category": "detection",
        }
        node = RubricNode.from_dict(data)
        assert node.name == "Test leaf"
        assert node.is_leaf is True
        assert node.category == "detection"
        assert node.children == []

    def test_from_dict_internal(self):
        data = {
            "name": "Parent",
            "weight": 1.0,
            "is_leaf": False,
            "children": [
                {"name": "Child 1", "weight": 0.5, "is_leaf": True, "category": "detection"},
                {"name": "Child 2", "weight": 0.5, "is_leaf": True, "category": "explanation"},
            ],
        }
        node = RubricNode.from_dict(data)
        assert len(node.children) == 2
        assert node.children[0].name == "Child 1"


class TestProtocolRubric:
    def test_load_transform_rubric(self):
        rubric_path = TASK_DATA_DIR / "transform_01" / "rubric.json"
        rubric = ProtocolRubric.from_file(rubric_path)
        assert rubric.protocol_id == "transform_01"
        assert rubric.total_leaf_nodes == 9

    def test_leaf_count_matches_metadata(self):
        rubric_path = TASK_DATA_DIR / "transform_01" / "rubric.json"
        rubric = ProtocolRubric.from_file(rubric_path)
        leaves = get_leaf_nodes(rubric.root)
        assert len(leaves) == rubric.total_leaf_nodes


class TestScoring:
    def _make_tree(self):
        """Create a simple rubric tree for testing."""
        return RubricNode(
            name="Root",
            weight=1.0,
            is_leaf=False,
            children=[
                RubricNode(
                    name="Detection",
                    weight=0.4,
                    is_leaf=False,
                    children=[
                        RubricNode(name="D1", weight=0.5, is_leaf=True, category="detection"),
                        RubricNode(name="D2", weight=0.5, is_leaf=True, category="detection"),
                    ],
                ),
                RubricNode(
                    name="Explanation",
                    weight=0.3,
                    is_leaf=False,
                    children=[
                        RubricNode(name="E1", weight=0.5, is_leaf=True, category="explanation"),
                        RubricNode(name="E2", weight=0.5, is_leaf=True, category="explanation"),
                    ],
                ),
                RubricNode(
                    name="Correction",
                    weight=0.3,
                    is_leaf=False,
                    children=[
                        RubricNode(name="C1", weight=0.5, is_leaf=True, category="correction"),
                        RubricNode(name="C2", weight=0.5, is_leaf=True, category="correction"),
                    ],
                ),
            ],
        )

    def test_all_pass(self):
        tree = self._make_tree()
        for leaf in get_leaf_nodes(tree):
            leaf.score = 1.0
        assert compute_weighted_score(tree) == 1.0

    def test_all_fail(self):
        tree = self._make_tree()
        for leaf in get_leaf_nodes(tree):
            leaf.score = 0.0
        assert compute_weighted_score(tree) == 0.0

    def test_detection_only_pass(self):
        tree = self._make_tree()
        leaves = get_leaf_nodes(tree)
        for leaf in leaves:
            leaf.score = 1.0 if leaf.category == "detection" else 0.0
        score = compute_weighted_score(tree)
        # Detection has weight 0.4 out of total 1.0
        assert abs(score - 0.4) < 0.001

    def test_category_scores(self):
        tree = self._make_tree()
        leaves = get_leaf_nodes(tree)
        for leaf in leaves:
            if leaf.category == "detection":
                leaf.score = 1.0
            elif leaf.category == "explanation":
                leaf.score = 0.5
            else:
                leaf.score = 0.0

        cats = compute_category_scores(tree)
        assert cats["detection"] == 1.0
        assert cats["explanation"] == 0.5
        assert cats["correction"] == 0.0

    def test_no_score_raises(self):
        tree = self._make_tree()
        with pytest.raises(ValueError, match="no score set"):
            compute_weighted_score(tree)


class TestJudgeContext:
    def test_rubric_to_judge_context(self):
        rubric_path = TASK_DATA_DIR / "transform_01" / "rubric.json"
        rubric = ProtocolRubric.from_file(rubric_path)
        items = rubric_to_judge_context(rubric)
        assert len(items) == 9
        assert all("leaf_name" in item for item in items)
        assert all("requirement" in item for item in items)
        categories = {item["category"] for item in items}
        assert categories == {"task_success", "decision_quality", "troubleshooting", "efficiency"}
