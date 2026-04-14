# BioProtocolBench Evaluation Results

Automatically aggregated from Inspect AI `.eval` logs in [results/logs](../results/logs).

## Per-model per-task summary

Mean overall score across the seed samples run for each (model, task) cell. `n` is the number of samples in that cell.

| Model | Task | n | overall (mean±std) | task_success | decision_quality | troubleshooting | efficiency |
|---|---|---:|---:|---:|---:|---:|---:|
| anthropic/claude-haiku-4-5 | `clone_01` | 3 | 0.933 ± 0.029 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.333 ± 0.289 |
| anthropic/claude-haiku-4-5 | `growth_01` | 3 | 0.817 ± 0.318 | 0.667 ± 0.577 | 0.889 ± 0.192 | 1.000 ± 0.000 | 0.833 ± 0.289 |
| anthropic/claude-haiku-4-5 | `pcr_01` | 3 | 0.925 ± 0.043 | 1.000 ± 0.000 | 0.917 ± 0.144 | 1.000 ± 0.000 | 0.500 ± 0.000 |
| anthropic/claude-haiku-4-5 | `screen_01` | 3 | 0.867 ± 0.231 | 0.667 ± 0.577 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| anthropic/claude-haiku-4-5 | `transform_01` | 3 | 0.533 ± 0.236 | 0.333 ± 0.577 | 0.611 ± 0.096 | 1.000 ± 0.000 | 0.167 ± 0.289 |
| openai/gpt-4o | `clone_01` | 3 | 0.933 ± 0.029 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.333 ± 0.289 |
| openai/gpt-4o | `growth_01` | 3 | 0.700 ± 0.000 | 1.000 ± 0.000 | 0.667 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 |
| openai/gpt-4o | `pcr_01` | 3 | 0.950 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.500 ± 0.000 |
| openai/gpt-4o | `screen_01` | 3 | 0.817 ± 0.318 | 0.667 ± 0.577 | 0.833 ± 0.289 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| openai/gpt-4o | `transform_01` | 3 | 0.483 ± 0.076 | 0.000 ± 0.000 | 0.722 ± 0.096 | 1.000 ± 0.000 | 0.667 ± 0.577 |
| openai/gpt-4o-mini | `clone_01` | 3 | 0.853 ± 0.185 | 1.000 ± 0.000 | 0.900 ± 0.100 | 0.667 ± 0.577 | 0.500 ± 0.500 |
| openai/gpt-4o-mini | `growth_01` | 3 | 0.600 ± 0.000 | 1.000 ± 0.000 | 0.333 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 |
| openai/gpt-4o-mini | `pcr_01` | 3 | 0.967 ± 0.029 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.667 ± 0.289 |
| openai/gpt-4o-mini | `screen_01` | 3 | 0.967 ± 0.029 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.667 ± 0.289 |
| openai/gpt-4o-mini | `transform_01` | 3 | 0.550 ± 0.050 | 0.000 ± 0.000 | 0.833 ± 0.167 | 1.000 ± 0.000 | 1.000 ± 0.000 |

## Per-sample detail

