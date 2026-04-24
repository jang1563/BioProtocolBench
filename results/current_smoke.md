# Current Task Smoke Bundle

Smoke-validation bundle for the newer implemented tasks added after the frozen April 2026 5-task portfolio snapshot.

This bundle is intentionally separate from the published portfolio results in [results.md](results.md):

- It uses **1 model**: `openai/gpt-4o-mini`
- It uses **1 seed per task**
- It covers the newer implemented tasks:
  `golden_gate_01`, `gibson_01`, `miniprep_01`, `express_01`, `purify_01`
- It is a **sanity-check / regression-smoke track**, not a comparable benchmark slice

## Outcome

All five smoke runs completed successfully on April 16, 2026, with `overall = 1.0` on the deterministic trajectory scorer.

| Task | Model | Seeds | Overall |
|---|---|---:|---:|
| `golden_gate_01` | `openai/gpt-4o-mini` | 1 | 1.000 |
| `gibson_01` | `openai/gpt-4o-mini` | 1 | 1.000 |
| `miniprep_01` | `openai/gpt-4o-mini` | 1 | 1.000 |
| `express_01` | `openai/gpt-4o-mini` | 1 | 1.000 |
| `purify_01` | `openai/gpt-4o-mini` | 1 | 1.000 |

## Files

- Aggregated table: [current_smoke_results.md](current_smoke_results.md)
- Raw eval logs: [current_smoke_logs](current_smoke_logs)
- Plots:
  [scorecard.png](current_smoke_plots/scorecard.png)
  [axis_heatmap.png](current_smoke_plots/axis_heatmap.png)

## Reproduce

```bash
source ~/.api_keys >/dev/null 2>&1
INSPECT_BIN=/tmp/labcraft-py311/bin/inspect \
SEEDS=1 \
MODELS="openai/gpt-4o-mini" \
TASKS="golden_gate_01 gibson_01 miniprep_01 express_01 purify_01" \
LOG_DIR=results/current_smoke_logs \
./scripts/run_portfolio_eval.sh

python3 scripts/aggregate_eval_results.py \
  --log-dir results/current_smoke_logs \
  --out results/current_smoke_results.md

python3 scripts/plot_scorecard.py \
  --log-dir results/current_smoke_logs \
  --out-dir results/current_smoke_plots \
  --task-preset auto \
  --models openai/gpt-4o-mini
```
