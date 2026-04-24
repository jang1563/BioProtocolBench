import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script_module(module_name: str, relative_path: str):
    script_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


human_baseline = _load_script_module(
    "run_human_baseline_for_pilot_tests",
    "scripts/run_human_baseline.py",
)
human_baseline_pilot = _load_script_module(
    "run_human_baseline_pilot",
    "scripts/run_human_baseline_pilot.py",
)


def test_load_seed_plan_preserves_manifest_order(tmp_path):
    seed_plan_path = tmp_path / "seed_plan.json"
    seed_plan_path.write_text(
        json.dumps(
            {
                "pilot_entries": [
                    {"task_id": "transform_01", "seed_index": 4},
                    {"task_id": "growth_01", "seed_index": 1},
                ]
            }
        )
    )

    rows = human_baseline_pilot.load_seed_plan(seed_plan_path)

    assert rows == [
        {"task_id": "transform_01", "seed_index": 4, "selection_rationale": ""},
        {"task_id": "growth_01", "seed_index": 1, "selection_rationale": ""},
    ]


def test_build_plan_rows_reads_saved_statuses(tmp_path):
    plan_entries = [
        {"task_id": "transform_01", "seed_index": 0, "selection_rationale": ""},
        {"task_id": "growth_01", "seed_index": 2, "selection_rationale": ""},
    ]
    first_path = tmp_path / "expert_a__transform_01_seed_00.json"
    first_path.write_text(json.dumps({"status": "completed"}))
    second_path = tmp_path / "expert_a__growth_01_seed_02.json"
    second_path.write_text(json.dumps({"status": "in_progress"}))

    rows = human_baseline_pilot.build_plan_rows(
        plan_entries,
        operator_id="expert_a",
        session_dir=tmp_path,
        baseline_module=human_baseline,
    )

    assert [row["status"] for row in rows] == ["completed", "in_progress"]


def test_select_plan_rows_prefers_in_progress_then_pending():
    rows = [
        {"task_id": "transform_01", "seed_index": 0, "status": "completed"},
        {"task_id": "transform_01", "seed_index": 2, "status": "in_progress"},
        {"task_id": "growth_01", "seed_index": 1, "status": "pending"},
    ]

    selected = human_baseline_pilot.select_plan_rows(rows, run_all=False)

    assert selected == [rows[1]]


def test_select_plan_rows_run_all_skips_completed_by_default():
    rows = [
        {"task_id": "transform_01", "seed_index": 0, "status": "completed"},
        {"task_id": "transform_01", "seed_index": 2, "status": "in_progress"},
        {"task_id": "growth_01", "seed_index": 1, "status": "pending"},
    ]

    selected = human_baseline_pilot.select_plan_rows(rows, run_all=True)

    assert selected == [rows[1], rows[2]]


def test_build_plan_rows_uses_growth_prompt_variant_in_session_path(tmp_path):
    plan_entries = [
        {"task_id": "growth_01", "seed_index": 2, "selection_rationale": ""},
    ]

    rows = human_baseline_pilot.build_plan_rows(
        plan_entries,
        operator_id="expert_a",
        session_dir=tmp_path,
        baseline_module=human_baseline,
        growth_prompt_variant="verbose_troubleshoot",
    )

    assert rows[0]["prompt_variant"] == "verbose_troubleshoot"
    assert rows[0]["session_path"].name == "expert_a__growth_01__verbose_troubleshoot_seed_02.json"
