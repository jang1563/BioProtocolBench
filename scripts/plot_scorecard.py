#!/usr/bin/env python3
"""Render scorecard + axis breakdown charts from Inspect .eval logs.

Reads results/logs/*.eval, aggregates per-(model, task) mean and stddev across
each of the four scoring axes, and writes two PNGs:

- results/scorecard.png   : grouped bar chart, overall score per model per task
- results/axis_heatmap.png : per-axis score matrix, models x (task, axis)

Both are PNGs at 150 dpi so they render crisply on GitHub's README.
"""
from __future__ import annotations

import json
import statistics
import sys
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = REPO_ROOT / "results" / "logs"
OUT_DIR = REPO_ROOT / "results"

TASKS = ["transform_01", "growth_01", "pcr_01", "screen_01", "clone_01"]
MODELS = [
    "openai/gpt-4o-mini",
    "openai/gpt-4o",
    "anthropic/claude-haiku-4-5",
    "anthropic/claude-sonnet-4-5",
]
AXES = ("task_success", "decision_quality", "troubleshooting", "efficiency", "overall")

MODEL_SHORT = {
    "openai/gpt-4o-mini": "gpt-4o-mini",
    "openai/gpt-4o": "gpt-4o",
    "anthropic/claude-haiku-4-5": "haiku-4-5",
    "anthropic/claude-sonnet-4-5": "sonnet-4-5",
}

MODEL_COLORS = {
    "openai/gpt-4o-mini": "#7fcf9f",
    "openai/gpt-4o": "#2ea572",
    "anthropic/claude-haiku-4-5": "#e09f7d",
    "anthropic/claude-sonnet-4-5": "#c05621",
}


def extract_scores(eval_path: Path):
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
        samples_dir = tmp_path / "samples"
        if not samples_dir.exists():
            return rows
        for sample_file in sorted(samples_dir.glob("*.json")):
            data = json.loads(sample_file.read_text())
            scores = data.get("scores") or {}
            value_block = None
            for _, scorer_info in scores.items():
                if isinstance(scorer_info, dict) and isinstance(scorer_info.get("value"), dict):
                    value_block = scorer_info["value"]
                    break
            if value_block is None:
                continue
            row = {"model": model, "task": task}
            for axis in AXES:
                row[axis] = float(value_block.get(axis, 0.0))
            rows.append(row)
    return rows


def load_all_rows():
    rows = []
    for path in sorted(LOG_DIR.glob("*.eval")):
        rows.extend(extract_scores(path))
    return rows


def aggregate(rows):
    cells = defaultdict(list)
    for row in rows:
        cells[(row["model"], row["task"])].append(row)
    agg = {}
    for (model, task), cell_rows in cells.items():
        entry = {"n": len(cell_rows)}
        for axis in AXES:
            values = [r[axis] for r in cell_rows]
            entry["{}_mean".format(axis)] = statistics.fmean(values) if values else 0.0
            entry["{}_std".format(axis)] = statistics.stdev(values) if len(values) > 1 else 0.0
        agg[(model, task)] = entry
    return agg


