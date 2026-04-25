import importlib.util
import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script_module(module_name: str, relative_path: str):
    script_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


aggregate_human_baseline = _load_script_module(
    "aggregate_human_baseline",
    "scripts/aggregate_human_baseline.py",
)


def test_dedupe_sessions_keeps_latest_completed_copy():
    older = {
        "operator_id": "expert_a",
        "task_id": "transform_01",
        "prompt_variant": "baseline",
        "sample_id": "transform_01_seeded_seed_00",
        "updated_at": "2026-04-16T20:00:00+00:00",
    }
    newer = {
        "operator_id": "expert_a",
        "task_id": "transform_01",
        "prompt_variant": "baseline",
        "sample_id": "transform_01_seeded_seed_00",
        "updated_at": "2026-04-16T21:00:00+00:00",
    }
    distinct = {
        "operator_id": "expert_a",
        "task_id": "growth_01",
        "prompt_variant": "baseline",
        "sample_id": "growth_01_seeded_seed_00",
        "updated_at": "2026-04-16T21:30:00+00:00",
    }

    deduped = aggregate_human_baseline.dedupe_sessions([older, newer, distinct])

    assert len(deduped) == 2
    rows_by_key = {(row["operator_id"], row["task_id"], row["sample_id"]): row for row in deduped}
    assert rows_by_key[("expert_a", "transform_01", "transform_01_seeded_seed_00")]["updated_at"] == newer["updated_at"]


def test_dedupe_sessions_keeps_distinct_prompt_variants():
    baseline = {
        "operator_id": "expert_a",
        "task_id": "growth_01",
        "prompt_variant": "baseline",
        "sample_id": "growth_01_seeded_seed_02",
        "updated_at": "2026-04-16T20:00:00+00:00",
    }
    verbose = {
        "operator_id": "expert_a",
        "task_id": "growth_01",
        "prompt_variant": "verbose_troubleshoot",
        "sample_id": "growth_01_seeded_seed_02",
        "updated_at": "2026-04-16T21:00:00+00:00",
    }

    deduped = aggregate_human_baseline.dedupe_sessions([baseline, verbose])

    assert len(deduped) == 2


def test_dedupe_sessions_treats_invalid_timestamp_as_older_than_valid_iso():
    invalid = {
        "operator_id": "expert_a",
        "task_id": "transform_01",
        "prompt_variant": "baseline",
        "sample_id": "transform_01_seeded_seed_00",
        "updated_at": "not-a-time",
        "overall": 0.1,
    }
    valid = {
        "operator_id": "expert_a",
        "task_id": "transform_01",
        "prompt_variant": "baseline",
        "sample_id": "transform_01_seeded_seed_00",
        "updated_at": "2026-04-17T12:00:00+00:00",
        "overall": 0.9,
    }

    deduped = aggregate_human_baseline.dedupe_sessions([invalid, valid])

    assert len(deduped) == 1
    assert deduped[0]["updated_at"] == valid["updated_at"]


def test_aggregate_human_baseline_writes_placeholder_when_no_sessions(tmp_path):
    session_dir = tmp_path / "sessions"
    out_path = tmp_path / "human_baseline_pilot.md"
    json_out_path = tmp_path / "human_baseline_pilot.json"
    snapshot_results = tmp_path / "results.md"
    snapshot_results.write_text(
        "\n".join(
            [
                "# Results",
                "",
                "## Per-sample detail",
                "",
                "| Model | Task | Sample | overall | task | decision | trouble | efficiency |",
                "|---|---|---|---:|---:|---:|---:|---:|",
                "| openai/gpt-4o-mini | `transform_01` | `transform_01_seeded_seed_00` | 0.600 | 0.000 | 1.000 | 1.000 | 1.000 |",
                "| anthropic/claude-sonnet-4-5 | `transform_01` | `transform_01_seeded_seed_00` | 0.800 | 1.000 | 0.667 | 1.000 | 0.000 |",
            ]
        )
    )

    rc = aggregate_human_baseline.main(
        [
            "--session-dir",
            str(session_dir),
            "--out",
            str(out_path),
            "--json-out",
            str(json_out_path),
            "--snapshot-results",
            str(snapshot_results),
        ]
    )

    assert rc == 0
    text = out_path.read_text()
    assert "No completed human baseline sessions have been checked in yet." in text
    assert "human_baseline_seed_plan.md" in text
    assert "Planned coverage" in text
    assert "Prompt split" in text
    assert "0.600-0.800" in text
    assert "python3 scripts/aggregate_human_baseline.py" in text
    payload = json.loads(json_out_path.read_text())
    assert payload["completed_session_count"] == 0
    assert payload["has_completed_sessions"] is False
    assert len(payload["coverage"]) == 6


