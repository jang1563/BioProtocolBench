#!/usr/bin/env python3
"""Launch the curated human-baseline pilot session pack."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEED_PLAN = REPO_ROOT / "results" / "human_baseline_seed_plan.json"
DEFAULT_SESSION_DIR = REPO_ROOT / "results" / "human_baseline_sessions"


def resolve_repo_path(path_str: str) -> Path:
    path = Path(path_str)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def load_run_human_baseline_module():
    module_name = "run_human_baseline_pilot_dep"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing

    script_path = REPO_ROOT / "scripts" / "run_human_baseline.py"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_seed_plan(seed_plan_path: Path) -> list[dict[str, Any]]:
    payload = json.loads(seed_plan_path.read_text())
    entries = payload.get("pilot_entries")
    if not isinstance(entries, list):
        raise ValueError("Seed plan must contain a 'pilot_entries' list.")

    normalized: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Each seed-plan entry must be a JSON object.")
        task_id = entry.get("task_id")
        seed_index = entry.get("seed_index")
        if not isinstance(task_id, str) or not isinstance(seed_index, int):
            raise ValueError("Each seed-plan entry needs string task_id and integer seed_index.")
        normalized.append(
            {
                "task_id": task_id,
                "seed_index": seed_index,
                "selection_rationale": entry.get("selection_rationale", ""),
            }
        )
    return normalized


def prompt_variant_for_entry(plan_entry: dict[str, Any], growth_prompt_variant: str) -> str:
    if plan_entry["task_id"] == "growth_01":
        return growth_prompt_variant
    return "baseline"


def resolve_session_path(
    plan_entry: dict[str, Any],
    operator_id: str,
    session_dir: Path,
    baseline_module,
    growth_prompt_variant: str,
) -> Path:
    prompt_variant = prompt_variant_for_entry(plan_entry, growth_prompt_variant)
    default_path = baseline_module._default_session_path_for_operator(
        plan_entry["task_id"],
        plan_entry["seed_index"],
        operator_id,
        prompt_variant=prompt_variant,
    )
    return session_dir / default_path.name


def build_plan_rows(
    plan_entries: list[dict[str, Any]],
    operator_id: str,
    session_dir: Path,
    baseline_module,
    growth_prompt_variant: str = "baseline",
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in plan_entries:
        prompt_variant = prompt_variant_for_entry(entry, growth_prompt_variant)
        session_path = resolve_session_path(
            entry,
            operator_id,
            session_dir,
            baseline_module,
            growth_prompt_variant=growth_prompt_variant,
        )
        rows.append(
            {
                **entry,
                "prompt_variant": prompt_variant,
                "session_path": session_path,
                "status": baseline_module.saved_session_status(session_path),
            }
        )
    return rows


def filter_plan_rows(
    rows: list[dict[str, Any]],
    task_filters: list[str] | None = None,
    seed_filters: list[int] | None = None,
) -> list[dict[str, Any]]:
    filtered = rows
    if task_filters:
        allowed_tasks = set(task_filters)
        filtered = [row for row in filtered if row["task_id"] in allowed_tasks]
    if seed_filters:
        allowed_seeds = set(seed_filters)
        filtered = [row for row in filtered if row["seed_index"] in allowed_seeds]
    return filtered


def select_plan_rows(
    rows: list[dict[str, Any]],
    run_all: bool = False,
) -> list[dict[str, Any]]:
    in_progress = [row for row in rows if row["status"] == "in_progress"]
    pending = [row for row in rows if row["status"] == "pending"]

    if run_all:
        return list(in_progress) + list(pending)

    if in_progress:
        return [in_progress[0]]
    if pending:
        return [pending[0]]
    return []


def print_plan(rows: list[dict[str, Any]], operator_id: str, session_dir: Path) -> None:
    print("Human baseline pilot plan")
    print("  operator_id: {}".format(operator_id))
    print("  session_dir: {}".format(session_dir))
    print()
    for index, row in enumerate(rows, start=1):
        print("[{}/{}] {} seed {:02d} [{}]".format(index, len(rows), row["task_id"], row["seed_index"], row["status"]))
        if row.get("prompt_variant", "baseline") != "baseline":
            print("  prompt_variant: {}".format(row["prompt_variant"]))
        print("  session: {}".format(row["session_path"]))
        if row["selection_rationale"]:
            print("  rationale: {}".format(row["selection_rationale"]))


def launch_plan_rows(
    rows: list[dict[str, Any]],
    operator_id: str,
    growth_prompt_variant: str,
    baseline_module,
) -> int:
    for index, row in enumerate(rows, start=1):
        print()
        print("=== Human baseline pilot {}/{} ===".format(index, len(rows)))
        print("task: {} | seed: {:02d} | operator: {} | status: {}".format(
            row["task_id"],
            row["seed_index"],
            operator_id,
            row["status"],
        ))
        if row.get("prompt_variant", "baseline") != "baseline":
            print("prompt_variant: {}".format(row["prompt_variant"]))
        print("session file: {}".format(row["session_path"]))
        if row["selection_rationale"]:
            print("why this seed: {}".format(row["selection_rationale"]))

        session = baseline_module.build_task_session(
            task_id=row["task_id"],
            seed_index=row["seed_index"],
            operator_id=operator_id,
            growth_prompt_variant=row.get("prompt_variant", growth_prompt_variant),
        )
        rc = baseline_module.run_human_baseline(session, row["session_path"])
        if rc != 0:
            return rc
        current_status = baseline_module.saved_session_status(row["session_path"])
        if current_status != "completed":
            print("Stopping pilot run because the current session remains {}.".format(current_status))
            return 0
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--operator-id",
        required=True,
        help="Short identifier for the human operator completing the pilot sessions.",
    )
    parser.add_argument(
        "--seed-plan",
        default=str(DEFAULT_SEED_PLAN),
        help="Pilot seed-plan JSON path.",
    )
    parser.add_argument(
        "--session-dir",
        default=str(DEFAULT_SESSION_DIR),
        help="Directory where session JSONs will be written.",
    )
    parser.add_argument(
        "--task",
        action="append",
        choices=("transform_01", "growth_01"),
        help="Optional task filter. May be passed more than once.",
    )
    parser.add_argument(
        "--seed-index",
        action="append",
        type=int,
        help="Optional seed filter. May be passed more than once.",
    )
    parser.add_argument(
        "--growth-prompt-variant",
        choices=("baseline", "verbose_troubleshoot"),
        default="baseline",
        help="Prompt variant for any growth_01 sessions in the pilot run.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print the plan and current session status without launching anything.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Launch every matching in-progress or pending pilot session in sequence.",
    )
    parser.add_argument(
        "--include-completed",
        action="store_true",
        help="Include already completed sessions when listing the pilot plan.",
    )
    args = parser.parse_args(argv)

    seed_plan_path = resolve_repo_path(args.seed_plan)
    session_dir = resolve_repo_path(args.session_dir)
    session_dir.mkdir(parents=True, exist_ok=True)

    baseline_module = load_run_human_baseline_module()
    plan_entries = load_seed_plan(seed_plan_path)
    rows = build_plan_rows(
        plan_entries,
        args.operator_id,
        session_dir,
        baseline_module,
        growth_prompt_variant=args.growth_prompt_variant,
    )
    rows = filter_plan_rows(rows, task_filters=args.task, seed_filters=args.seed_index)

    if not args.include_completed:
        list_rows = [row for row in rows if row["status"] != "completed"]
    else:
        list_rows = rows

    if args.list:
        print_plan(list_rows, args.operator_id, session_dir)
        return 0

    selected_rows = select_plan_rows(
        rows,
        run_all=args.all,
    )
    if not selected_rows:
        print("No matching pilot sessions remain to run for operator {}.".format(args.operator_id))
        return 0

    return launch_plan_rows(
        selected_rows,
        operator_id=args.operator_id,
        growth_prompt_variant=args.growth_prompt_variant,
        baseline_module=baseline_module,
    )


if __name__ == "__main__":
    raise SystemExit(main())
