"""LabCraft task definitions."""

from .base import TaskPaths
from .clone_01 import CLONE_01_GROUND_TRUTH, CLONE_01_RUBRIC, build_clone_01_sample
from .golden_gate_01 import (
    GOLDEN_GATE_01_GROUND_TRUTH,
    GOLDEN_GATE_01_RUBRIC,
    build_golden_gate_01_sample,
)
from .growth_01 import GROWTH_01_GROUND_TRUTH, GROWTH_01_RUBRIC, build_growth_01_sample
from .pcr_01 import PCR_01_GROUND_TRUTH, PCR_01_RUBRIC, build_pcr_01_sample
from .screen_01 import SCREEN_01_GROUND_TRUTH, SCREEN_01_RUBRIC, build_screen_01_sample
from .transform_01 import (
    TRANSFORM_01_GROUND_TRUTH,
    TRANSFORM_01_RUBRIC,
    build_transform_01_sample,
)

__all__ = [
    "TaskPaths",
    "CLONE_01_GROUND_TRUTH",
    "CLONE_01_RUBRIC",
    "build_clone_01_sample",
    "GOLDEN_GATE_01_GROUND_TRUTH",
    "GOLDEN_GATE_01_RUBRIC",
    "build_golden_gate_01_sample",
    "GROWTH_01_GROUND_TRUTH",
    "GROWTH_01_RUBRIC",
    "build_growth_01_sample",
    "PCR_01_GROUND_TRUTH",
    "PCR_01_RUBRIC",
    "build_pcr_01_sample",
    "SCREEN_01_GROUND_TRUTH",
    "SCREEN_01_RUBRIC",
    "build_screen_01_sample",
    "TRANSFORM_01_GROUND_TRUTH",
    "TRANSFORM_01_RUBRIC",
    "build_transform_01_sample",
]
