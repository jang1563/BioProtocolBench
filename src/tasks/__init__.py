"""LabCraft task definitions."""

from .base import TaskPaths
from .clone_01 import CLONE_01_GROUND_TRUTH, CLONE_01_RUBRIC, build_clone_01_sample
from .express_01 import (
    EXPRESS_01_GROUND_TRUTH,
    EXPRESS_01_RUBRIC,
    build_express_01_sample,
)
from .followup_01 import (
    FOLLOWUP_01_GROUND_TRUTH,
    FOLLOWUP_01_RUBRIC,
    build_followup_01_sample,
)
from .gibson_01 import GIBSON_01_GROUND_TRUTH, GIBSON_01_RUBRIC, build_gibson_01_sample
from .golden_gate_01 import (
    GOLDEN_GATE_01_GROUND_TRUTH,
    GOLDEN_GATE_01_RUBRIC,
    build_golden_gate_01_sample,
)
from .miniprep_01 import (
    MINIPREP_01_GROUND_TRUTH,
    MINIPREP_01_RUBRIC,
    build_miniprep_01_sample,
)
from .purify_01 import PURIFY_01_GROUND_TRUTH, PURIFY_01_RUBRIC, build_purify_01_sample
from .growth_01 import GROWTH_01_GROUND_TRUTH, GROWTH_01_RUBRIC, build_growth_01_sample
from .pcr_01 import PCR_01_GROUND_TRUTH, PCR_01_RUBRIC, build_pcr_01_sample
from .screen_01 import SCREEN_01_GROUND_TRUTH, SCREEN_01_RUBRIC, build_screen_01_sample
from .perturb_followup_01 import (
    PERTURB_FOLLOWUP_01_GROUND_TRUTH,
    PERTURB_FOLLOWUP_01_RUBRIC,
    build_perturb_followup_01_sample,
)
from .target_prioritize_01 import (
    TARGET_PRIORITIZE_01_GROUND_TRUTH,
    TARGET_PRIORITIZE_01_RUBRIC,
    build_target_prioritize_01_sample,
)
from .target_validate_01 import (
    TARGET_VALIDATE_01_GROUND_TRUTH,
    TARGET_VALIDATE_01_RUBRIC,
    build_target_validate_01_sample,
)
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
    "EXPRESS_01_GROUND_TRUTH",
    "EXPRESS_01_RUBRIC",
    "build_express_01_sample",
    "FOLLOWUP_01_GROUND_TRUTH",
    "FOLLOWUP_01_RUBRIC",
    "build_followup_01_sample",
    "PERTURB_FOLLOWUP_01_GROUND_TRUTH",
    "PERTURB_FOLLOWUP_01_RUBRIC",
    "build_perturb_followup_01_sample",
    "GIBSON_01_GROUND_TRUTH",
    "GIBSON_01_RUBRIC",
    "build_gibson_01_sample",
    "GOLDEN_GATE_01_GROUND_TRUTH",
    "GOLDEN_GATE_01_RUBRIC",
    "build_golden_gate_01_sample",
    "MINIPREP_01_GROUND_TRUTH",
    "MINIPREP_01_RUBRIC",
    "build_miniprep_01_sample",
    "PURIFY_01_GROUND_TRUTH",
    "PURIFY_01_RUBRIC",
    "build_purify_01_sample",
    "GROWTH_01_GROUND_TRUTH",
    "GROWTH_01_RUBRIC",
    "build_growth_01_sample",
    "PCR_01_GROUND_TRUTH",
    "PCR_01_RUBRIC",
    "build_pcr_01_sample",
    "SCREEN_01_GROUND_TRUTH",
    "SCREEN_01_RUBRIC",
    "build_screen_01_sample",
    "TARGET_PRIORITIZE_01_GROUND_TRUTH",
    "TARGET_PRIORITIZE_01_RUBRIC",
    "build_target_prioritize_01_sample",
    "TARGET_VALIDATE_01_GROUND_TRUTH",
    "TARGET_VALIDATE_01_RUBRIC",
    "build_target_validate_01_sample",
    "TRANSFORM_01_GROUND_TRUTH",
    "TRANSFORM_01_RUBRIC",
    "build_transform_01_sample",
]
