# Current Task Frontier Bundle

Small cross-provider bundle for the newer implemented tasks added after the frozen April 2026 5-task portfolio snapshot.

This bundle is intentionally separate from:

- the published historical portfolio in [results.md](results.md)
- the 1-model smoke track in [current_smoke.md](current_smoke.md)
- the OpenAI-only comparable slice in [current_openai.md](current_openai.md)

## Configuration

- Models: `openai/gpt-4o-mini`, `openai/gpt-4o`, `anthropic/claude-haiku-4-5`, `anthropic/claude-sonnet-4-5`
- Seeds: 3 per task
- Tasks:
  `golden_gate_01`, `gibson_01`, `miniprep_01`, `express_01`, `purify_01`

## Headline

The current-task frontier bundle is nearly saturated across all four models.

- `gpt-4o-mini` and `claude-sonnet-4-5` scored `1.000` on all five tasks across all three seeds.
- `gpt-4o` only dropped on `gibson_01`, with `overall = 0.967 ± 0.029` because efficiency fell to `0.667 ± 0.289` while every other axis stayed perfect.
- `claude-haiku-4-5` only dropped on the two assembly tasks, with `overall = 0.983 ± 0.029` on both `golden_gate_01` and `gibson_01`, again driven entirely by efficiency misses.

## Summary

| Model | Mean across tasks | golden_gate_01 | gibson_01 | miniprep_01 | express_01 | purify_01 |
|---|---:|---:|---:|---:|---:|---:|
| `openai/gpt-4o-mini` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `openai/gpt-4o` | 0.993 | 1.000 | 0.967 | 1.000 | 1.000 | 1.000 |
| `anthropic/claude-haiku-4-5` | 0.993 | 0.983 | 0.983 | 1.000 | 1.000 | 1.000 |
| `anthropic/claude-sonnet-4-5` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

## Interpretation

On this newer-task slice, the remaining separation is almost entirely about agentic efficiency rather than biology or reporting accuracy.

- All four models saturated `task_success`, `decision_quality`, and `troubleshooting` on every cell in this bundle.
- The only non-perfect scores came from extra tool use on assembly-style tasks.
- This makes the current-task bundle a useful complement to the harder historical 5-task snapshot: it is already sensitive enough to detect execution-quality differences, but not yet broad enough to produce a large provider gap.

## Notes

The Anthropic raw log directory contains repeated reruns for some cells after an interrupted earlier run. The aggregated tables and plots in this bundle deduplicate repeated `(model, task, sample_id)` rows by keeping the latest `.eval` archive, so every reported cell here still reflects exactly 3 seeds.

## Files

- Aggregated table: [current_frontier_results.md](current_frontier_results.md)
- Raw eval logs: [current_openai_logs](current_openai_logs), [current_anthropic_logs](current_anthropic_logs)
- Plots: [scorecard.png](current_frontier_plots/scorecard.png), [axis_heatmap.png](current_frontier_plots/axis_heatmap.png)

## Reproduce

```bash
source ~/.api_keys >/dev/null 2>&1

INSPECT_BIN=/tmp/labcraft-py311/bin/inspect \
SEEDS=3 \
MODELS="openai/gpt-4o-mini openai/gpt-4o" \
TASKS="golden_gate_01 gibson_01 miniprep_01 express_01 purify_01" \
LOG_DIR=results/current_openai_logs \
./scripts/run_portfolio_eval.sh

INSPECT_BIN=/tmp/labcraft-py311/bin/inspect \
SEEDS=3 \
MODELS="anthropic/claude-haiku-4-5 anthropic/claude-sonnet-4-5" \
TASKS="golden_gate_01 gibson_01 miniprep_01 express_01 purify_01" \
LOG_DIR=results/current_anthropic_logs \
./scripts/run_portfolio_eval.sh

python3 scripts/aggregate_eval_results.py \
  --log-dir results/current_openai_logs results/current_anthropic_logs \
  --out results/current_frontier_results.md

python3 scripts/plot_scorecard.py \
  --log-dir results/current_openai_logs results/current_anthropic_logs \
  --out-dir results/current_frontier_plots \
  --task-preset auto \
  --models openai/gpt-4o-mini openai/gpt-4o anthropic/claude-haiku-4-5 anthropic/claude-sonnet-4-5
```
