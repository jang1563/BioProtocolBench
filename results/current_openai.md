# Current Task OpenAI Bundle

Small comparable bundle for the newer implemented tasks added after the frozen April 2026 5-task portfolio snapshot.

This bundle is intentionally separate from both:

- the published historical portfolio in [results.md](results.md)
- the 1-model, 1-seed sanity-check track in [current_smoke.md](current_smoke.md)

## Configuration

- Models: `openai/gpt-4o-mini`, `openai/gpt-4o`
- Seeds: 3 per task
- Tasks:
  `golden_gate_01`, `gibson_01`, `miniprep_01`, `express_01`, `purify_01`

## Headline

The newer-task bundle is almost fully saturated for both OpenAI models.

- `gpt-4o-mini` scored `1.000` on all five tasks across all three seeds.
- `gpt-4o` also saturated four of five tasks.
- The only visible gap was `gibson_01`, where `gpt-4o` achieved `overall = 0.967 ± 0.029` because the task was solved correctly but missed the optimal efficiency budget on 2 of 3 seeds.

## Summary

| Model | golden_gate_01 | gibson_01 | miniprep_01 | express_01 | purify_01 |
|---|---:|---:|---:|---:|---:|
| `openai/gpt-4o-mini` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `openai/gpt-4o` | 1.000 | 0.967 | 1.000 | 1.000 | 1.000 |

## Interpretation

This is not yet a broad benchmark result, but it is a useful signal:

- the newer tasks are wired correctly enough to support repeated multi-seed evaluation
- both OpenAI models solve the task-success and decision-quality requirements reliably here
- `gibson_01` still exposes a small execution-efficiency difference that the deterministic scorer can detect

## Files

- Aggregated table: [current_openai_results.md](current_openai_results.md)
- Raw eval logs: [current_openai_logs](current_openai_logs)
- Plots:
  [scorecard.png](current_openai_plots/scorecard.png)
  [axis_heatmap.png](current_openai_plots/axis_heatmap.png)

## Reproduce

```bash
source ~/.api_keys >/dev/null 2>&1
INSPECT_BIN=/tmp/labcraft-py311/bin/inspect \
SEEDS=3 \
MODELS="openai/gpt-4o-mini openai/gpt-4o" \
TASKS="golden_gate_01 gibson_01 miniprep_01 express_01 purify_01" \
LOG_DIR=results/current_openai_logs \
./scripts/run_portfolio_eval.sh

python3 scripts/aggregate_eval_results.py \
  --log-dir results/current_openai_logs \
  --out results/current_openai_results.md

python3 scripts/plot_scorecard.py \
  --log-dir results/current_openai_logs \
  --out-dir results/current_openai_plots \
  --task-preset auto \
  --models openai/gpt-4o-mini openai/gpt-4o
```
