# Human Baseline Workflow

Minimal terminal workflow for collecting manual baseline runs on the two most informative snapshot tasks:

- `transform_01`
- `growth_01`

The goal is not to build a full multi-user annotation platform. It is to give a domain expert a reproducible way to run the seeded LabCraft tasks manually, save the exact tool transcript, and score the final answer with the same deterministic scorer used for agent runs.

## What it does

The script [scripts/run_human_baseline.py](../scripts/run_human_baseline.py):

- prints the exact task prompt
- initializes the same seeded environment used in the evals
- exposes the relevant lab tools and reference tools in a simple REPL
- records every tool call in scorer-compatible transcript format
- prompts for a final answer
- scores the run immediately using the same trajectory scorer as the agent benchmark

## Supported tasks

Initial support is intentionally narrow:

- `transform_01`
- `growth_01`

Those are the two snapshot tasks where a small expert baseline would add the most interpretive value.

## Run examples

From the repo root:

```bash
python3 scripts/run_human_baseline.py --task transform_01 --seed-index 0
python3 scripts/run_human_baseline.py --task growth_01 --seed-index 3
python3 scripts/run_human_baseline.py --task growth_01 --seed-index 2 --growth-prompt-variant verbose_troubleshoot
python3 scripts/run_human_baseline.py --task transform_01 --seed-index 1 --operator-id expert_a
python3 scripts/run_human_baseline_pilot.py --operator-id expert_a --list
python3 scripts/run_human_baseline_pilot.py --operator-id expert_a
python3 scripts/run_human_baseline_pilot.py --operator-id expert_a --all
```

By default the session is saved to:

```text
results/human_baseline_sessions/<operator_id>__<task>_seed_<NN>.json
```

For `growth_01` runs with a non-baseline prompt variant, the filename gets a variant suffix so distinct prompt conditions do not collide, for example:

```text
results/human_baseline_sessions/<operator_id>__growth_01__verbose_troubleshoot_seed_<NN>.json
```

You can override that with `--session-out /tmp/my_session.json`.

If you rerun the same session command and the JSON is still `in_progress`, the CLI now restores the recorded tool-state transcript instead of silently wiping it. Use the `history` command to review prior tool calls and recover generated IDs such as `culture_...`, `plate_...`, or `growth_...`. If the target JSON is already `completed`, the CLI refuses to overwrite it unless you choose a different `--session-out` path.

Before a session is finalized, the CLI shows a provisional deterministic score and task-specific formatting notes. That gives a human operator one last chance to fix missing labels, missing `"consistent"` wording on `transform_01`, or missing troubleshooting language on `growth_01` before the JSON is marked `completed`.

## REPL commands

- `help`: show command help
- `prompt`: print the task prompt again
- `tools`: list available tools and example JSON arguments
- `history`: print the recorded tool calls and observations for the current session
- `template`: print a scorer-friendly final-answer template
- `status`: show how many tool calls have been recorded
- `final`: enter a multiline final answer, review the provisional score and formatting notes, then choose `save`, `edit`, or `cancel`
- `quit`: exit without scoring

Tool calls use the format:

```text
<tool_name> <json arguments>
```

Example:

```text
prepare_media {"medium": "LB agar", "antibiotic": "ampicillin", "antibiotic_concentration_ug_ml": 100, "plate_count": 4}
```

## Why `seed-index` matters

The agent evals use deterministic seeded sample IDs such as:

- `transform_01_seeded_seed_00`
- `growth_01_seeded_seed_04`

This workflow uses the same seeded naming convention, so a human baseline on `--seed-index 4` is running the same stochastic instance that the agent saw for seed `04`.

## Output artifact

Each saved JSON session includes:

- task id
- seed index
- sample id
- operator id
- prompt variant
- prompt
- repo-relative scorer metadata paths
- transcript
- final answer
- deterministic score breakdown

That makes it possible to compare human and model performance on the same seeded instance without rerunning the environment.

## Recommended pilot seeds

Start with the curated seed pack in [results/human_baseline_seed_plan.md](../results/human_baseline_seed_plan.md).

That file narrows the first manual pass to the most informative seeded instances from the frozen snapshot:

- `transform_01`: seeds `00`, `02`, `04`
- `growth_01`: seeds `01`, `02`, `03`

The goal is to spend the first few expert sessions on the seeds where frontier models disagreed most sharply, rather than on random instances that are less diagnostic.

To work through that pack without copying commands by hand:

```bash
python3 scripts/run_human_baseline_pilot.py --operator-id expert_a --list
python3 scripts/run_human_baseline_pilot.py --operator-id expert_a
python3 scripts/run_human_baseline_pilot.py --operator-id expert_a --all
```

The pilot launcher reads the machine-readable seed manifest, checks the saved JSON status for each planned seed, resumes the first `in_progress` session if one exists, otherwise launches the next `pending` session, and skips `completed` seeds by default.

## Aggregate pilot results

Once you have one or more completed sessions in `results/human_baseline_sessions/`, generate a markdown summary with:

```bash
python3 scripts/aggregate_human_baseline.py
```

By default that writes:

```text
results/human_baseline_pilot.md
results/human_baseline_pilot.json
```

If no completed expert sessions are checked in yet, the script still writes placeholder artifacts at those paths so the repo has stable targets for future baseline results. The generated markdown page now also shows pilot-seed coverage and the frozen snapshot's same-seed model score range, while the JSON sidecar gives downstream scripts a stable structured interface.

If a seed has runs from multiple `growth_01` prompt variants, the aggregate report now shows the prompt split explicitly instead of rolling them into an indistinguishable coverage count.

To render the companion pilot plots, run:

```bash
python3 scripts/plot_human_baseline.py
```

By default that writes:

```text
results/human_baseline_plots/coverage.png
results/human_baseline_plots/seed_context.png
```

The seed-context plot uses distinct human markers for baseline versus `verbose_troubleshoot` growth runs so mixed prompt conditions are visually separable.

## Caveats

- This is a minimal expert-baseline scaffold, not a polished annotation app.
- It currently supports only `transform_01` and `growth_01`.
- The final answer is still parsed by the same deterministic regex-based scorer, so template compliance matters for humans too.
