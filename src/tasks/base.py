"""Shared path helpers for LabCraft tasks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TaskPaths:
    task_id: str
    root: Path

    @property
    def ground_truth(self) -> Path:
        return self.root / "ground_truth.json"

    @property
    def rubric(self) -> Path:
        return self.root / "rubric.json"

    @property
    def sources(self) -> Path:
        return self.root / "SOURCES.md"
