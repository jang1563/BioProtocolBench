"""Inspect AI task entry points for LabCraft.

Phase 1 begins with Transform-01.
"""

from __future__ import annotations

try:
    from inspect_ai import Task, task
    from inspect_ai.dataset import MemoryDataset, Sample
except ImportError:  # pragma: no cover - keeps local imports working before Inspect is installed.
    Task = None
    MemoryDataset = None
    Sample = None

    def task(func):
        return func

from src.solvers import (
    build_clone_solver,
    build_growth_solver,
    build_labcraft_solver,
    build_pcr_solver,
    build_screen_solver,
    configure_clone_sample,
    configure_growth_sample,
    configure_pcr_sample,
    configure_screen_sample,
    configure_transform_sample,
)
from src.tasks.clone_01 import build_clone_01_sample
from src.tasks.growth_01 import build_growth_01_sample
from src.tasks.pcr_01 import build_pcr_01_sample
from src.tasks.screen_01 import build_screen_01_sample
from src.tasks.transform_01 import build_transform_01_sample
from src.tools.lab_tools import cleanup_sample
from src.trajectory_scorer import (
    build_clone_trajectory_scorer,
    build_growth_trajectory_scorer,
    build_pcr_trajectory_scorer,
    build_screen_trajectory_scorer,
    build_transform_trajectory_scorer,
)


async def _cleanup_transform_sample(state):
    cleanup_sample(state.sample_id)


@task
def transform_01():
    if Task is None or MemoryDataset is None or Sample is None:
        raise ImportError("inspect_ai is required to instantiate LabCraft tasks.")
    sample = build_transform_01_sample()
    return Task(
        dataset=MemoryDataset(
            samples=[
                Sample(
                    input=sample["input"],
                    target=sample["target"],
                    id=sample["id"],
                    metadata=sample["metadata"],
                )
            ]
        ),
        setup=configure_transform_sample(),
        solver=build_labcraft_solver(),
        scorer=build_transform_trajectory_scorer(),
        cleanup=_cleanup_transform_sample,
        message_limit=40,
    )


@task
def growth_01():
    if Task is None or MemoryDataset is None or Sample is None:
        raise ImportError("inspect_ai is required to instantiate LabCraft tasks.")
    sample = build_growth_01_sample()
    return Task(
        dataset=MemoryDataset(
            samples=[
                Sample(
                    input=sample["input"],
                    target=sample["target"],
                    id=sample["id"],
                    metadata=sample["metadata"],
                )
            ]
        ),
        setup=configure_growth_sample(),
        solver=build_growth_solver(),
        scorer=build_growth_trajectory_scorer(),
        cleanup=_cleanup_transform_sample,
        message_limit=80,
    )


@task
def pcr_01():
    if Task is None or MemoryDataset is None or Sample is None:
        raise ImportError("inspect_ai is required to instantiate LabCraft tasks.")
    sample = build_pcr_01_sample()
    return Task(
        dataset=MemoryDataset(
            samples=[
                Sample(
                    input=sample["input"],
                    target=sample["target"],
                    id=sample["id"],
                    metadata=sample["metadata"],
                )
            ]
        ),
        setup=configure_pcr_sample(),
        solver=build_pcr_solver(),
        scorer=build_pcr_trajectory_scorer(),
        cleanup=_cleanup_transform_sample,
        message_limit=60,
    )


@task
def screen_01():
    if Task is None or MemoryDataset is None or Sample is None:
        raise ImportError("inspect_ai is required to instantiate LabCraft tasks.")
    sample = build_screen_01_sample()
    return Task(
        dataset=MemoryDataset(
            samples=[
                Sample(
                    input=sample["input"],
                    target=sample["target"],
                    id=sample["id"],
                    metadata=sample["metadata"],
                )
            ]
        ),
        setup=configure_screen_sample(),
        solver=build_screen_solver(),
        scorer=build_screen_trajectory_scorer(),
        cleanup=_cleanup_transform_sample,
        message_limit=50,
    )


@task
def clone_01():
    if Task is None or MemoryDataset is None or Sample is None:
        raise ImportError("inspect_ai is required to instantiate LabCraft tasks.")
    sample = build_clone_01_sample()
    return Task(
        dataset=MemoryDataset(
            samples=[
                Sample(
                    input=sample["input"],
                    target=sample["target"],
                    id=sample["id"],
                    metadata=sample["metadata"],
                )
            ]
        ),
        setup=configure_clone_sample(),
        solver=build_clone_solver(),
        scorer=build_clone_trajectory_scorer(),
        cleanup=_cleanup_transform_sample,
        message_limit=80,
    )


@task
def labcraft_suite():
    if Task is None:
        raise ImportError("inspect_ai is required to instantiate LabCraft tasks.")
    return transform_01()


__all__ = ["transform_01", "growth_01", "pcr_01", "screen_01", "clone_01", "labcraft_suite"]
