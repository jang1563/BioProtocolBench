#!/usr/bin/env python3
"""Aggregate Inspect .eval logs in results/logs into results/results.md.

Scans every .eval archive in the log directory (default results/logs), pulls
model/task/status and per-axis scores out of each log's header.json and
samples/*.json, then writes a human-readable Markdown summary with
per-(model, task) means and standard deviations.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_DIR = REPO_ROOT / "results" / "logs"
DEFAULT_OUT = REPO_ROOT / "results" / "results.md"

AXES = ("overall", "task_success", "decision_quality", "troubleshooting", "efficiency")


def extract_scores(eval_path: Path):
    """Return a list of per-sample dicts: {task, model, status, axis -> float, tokens}."""
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        try:
            with zipfile.ZipFile(eval_path) as zf:
                zf.extractall(tmp_path)
        except zipfile.BadZipFile:
            return rows

        header_path = tmp_path / "header.json"
        if not header_path.exists():
            return rows
        header = json.loads(header_path.read_text())
        eval_info = header.get("eval", {})
        model = eval_info.get("model", "unknown")
        task = eval_info.get("task", "unknown")
        status = header.get("status", "unknown")

        token_stats = (
            header.get("stats", {})
            .get("model_usage", {})
            .get(model, {})
        )
        tokens = {
            "input": token_stats.get("input_tokens"),
            "output": token_stats.get("output_tokens"),
            "total": token_stats.get("total_tokens"),
            "input_cache_read": token_stats.get("input_tokens_cache_read"),
        }

        samples_dir = tmp_path / "samples"
        if not samples_dir.exists():
            return rows
        for sample_file in sorted(samples_dir.glob("*.json")):
            data = json.loads(sample_file.read_text())
            scores = data.get("scores") or {}
            value_block = None
            for scorer_name, scorer_info in scores.items():
                if isinstance(scorer_info, dict) and isinstance(
                    scorer_info.get("value"), dict
                ):
                    value_block = scorer_info["value"]
                    break
            if value_block is None:
                continue
            sample_id = data.get("id") or sample_file.stem
            row = {
                "model": model,
                "task": task,
                "status": status,
                "sample_id": sample_id,
                "eval_log": eval_path.name,
                "tokens": tokens,
            }
            for axis in AXES:
                row[axis] = float(value_block.get(axis, 0.0))
            rows.append(row)
    return rows


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


def format_markdown(summary, per_sample_rows, out_path: Path, log_dir: Path):
    lines = [
        "# BioProtocolBench Evaluation Results",
        "",
        "Automatically aggregated from Inspect AI `.eval` logs in [{rel}](../{rel}).".format(
            rel=log_dir.relative_to(REPO_ROOT).as_posix()
        ),
        "",
        "## Per-model per-task summary",
        "",
        "Mean overall score across the seed samples run for each (model, task) cell. `n` is the number of samples in that cell.",
        "",
        "| Model | Task | n | overall (mean±std) | task_success | decision_quality | troubleshooting | efficiency |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
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
    parser.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args(argv)

    log_dir = Path(args.log_dir)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    eval_paths = sorted(log_dir.glob("*.eval"))
    if not eval_paths:
        print("No .eval files found in {}".format(log_dir), file=sys.stderr)
        return 1

    all_rows = []
    for path in eval_paths:
        all_rows.extend(extract_scores(path))
    if not all_rows:
        print("No scoreable samples found.", file=sys.stderr)
        return 1

    summary = aggregate(all_rows)
    format_markdown(summary, all_rows, out_path, log_dir)
    print("Wrote {} rows to {}".format(len(all_rows), out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