| Model | Task | Sample | overall | task | decision | trouble | efficiency |
|---|---|---|---:|---:|---:|---:|---:|
| openai/gpt-4o-mini | `transform_01` | `transform_01_seeded_seed_00` | 0.500 | 0.000 | 0.667 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `transform_01` | `transform_01_seeded_seed_01` | 0.600 | 0.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `transform_01` | `transform_01_seeded_seed_02` | 0.550 | 0.000 | 0.833 | 1.000 | 1.000 |
| openai/gpt-4o | `transform_01` | `transform_01_seeded_seed_00` | 0.500 | 0.000 | 0.667 | 1.000 | 1.000 |
| openai/gpt-4o | `transform_01` | `transform_01_seeded_seed_01` | 0.550 | 0.000 | 0.833 | 1.000 | 1.000 |
| openai/gpt-4o | `transform_01` | `transform_01_seeded_seed_02` | 0.400 | 0.000 | 0.667 | 1.000 | 0.000 |
| anthropic/claude-haiku-4-5 | `transform_01` | `transform_01_seeded_seed_00` | 0.350 | 0.000 | 0.500 | 1.000 | 0.000 |
| anthropic/claude-haiku-4-5 | `transform_01` | `transform_01_seeded_seed_01` | 0.800 | 1.000 | 0.667 | 1.000 | 0.000 |
| anthropic/claude-haiku-4-5 | `transform_01` | `transform_01_seeded_seed_02` | 0.450 | 0.000 | 0.667 | 1.000 | 0.500 |
| openai/gpt-4o-mini | `growth_01` | `growth_01_seeded_seed_00` | 0.600 | 1.000 | 0.333 | 0.000 | 1.000 |
| openai/gpt-4o-mini | `growth_01` | `growth_01_seeded_seed_01` | 0.600 | 1.000 | 0.333 | 0.000 | 1.000 |
| openai/gpt-4o-mini | `growth_01` | `growth_01_seeded_seed_02` | 0.600 | 1.000 | 0.333 | 0.000 | 1.000 |
| openai/gpt-4o | `growth_01` | `growth_01_seeded_seed_00` | 0.700 | 1.000 | 0.667 | 0.000 | 1.000 |
| openai/gpt-4o | `growth_01` | `growth_01_seeded_seed_01` | 0.700 | 1.000 | 0.667 | 0.000 | 1.000 |
| openai/gpt-4o | `growth_01` | `growth_01_seeded_seed_02` | 0.700 | 1.000 | 0.667 | 0.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `growth_01` | `growth_01_seeded_seed_00` | 0.450 | 0.000 | 0.667 | 1.000 | 0.500 |
| anthropic/claude-haiku-4-5 | `growth_01` | `growth_01_seeded_seed_01` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `growth_01` | `growth_01_seeded_seed_02` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `pcr_01` | `pcr_01_seeded_seed_00` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `pcr_01` | `pcr_01_seeded_seed_01` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| openai/gpt-4o-mini | `pcr_01` | `pcr_01_seeded_seed_02` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| openai/gpt-4o | `pcr_01` | `pcr_01_seeded_seed_00` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| openai/gpt-4o | `pcr_01` | `pcr_01_seeded_seed_01` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| openai/gpt-4o | `pcr_01` | `pcr_01_seeded_seed_02` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| anthropic/claude-haiku-4-5 | `pcr_01` | `pcr_01_seeded_seed_00` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| anthropic/claude-haiku-4-5 | `pcr_01` | `pcr_01_seeded_seed_01` | 0.875 | 1.000 | 0.750 | 1.000 | 0.500 |
| anthropic/claude-haiku-4-5 | `pcr_01` | `pcr_01_seeded_seed_02` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| openai/gpt-4o-mini | `screen_01` | `screen_01_seeded_seed_00` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `screen_01` | `screen_01_seeded_seed_01` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| openai/gpt-4o-mini | `screen_01` | `screen_01_seeded_seed_02` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| openai/gpt-4o | `screen_01` | `screen_01_seeded_seed_00` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o | `screen_01` | `screen_01_seeded_seed_01` | 0.450 | 0.000 | 0.500 | 1.000 | 1.000 |
| openai/gpt-4o | `screen_01` | `screen_01_seeded_seed_02` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `screen_01` | `screen_01_seeded_seed_00` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `screen_01` | `screen_01_seeded_seed_01` | 0.600 | 0.000 | 1.000 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `screen_01` | `screen_01_seeded_seed_02` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| openai/gpt-4o-mini | `clone_01` | `clone_01_seeded_seed_00` | 0.640 | 1.000 | 0.800 | 0.000 | 0.000 |
| openai/gpt-4o-mini | `clone_01` | `clone_01_seeded_seed_01` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| openai/gpt-4o-mini | `clone_01` | `clone_01_seeded_seed_02` | 0.970 | 1.000 | 0.900 | 1.000 | 1.000 |
| anthropic/claude-haiku-4-5 | `clone_01` | `clone_01_seeded_seed_00` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| anthropic/claude-haiku-4-5 | `clone_01` | `clone_01_seeded_seed_01` | 0.900 | 1.000 | 1.000 | 1.000 | 0.000 |
| anthropic/claude-haiku-4-5 | `clone_01` | `clone_01_seeded_seed_02` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| openai/gpt-4o | `clone_01` | `clone_01_seeded_seed_00` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
| openai/gpt-4o | `clone_01` | `clone_01_seeded_seed_01` | 0.900 | 1.000 | 1.000 | 1.000 | 0.000 |
| openai/gpt-4o | `clone_01` | `clone_01_seeded_seed_02` | 0.950 | 1.000 | 1.000 | 1.000 | 0.500 |
