"""Utilities for loading and scoring hierarchical rubric trees."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class RubricNode:
    """A single node in a hierarchical rubric tree."""

    name: str
    weight: float
    is_leaf: bool
    category: str | None = None
    requirement: str | None = None
    grading_notes: str | None = None
    children: list[RubricNode] = field(default_factory=list)
    score: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RubricNode:
        children = [cls.from_dict(c) for c in data.get("children", [])]
        return cls(
            name=data["name"],
            weight=data["weight"],
            is_leaf=data["is_leaf"],
            category=data.get("category"),
            requirement=data.get("requirement"),
            grading_notes=data.get("grading_notes"),
            children=children,
        )


@dataclass
class ProtocolRubric:
    """Full rubric for a task, including metadata."""

    protocol_id: str
    protocol_title: str
    source: str
    num_errors_introduced: int
    total_leaf_nodes: int
    root: RubricNode

    @classmethod
    def from_file(cls, path: str | Path) -> ProtocolRubric:
        with open(path) as f:
            data = json.load(f)
        return cls(
            protocol_id=data.get("protocol_id", data.get("task_id", "")),
            protocol_title=data.get("protocol_title", data.get("task_title", "")),
            source=data.get("source", ""),
            num_errors_introduced=data.get("num_errors_introduced", 0),
            total_leaf_nodes=data["total_leaf_nodes"],
            root=RubricNode.from_dict(data["rubric"]),
        )


def get_leaf_nodes(node: RubricNode) -> list[RubricNode]:
    """Collect all leaf nodes from the rubric tree."""
    if node.is_leaf:
        return [node]
    leaves = []
    for child in node.children:
        leaves.extend(get_leaf_nodes(child))
    return leaves


def compute_weighted_score(node: RubricNode) -> float:
    """Compute the weighted score for a node, recursively.

    Leaf nodes must have their score set before calling this.
    Uses the PaperBench formula: S_P = sum(w_j * s_j) / sum(w_j)
    """
    if node.is_leaf:
        if node.score is None:
            raise ValueError(f"Leaf node '{node.name}' has no score set")
        return node.score

    total_weight = sum(c.weight for c in node.children)
    if total_weight == 0:
        return 0.0

    weighted_sum = sum(c.weight * compute_weighted_score(c) for c in node.children)
    node.score = weighted_sum / total_weight
    return node.score


def compute_category_scores(node: RubricNode) -> dict[str, float]:
    """Compute average scores per category."""
    leaves = get_leaf_nodes(node)
    categories: dict[str, list[float]] = {}
    for leaf in leaves:
        if leaf.score is not None and leaf.category:
            categories.setdefault(leaf.category, []).append(leaf.score)

    return {
        cat: sum(scores) / len(scores) for cat, scores in categories.items() if scores
    }


def rubric_to_judge_context(rubric: ProtocolRubric) -> list[dict[str, str]]:
    """Convert rubric leaf nodes to a list of judge evaluation items."""
    leaves = get_leaf_nodes(rubric.root)
    return [
        {
            "leaf_name": leaf.name,
            "category": leaf.category or "unknown",
            "requirement": leaf.requirement or "",
            "grading_notes": leaf.grading_notes or "",
        }
        for leaf in leaves
    ]
