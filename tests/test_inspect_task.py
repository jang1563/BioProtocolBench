from src.inspect_task import _expand_seeds
import src.inspect_task as inspect_task
from src.tasks.target_prioritize_01 import build_target_prioritize_01_prompt


def test_expand_seeds_defaults_to_zero_start():
    base_sample = {
        "id": "purify_01_seeded",
        "input": "prompt",
        "target": "target",
        "metadata": {"task_id": "purify_01"},
    }

    expanded = _expand_seeds(base_sample, seeds=3)

    assert [sample["id"] for sample in expanded] == [
        "purify_01_seeded_seed_00",
        "purify_01_seeded_seed_01",
        "purify_01_seeded_seed_02",
    ]
    assert [sample["metadata"]["seed_index"] for sample in expanded] == [0, 1, 2]


def test_expand_seeds_supports_nonzero_seed_start():
    base_sample = {
        "id": "purify_01_seeded",
        "input": "prompt",
        "target": "target",
        "metadata": {"task_id": "purify_01"},
    }

    expanded = _expand_seeds(base_sample, seeds=2, seed_start=3)

    assert [sample["id"] for sample in expanded] == [
        "purify_01_seeded_seed_03",
        "purify_01_seeded_seed_04",
    ]
    assert [sample["metadata"]["seed_index"] for sample in expanded] == [3, 4]


def test_expand_single_seed_with_nonzero_seed_start_gets_suffix():
    base_sample = {
        "id": "purify_01_seeded",
        "input": "prompt",
        "target": "target",
        "metadata": {"task_id": "purify_01"},
    }

    expanded = _expand_seeds(base_sample, seeds=1, seed_start=4)

    assert len(expanded) == 1
    assert expanded[0]["id"] == "purify_01_seeded_seed_04"
    assert expanded[0]["metadata"]["seed_index"] == 4


def test_discovery_tasks_are_registered():
    assert "perturb_followup_01" in inspect_task.__all__
    assert "target_prioritize_01" in inspect_task.__all__
    assert "target_validate_01" in inspect_task.__all__


def test_target_prioritize_prompt_clarifies_immediate_no_go_vs_followup():
    prompt = build_target_prioritize_01_prompt()

    assert "clearest immediate no-go" in prompt
    assert "better handled by follow-up" in prompt
    assert "remaining risk for the top target" in prompt
