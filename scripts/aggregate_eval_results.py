#!/usr/bin/env python3
"""Aggregate Inspect .eval logs in results/logs into results/results.md.

Scans every .eval archive in the log directory (default results/logs), pulls
model/task/status and per-axis scores out of each log's header.json and
samples/*.json, deduplicates repeated reruns by keeping the latest archive for
each (model, task, sample_id), then writes a human-readable Markdown summary
with per-(model, task) means and standard deviations.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import statistics
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_DIR = REPO_ROOT / "results" / "logs"
DEFAULT_OUT = REPO_ROOT / "results" / "results.md"

AXES = ("overall", "task_success", "decision_quality", "troubleshooting", "efficiency")


def resolve_repo_path(path_str: str) -> Path:
    path = Path(path_str)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def repo_relative_display_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _is_repo_relative_path(path: Path) -> bool:
    try:
        path.relative_to(REPO_ROOT)
        return True
    except ValueError:
        return False


def _format_log_dir_reference(log_dir: Path) -> str:
    rel = repo_relative_display_path(log_dir)
    if _is_repo_relative_path(log_dir):
        return "[{rel}](../{rel})".format(rel=rel)
    return "`{}`".format(rel)


def _parse_created_timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not value.strip():
        return datetime.min.replace(tzinfo=timezone.utc)
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def extract_scores(eval_path: Path):
    """Return a list of per-sample dicts: {task, model, status, axis -> float, tokens}."""
    rows = []
    try:
        from inspect_ai.log import read_eval_log

        log = read_eval_log(str(eval_path))
    except Exception:
        return rows

    model = getattr(getattr(log, "eval", None), "model", "unknown")
    task = getattr(getattr(log, "eval", None), "task", "unknown")
    status = getattr(log, "status", "unknown")
    created = getattr(getattr(log, "eval", None), "created", "") or ""

    model_usage = getattr(getattr(log, "stats", None), "model_usage", {}) or {}
    token_stats = model_usage.get(model)
    tokens = {
        "input": getattr(token_stats, "input_tokens", None),
        "output": getattr(token_stats, "output_tokens", None),
        "total": getattr(token_stats, "total_tokens", None),
        "input_cache_read": getattr(token_stats, "input_tokens_cache_read", None),
    }

    for sample in getattr(log, "samples", []) or []:
        scores = getattr(sample, "scores", {}) or {}
        value_block = None
        for scorer_info in scores.values():
            candidate = getattr(scorer_info, "value", None)
            if isinstance(candidate, dict):
                value_block = candidate
                break
        if value_block is None:
            continue
        row = {
            "model": model,
            "task": task,
            "status": status,
            "sample_id": getattr(sample, "id", eval_path.stem),
            "eval_log": eval_path.name,
            "eval_log_path": str(eval_path.resolve()),
            "created": created,
            "tokens": tokens,
        }
        for axis in AXES:
            row[axis] = float(value_block.get(axis, 0.0))
        rows.append(row)
    return rows


def dedupe_rows(rows):
    """Keep only the latest archive for each (model, task, sample_id)."""
    latest_by_sample = {}
    for row in rows:
        key = (row["model"], row["task"], row["sample_id"])
        current = latest_by_sample.get(key)
        row_order_key = (
            _parse_created_timestamp(row.get("created")),
            row.get("eval_log", ""),
            row.get("eval_log_path", ""),
        )
        if current is None:
            latest_by_sample[key] = row
            continue
        current_order_key = (
            _parse_created_timestamp(current.get("created")),
            current.get("eval_log", ""),
            current.get("eval_log_path", ""),
        )
        if row_order_key >= current_order_key:
            latest_by_sample[key] = row
    return sorted(
        latest_by_sample.values(),
        key=lambda row: (
            row["model"],
            row["task"],
            row["sample_id"],
            row.get("eval_log", ""),
        ),
    )


def aggregate(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["model"], row["task"])].append(row)
    summary = []
    for (model, task), cell_rows in sorted(groups.items()):
        entry = {
            "model": model,
            "task": task,
            "n": len(cell_rows),
        }
        for axis in AXES:
            values = [row[axis] for row in cell_rows if axis in row]
            if not values:
                continue
            entry["{}_mean".format(axis)] = statistics.fmean(values)
            entry["{}_std".format(axis)] = (
                statistics.stdev(values) if len(values) > 1 else 0.0
            )
        summary.append(entry)
    return summary


def format_markdown(
    summary,
    per_sample_rows,
    out_path: Path,
    log_dirs: list[Path],
    deduped_count: int,
):
    rel_links = [_format_log_dir_reference(log_dir) for log_dir in log_dirs]
    lines = [
        "# BioProtocolBench Evaluation Results",
        "",
        "Automatically aggregated from Inspect AI `.eval` logs in {}.".format(
            ", ".join(rel_links)
        ),
        "",
    ]
    if deduped_count:
        lines.extend(
            [
                "Repeated reruns with the same `(model, task, sample_id)` are deduplicated by keeping the latest `.eval` archive. {} duplicate sample rows were ignored.".format(
                    deduped_count
                ),
                "",
            ]
        )
    lines.extend(
        [
        "## Per-model per-task summary",
        "",
        "Mean overall score across the seed samples run for each (model, task) cell. `n` is the number of samples in that cell.",
        "",
        "| Model | Task | n | overall (mean±std) | task_success | decision_quality | troubleshooting | efficiency |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for entry in summary:
        line = "| {model} | `{task}` | {n} | {ov_mean:.3f} ± {ov_std:.3f} | {ts_mean:.3f} ± {ts_std:.3f} | {dq_mean:.3f} ± {dq_std:.3f} | {tr_mean:.3f} ± {tr_std:.3f} | {ef_mean:.3f} ± {ef_std:.3f} |".format(
            model=entry["model"],
            task=entry["task"],
            n=entry["n"],
            ov_mean=entry.get("overall_mean", 0.0),
            ov_std=entry.get("overall_std", 0.0),
            ts_mean=entry.get("task_success_mean", 0.0),
            ts_std=entry.get("task_success_std", 0.0),
            dq_mean=entry.get("decision_quality_mean", 0.0),
            dq_std=entry.get("decision_quality_std", 0.0),
            tr_mean=entry.get("troubleshooting_mean", 0.0),
            tr_std=entry.get("troubleshooting_std", 0.0),
            ef_mean=entry.get("efficiency_mean", 0.0),
            ef_std=entry.get("efficiency_std", 0.0),
        )
        lines.append(line)

    lines.extend(
        [
            "",
            "## Per-sample detail",
            "",
            "| Model | Task | Sample | overall | task | decision | trouble | efficiency |",
            "|---|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in per_sample_rows:
        lines.append(
            "| {model} | `{task}` | `{sample}` | {overall:.3f} | {task_success:.3f} | {decision_quality:.3f} | {troubleshooting:.3f} | {efficiency:.3f} |".format(
                model=row["model"],
                task=row["task"],
                sample=row["sample_id"],
                overall=row["overall"],
                task_success=row["task_success"],
                decision_quality=row["decision_quality"],
                troubleshooting=row["troubleshooting"],
                efficiency=row["efficiency"],
            )
        )
    lines.append("")
    out_path.write_text("\n".join(lines))


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--log-dir",
        nargs="+",
        default=[str(DEFAULT_LOG_DIR)],
        help="One or more directories containing Inspect .eval archives.",
    )
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args(argv)

    log_dirs = [resolve_repo_path(path_str) for path_str in args.log_dir]
    out_path = resolve_repo_path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    eval_paths = []
    for log_dir in log_dirs:
        eval_paths.extend(sorted(log_dir.glob("*.eval")))
    if not eval_paths:
        print("No .eval files found in {}".format(", ".join(str(p) for p in log_dirs)), file=sys.stderr)
        return 1

    all_rows = []
    for path in eval_paths:
        all_rows.extend(extract_scores(path))
    if not all_rows:
        print("No scoreable samples found.", file=sys.stderr)
        return 1

    deduped_rows = dedupe_rows(all_rows)
    summary = aggregate(deduped_rows)
    format_markdown(
        summary,
        deduped_rows,
        out_path,
        log_dirs,
        deduped_count=len(all_rows) - len(deduped_rows),
    )
    print("Wrote {} rows to {}".format(len(deduped_rows), out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