def test_load_completed_sessions_reads_operator_and_scores(tmp_path):
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    session_path = session_dir / "transform_01_seed_00.json"
    session_path.write_text(
        json.dumps(
            {
                "task_id": "transform_01",
                "seed_index": 0,
                "sample_id": "transform_01_seeded_seed_00",
                "operator_id": "expert_a",
                "prompt_variant": "baseline",
                "status": "completed",
                "updated_at": "2026-04-16T22:00:00+00:00",
                "score": {
                    "overall": 0.95,
                    "task_success": 1.0,
                    "decision_quality": 1.0,
                    "troubleshooting": 1.0,
                    "efficiency": 0.5,
                },
            }
        )
    )

    rows = aggregate_human_baseline.load_completed_sessions(session_dir)

    assert len(rows) == 1
    assert rows[0]["operator_id"] == "expert_a"
    assert rows[0]["overall"] == 0.95


def test_load_completed_sessions_rescores_supported_tasks(tmp_path):
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    session_path = session_dir / "transform_01_seed_00.json"
    session_path.write_text(
        json.dumps(
            {
                "task_id": "transform_01",
                "seed_index": 0,
                "sample_id": "transform_01_seeded_seed_00",
                "operator_id": "expert_a",
                "prompt_variant": "baseline",
                "status": "completed",
                "updated_at": "2026-04-16T22:00:00+00:00",
                "ground_truth_path": str(REPO_ROOT / "task_data" / "transform_01" / "ground_truth.json"),
                "transcript": [],
                "final_answer": "10 pg: 1e9 CFU/ug\n100 pg: 1e9 CFU/ug\n1,000 pg: 1e9 CFU/ug\n10,000 pg: 1e9 CFU/ug\nInterpretation: consistent",
                "score": {
                    "overall": 1.0,
                    "task_success": 1.0,
                    "decision_quality": 1.0,
                    "troubleshooting": 1.0,
                    "efficiency": 1.0,
                },
            }
        )
    )

    rows = aggregate_human_baseline.load_completed_sessions(session_dir)

    assert len(rows) == 1
    assert rows[0]["score_source"] == "rescored"
    assert rows[0]["overall"] == pytest.approx(0.0)


def test_load_completed_sessions_falls_back_to_stored_score_when_ground_truth_path_is_stale(tmp_path):
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    session_path = session_dir / "transform_01_seed_00.json"
    session_path.write_text(
        json.dumps(
            {
                "task_id": "transform_01",
                "seed_index": 0,
                "sample_id": "transform_01_seeded_seed_00",
                "operator_id": "expert_a",
                "prompt_variant": "baseline",
                "status": "completed",
                "updated_at": "2026-04-16T22:00:00+00:00",
                "ground_truth_path": "/stale/clone/task_data/transform_01/ground_truth.json",
                "transcript": [],
                "final_answer": "10 pg: 1e9 CFU/ug\n100 pg: 1e9 CFU/ug\n1,000 pg: 1e9 CFU/ug\n10,000 pg: 1e9 CFU/ug\nInterpretation: consistent",
                "score": {
                    "overall": 0.95,
                    "task_success": 1.0,
                    "decision_quality": 1.0,
                    "troubleshooting": 1.0,
                    "efficiency": 0.5,
                },
            }
        )
    )

    rows = aggregate_human_baseline.load_completed_sessions(session_dir)

    assert len(rows) == 1
    assert rows[0]["score_source"] == "rescored"
    assert rows[0]["overall"] == pytest.approx(0.0)


def test_load_snapshot_sample_scores_parses_per_sample_markdown(tmp_path):
    results_path = tmp_path / "results.md"
    results_path.write_text(
        "\n".join(
            [
                "# Results",
                "",
                "## Per-sample detail",
                "",
                "| Model | Task | Sample | overall | task | decision | trouble | efficiency |",
                "|---|---|---|---:|---:|---:|---:|---:|",
                "| openai/gpt-4o-mini | `growth_01` | `growth_01_seeded_seed_03` | 0.700 | 1.000 | 0.667 | 0.000 | 1.000 |",
                "| anthropic/claude-sonnet-4-5 | `growth_01` | `growth_01_seeded_seed_03` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |",
            ]
        )
    )

    rows = aggregate_human_baseline.load_snapshot_sample_scores(results_path)

    assert rows[("growth_01", "growth_01_seeded_seed_03")]["openai/gpt-4o-mini"]["overall"] == 0.7
    assert rows[("growth_01", "growth_01_seeded_seed_03")]["anthropic/claude-sonnet-4-5"]["efficiency"] == 1.0


def test_load_seed_plan_reads_json_manifest(tmp_path):
    seed_plan_path = tmp_path / "human_baseline_seed_plan.json"
    seed_plan_path.write_text(
        json.dumps(
            {
                "pilot_entries": [
                    {"task_id": "growth_01", "seed_index": 3},
                    {"task_id": "transform_01", "seed_index": 2},
                ]
            }
        )
    )

    plan = aggregate_human_baseline.load_seed_plan(seed_plan_path)

    assert plan == [
        {"task_id": "growth_01", "seed_index": 3},
        {"task_id": "transform_01", "seed_index": 2},
    ]