def plot_scorecard(agg):
    fig, ax = plt.subplots(figsize=(11, 5.5))
    n_models = len(MODELS)
    bar_width = 0.18
    x_positions = np.arange(len(TASKS))

    for i, model in enumerate(MODELS):
        means = [agg.get((model, task), {}).get("overall_mean", 0.0) for task in TASKS]
        stds = [agg.get((model, task), {}).get("overall_std", 0.0) for task in TASKS]
        offsets = x_positions + (i - (n_models - 1) / 2) * bar_width
        ax.bar(
            offsets,
            means,
            bar_width,
            yerr=stds,
            capsize=3,
            color=MODEL_COLORS[model],
            label=MODEL_SHORT[model],
            edgecolor="#222",
            linewidth=0.4,
            error_kw={"elinewidth": 1.0, "ecolor": "#333"},
        )

    ax.set_xticks(x_positions)
    ax.set_xticklabels(TASKS, fontsize=11)
    ax.set_ylabel("Overall score (mean \u00b1 std, n=5)", fontsize=11)
    ax.set_ylim(0, 1.05)
    ax.set_yticks(np.arange(0.0, 1.01, 0.2))
    ax.axhline(1.0, color="#aaa", linestyle=":", linewidth=0.8)
    ax.grid(axis="y", linestyle="--", linewidth=0.4, alpha=0.5)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_title(
        "BioProtocolBench overall score by model and task (N=5 seeds per cell)",
        fontsize=12,
        pad=12,
    )
    ax.legend(
        loc="lower left",
        frameon=False,
        ncol=4,
        fontsize=10,
        bbox_to_anchor=(0.0, -0.22),
    )

    plt.tight_layout()
    out_path = OUT_DIR / "scorecard.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out_path


def plot_axis_heatmap(agg):
    display_axes = ("task_success", "decision_quality", "troubleshooting", "efficiency")
    axis_labels = {
        "task_success": "task",
        "decision_quality": "decision",
        "troubleshooting": "trouble",
        "efficiency": "efficiency",
    }

    rows = len(MODELS)
    cols = len(TASKS) * len(display_axes)
    matrix = np.full((rows, cols), np.nan)
    col_labels = []
    for task in TASKS:
        for axis in display_axes:
            col_labels.append(axis_labels[axis])

    for j, task in enumerate(TASKS):
        for k, axis in enumerate(display_axes):
            col = j * len(display_axes) + k
            for i, model in enumerate(MODELS):
                entry = agg.get((model, task), {})
                matrix[i, col] = entry.get("{}_mean".format(axis), np.nan)

    fig, ax = plt.subplots(figsize=(14, 5.5))
    im = ax.imshow(matrix, cmap="RdYlGn", vmin=0.0, vmax=1.0, aspect="auto")

    ax.set_yticks(np.arange(rows))
    ax.set_yticklabels([MODEL_SHORT[m] for m in MODELS], fontsize=11)
    ax.set_xticks(np.arange(cols))
    ax.set_xticklabels(col_labels, fontsize=9.5, rotation=35, ha="right")

    ax_top = ax.secondary_xaxis("top")
    task_centers = [
        j * len(display_axes) + (len(display_axes) - 1) / 2 for j in range(len(TASKS))
    ]
    ax_top.set_xticks(task_centers)
    ax_top.set_xticklabels(TASKS, fontsize=11.5, fontweight="bold")
    ax_top.tick_params(axis="x", which="both", length=0, pad=6)

    for j in range(1, len(TASKS)):
        left = j * len(display_axes) - 0.5
        ax.axvline(left, color="#222", linewidth=1.0)

    for i in range(rows):
        for k in range(cols):
            val = matrix[i, k]
            if np.isnan(val):
                continue
            color = "#111" if val > 0.55 else "#f5f5f5"
            ax.text(
                k,
                i,
                "{:.2f}".format(val),
                ha="center",
                va="center",
                fontsize=9.5,
                color=color,
            )

    fig.suptitle(
        "Per-axis breakdown: mean score (0 - 1) across N=5 seeds",
        fontsize=12.5,
        y=0.97,
    )
    cbar = fig.colorbar(im, ax=ax, shrink=0.82, pad=0.015)
    cbar.ax.tick_params(labelsize=9)
    plt.subplots_adjust(top=0.80, bottom=0.20, left=0.10, right=0.95)
    out_path = OUT_DIR / "axis_heatmap.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out_path


def main():
    rows = load_all_rows()
    if not rows:
        print("No .eval files found in {}".format(LOG_DIR), file=sys.stderr)
        return 1
    agg = aggregate(rows)
    scorecard_path = plot_scorecard(agg)
    heatmap_path = plot_axis_heatmap(agg)
    print("Wrote {} and {}".format(scorecard_path, heatmap_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
