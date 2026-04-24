# Current Task Frontier Bundle (5 Seeds)

Expanded cross-provider bundle for the newer implemented tasks, extending the earlier 3-seed frontier slice to 5 stochastic seeds per task.

This bundle is intentionally separate from:

- the published historical portfolio in [results.md](results.md)
- the 1-model smoke track in [current_smoke.md](current_smoke.md)
- the OpenAI-only 3-seed slice in [current_openai.md](current_openai.md)
- the earlier cross-provider 3-seed slice in [current_frontier.md](current_frontier.md)

## Configuration

- Models: `openai/gpt-4o-mini`, `openai/gpt-4o`, `anthropic/claude-haiku-4-5`, `anthropic/claude-sonnet-4-5`
- Seeds: 5 per task
- Tasks:
  `golden_gate_01`, `gibson_01`, `miniprep_01`, `express_01`, `purify_01`
- Construction:
  seeds `00`-`02` come from the existing 3-seed logs
  seeds `03`-`04` were added later via the new `seed_start` task parameter

## Headline

The 5-seed view sharpens the separation that the 3-seed slice only hinted at.

- `gpt-4o-mini` and `claude-sonnet-4-5` remained perfect across all five tasks and all five seeds.
- `gpt-4o` improved slightly relative to the 3-seed view, ending at `0.996` mean across tasks with its only gap still on `gibson_01` efficiency.
- `claude-haiku-4-5` dropped materially to `0.976` mean across tasks because the added seeds exposed a real `golden_gate_01` task-success miss and another `gibson_01` efficiency miss.

## Summary

| Model | Mean across tasks | golden_gate_01 | gibson_01 | miniprep_01 | express_01 | purify_01 |
|---|---:|---:|---:|---:|---:|---:|
| `openai/gpt-4o-mini` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `openai/gpt-4o` | 0.996 | 1.000 | 0.980 | 1.000 | 1.000 | 1.000 |
| `anthropic/claude-haiku-4-5` | 0.976 | 0.910 | 0.970 | 1.000 | 1.000 | 1.000 |
| `anthropic/claude-sonnet-4-5` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

## Interpretation

This larger slice changes the story in one important way: the earlier 3-seed frontier view understated Haiku's instability on the assembly tasks.

- `gpt-4o-mini` and `claude-sonnet-4-5` now look genuinely stable on this task family, not just lucky over 3 seeds.
- `gpt-4o` still solves everything correctly but pays an execution-efficiency penalty on `gibson_01` in 1 of 5 samples.
- `claude-haiku-4-5` is no longer just an efficiency-near-miss model here. On `golden_gate_01` seed `04`, it executed the protocol correctly but converted a low-count plate into an incorrect final transformant report (`80`), causing `task_success = 0.0` for that sample. On `gibson_01`, it also picked up another avoidable efficiency miss on seed `04`.

## Notes

The Anthropic 3-seed raw log directory contains repeated reruns for some cells after an interrupted earlier run. The aggregated tables and plots here deduplicate repeated `(model, task, sample_id)` rows by keeping the latest `.eval` archive.

The 5-seed bundle is assembled from four log directories: the original 3-seed OpenAI and Anthropic runs, plus separate seed-`03`/`04` extension runs collected with `SEED_START=3`.

## Files

- Aggregated table: [current_frontier_5seed_results.md](current_frontier_5seed_results.md)
- Raw eval logs: [current_openai_logs](current_openai_logs), [current_anthropic_logs](current_anthropic_logs), [current_openai_logs_seed34](current_openai_logs_seed34), [current_anthropic_logs_seed34](current_anthropic_logs_seed34)
- Plots: [scorecard.png](current_frontier_5seed_plots/scorecard.png), [axis_heatmap.png](current_frontier_5seed_plots/axis_heatmap.png)
- Focused assembly-task view: [current_frontier_5seed_assembly.md](current_frontier_5seed_assembly.md)

## Reproduce

```bash
source ~/.api_keys >/dev/null 2>&1

# Base 3-seed bundle.
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

# Incremental seeds 03-04 only.
INSPECT_BIN=/tmp/labcraft-py311/bin/inspect \
SEEDS=2 \
SEED_START=3 \
MODELS="openai/gpt-4o-mini openai/gpt-4o" \
TASKS="golden_gate_01 gibson_01 miniprep_01 express_01 purify_01" \
LOG_DIR=results/current_openai_logs_seed34 \
./scripts/run_portfolio_eval.sh

INSPECT_BIN=/tmp/labcraft-py311/bin/inspect \
SEEDS=2 \
SEED_START=3 \
MODELS="anthropic/claude-haiku-4-5 anthropic/claude-sonnet-4-5" \
TASKS="golden_gate_01 gibson_01 miniprep_01 express_01 purify_01" \
LOG_DIR=results/current_anthropic_logs_seed34 \
./scripts/run_portfolio_eval.sh

python3 scripts/aggregate_eval_results.py \
  --log-dir results/current_openai_logs results/current_anthropic_logs \
            results/current_openai_logs_seed34 results/current_anthropic_logs_seed34 \
  --out results/current_frontier_5seed_results.md

python3 scripts/plot_scorecard.py \
  --log-dir results/current_openai_logs results/current_anthropic_logs \
            results/current_openai_logs_seed34 results/current_anthropic_logs_seed34 \
  --out-dir results/current_frontier_5seed_plots \
  --task-preset auto \
  --models openai/gpt-4o-mini openai/gpt-4o anthropic/claude-haiku-4-5 anthropic/claude-sonnet-4-5
```
