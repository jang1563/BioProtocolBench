# Current Frontier 5-Seed Assembly View

Focused view of the two assembly tasks in the newer-task 5-seed frontier bundle: `golden_gate_01` and `gibson_01`.

This page exists because the most interesting variance in the 5-seed newer-task bundle is concentrated here. The protein and miniprep tasks are saturated for all four models, so the assembly-only view makes the remaining differences much easier to see.

## Key takeaway

- `gpt-4o-mini` and `claude-sonnet-4-5` are perfect on both assembly tasks across all 5 seeds.
- `gpt-4o` is still near-perfect, with only a small `gibson_01` efficiency penalty.
- `claude-haiku-4-5` is the only model with a real task-success miss on this slice: `golden_gate_01` falls to `0.910` because one seed produced an incorrect final transformant report despite perfect decision quality.

## Assembly-task summary

| Model | golden_gate_01 | gibson_01 |
|---|---:|---:|
| `openai/gpt-4o-mini` | 1.000 | 1.000 |
| `openai/gpt-4o` | 1.000 | 0.980 |
| `anthropic/claude-haiku-4-5` | 0.910 | 0.970 |
| `anthropic/claude-sonnet-4-5` | 1.000 | 1.000 |

## Files

- Overall-only assembly scorecard: [scorecard.png](current_frontier_5seed_assembly_plots/scorecard.png)
- Assembly axis breakdown: [axis_heatmap.png](current_frontier_5seed_assembly_plots/axis_heatmap.png)
- Full 5-seed frontier bundle: [current_frontier_5seed.md](current_frontier_5seed.md)

## Reproduce

```bash
python3 scripts/plot_scorecard.py \
  --log-dir results/current_openai_logs results/current_anthropic_logs \
            results/current_openai_logs_seed34 results/current_anthropic_logs_seed34 \
  --out-dir results/current_frontier_5seed_assembly_plots \
  --tasks golden_gate_01 gibson_01 \
  --models openai/gpt-4o-mini openai/gpt-4o anthropic/claude-haiku-4-5 anthropic/claude-sonnet-4-5
```