def test_build_pilot_coverage_marks_completed_seed_and_snapshot_best():
    human_rows = [
        {
            "task_id": "transform_01",
            "seed_index": 2,
            "sample_id": "transform_01_seeded_seed_02",
            "operator_id": "expert_a",
        }
    ]
    snapshot_scores = {
        ("transform_01", "transform_01_seeded_seed_02"): {
            "openai/gpt-4o-mini": {"overall": 0.5},
            "anthropic/claude-haiku-4-5": {"overall": 0.85},
        }
    }
    seed_plan = [{"task_id": "transform_01", "seed_index": 2}]

    coverage = aggregate_human_baseline.build_pilot_coverage(
        human_rows,
        snapshot_scores,
        seed_plan,
    )
    row = next(
        entry
        for entry in coverage
        if entry["task_id"] == "transform_01" and entry["seed_index"] == 2
    )

    assert row["human_sessions"] == 1
    assert row["operators"] == "expert_a"
    assert row["prompt_breakdown_display"] == "baseline: 1"
    assert row["snapshot_range_display"] == "0.500-0.850"
    assert row["snapshot_best_model"] == "claude-haiku-4-5"


def test_build_pilot_coverage_reports_prompt_variant_breakdown():
    human_rows = [
        {
            "task_id": "growth_01",
            "seed_index": 2,
            "sample_id": "growth_01_seeded_seed_02",
            "operator_id": "expert_a",
            "prompt_variant": "baseline",
        },
        {
            "task_id": "growth_01",
            "seed_index": 2,
            "sample_id": "growth_01_seeded_seed_02",
            "operator_id": "expert_b",
            "prompt_variant": "verbose_troubleshoot",
        },
    ]

    coverage = aggregate_human_baseline.build_pilot_coverage(
        human_rows,
        snapshot_scores={},
        seed_plan=[{"task_id": "growth_01", "seed_index": 2}],
    )

    assert coverage[0]["human_sessions"] == 2
    assert coverage[0]["prompt_breakdown_display"] == "baseline: 1; verbose_troubleshoot: 1"
    assert coverage[0]["human_sessions_by_prompt"] == {
        "baseline": 1,
        "verbose_troubleshoot": 1,
    }


def test_aggregate_human_baseline_main_writes_json_for_completed_sessions(tmp_path):
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    out_path = tmp_path / "human_baseline_pilot.md"
    json_out_path = tmp_path / "human_baseline_pilot.json"
    snapshot_results = tmp_path / "results.md"
    snapshot_results.write_text(
        "\n".join(
            [
                "# Results",
                "",
                "## Per-sample detail",
                "",
                "| Model | Task | Sample | overall | task | decision | trouble | efficiency |",
                "|---|---|---|---:|---:|---:|---:|---:|",
                "| openai/gpt-4o-mini | `transform_01` | `transform_01_seeded_seed_00` | 0.600 | 0.000 | 1.000 | 1.000 | 1.000 |",
            ]
        )
    )
    (session_dir / "transform_01_seed_00.json").write_text(
        json.dumps(
            {
                "task_id": "transform_01",
                "seed_index": 0,
                "sample_id": "transform_01_seeded_seed_00",
                "operator_id": "expert_a",
                "prompt_variant": "baseline",
                "status": "completed",
                "updated_at": "2026-04-16T22:00:00+00:00",
                "score": {
                    "overall": 0.95,
                    "task_success": 1.0,
                    "decision_quality": 1.0,
                    "troubleshooting": 1.0,
                    "efficiency": 0.5,
                },
            }
        )
    )

    rc = aggregate_human_baseline.main(
        [
            "--session-dir",
            str(session_dir),
            "--out",
            str(out_path),
            "--json-out",
            str(json_out_path),
            "--snapshot-results",
            str(snapshot_results),
        ]
    )

    assert rc == 0
    payload = json.loads(json_out_path.read_text())
    assert payload["completed_session_count"] == 1
    assert payload["human_vs_snapshot"][0]["session_path"].endswith("transform_01_seed_00.json")


def test_aggregate_human_baseline_prefers_valid_newer_timestamp_during_dedupe(tmp_path):
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    (session_dir / "older_invalid.json").write_text(
        json.dumps(
            {
                "task_id": "transform_01",
                "seed_index": 0,
                "sample_id": "transform_01_seeded_seed_00",
                "operator_id": "expert_a",
                "prompt_variant": "baseline",
                "status": "completed",
                "updated_at": "not-a-time",
                "score": {
                    "overall": 0.1,
                    "task_success": 0.0,
                    "decision_quality": 0.0,
                    "troubleshooting": 0.5,
                    "efficiency": 0.5,
                },
            }
        )
    )
    (session_dir / "newer_valid.json").write_text(
        json.dumps(
            {
                "task_id": "transform_01",
                "seed_index": 0,
                "sample_id": "transform_01_seeded_seed_00",
                "operator_id": "expert_a",
                "prompt_variant": "baseline",
                "status": "completed",
                "updated_at": "2026-04-17T12:00:00+00:00",
                "score": {
                    "overall": 0.9,
                    "task_success": 1.0,
                    "decision_quality": 1.0,
                    "troubleshooting": 1.0,
                    "efficiency": 0.5,
                },
            }
        )
    )

    rows = aggregate_human_baseline.dedupe_sessions(
        aggregate_human_baseline.load_completed_sessions(session_dir)
    )

    assert len(rows) == 1
    assert rows[0]["overall"] == pytest.approx(0.9)
