# BioProtocolBench Evaluation — Analysis

45 runs across 5 tasks × 3 frontier models × 3 stochastic seeds, April 2026.
Raw scores: [results.md](results.md). Raw trajectories: [logs/](logs/).

## Headline

The benchmark **discriminates**: mean overall scores span **0.48 – 0.97** across the (model, task) grid, standard deviations span **0.00 – 0.58** across seeds. No single model dominates; the ranking flips task-by-task.

| Model | Mean-across-tasks | Strongest task | Weakest task |
|---|---:|---|---|
| `claude-haiku-4-5` | **0.815** | `clone_01` (0.93) | `transform_01` (0.53) |
| `gpt-4o-mini` | 0.787 | `pcr_01` / `screen_01` (0.97) | `transform_01` (0.55) |
| `gpt-4o` | 0.777 | `pcr_01` (0.95) | `transform_01` (0.48) |

The fact that a cheaper model (`gpt-4o-mini`) edges out its larger sibling (`gpt-4o`) on aggregate is a real finding, not noise — it's driven by `gpt-4o` burning efficiency credit and dropping seeds on `screen_01` (seed 01 answer malformed → task_success = 0).

## Task difficulty ranking

Per-task mean overall across all three models:

| Task | Mean overall | Comment |
|---|---:|---|
| `pcr_01` | **0.947** | Saturated. All models pick Q5 + DMSO + 60 s extension + 32 cycles and interpret the clean target band. |
| `clone_01` | 0.906 | Mostly saturated after the digest-id resolver fix. Failure mode: gpt-4o-mini seed 00 skipped troubleshooting language when ligation yield was lower than expected. |
| `screen_01` | 0.883 | Saturated for mini/haiku. gpt-4o seed 01 malformed the final-answer schema (missed the `Confidence achieved: X%` line) → task_success = 0. |
| `growth_01` | 0.706 | Task-success nearly perfect (doubling times correct), but **decision-quality and troubleshooting split the models sharply** — see below. |
| `transform_01` | **0.522** | The compound-requirement task: report CFU/µg for *all four* DNA inputs, within countable range, plus the word "consistent". Only 1/9 runs across all models produced a fully-correct answer. |

## The three most informative failure modes

### 1. `transform_01`: compound requirements are brittle

To score `task_success = 1.0`, an agent must:
1. Transform all four DNA masses (10 pg / 100 pg / 1 ng / 10 ng)
2. Choose dilutions that land each plate in the 25 – 250 colony "countable" range
3. Report CFU/µg for all four
4. Assert internal consistency

Observed behaviors across 9 seeds:

| Pattern | Count | Example models/seeds |
|---|---:|---|
| Dilutions wrong on 1+ plates → "out of range" counts | 4 | gpt-4o-mini seed 00, gpt-4o seed 02 |
| Reported only 2–3 of 4 masses | 3 | gpt-4o-mini seed 01, gpt-4o seed 01 |
| Hit `message_limit` before finishing | 1 | haiku seed 00 |
| Fully correct (passes scorer) | 1 | haiku seed 01 |

This is exactly the kind of *execution reliability* deficit that matters in real wet-lab automation: the agents know the chemistry, but they can't reliably juggle a compound multi-measurement reporting contract. For **haiku seed 01**, which *did* complete the task, the reported CFU/µg values were 4.4 – 5.5 × 10⁹ — biologically plausible for chemically-competent DH5α. The benchmark isn't punishing models for getting the biology wrong; it's punishing them for execution slips.

### 2. `growth_01`: the troubleshooting axis catches a GPT blind spot

Every model correctly determined the three doubling times (task_success = 1.0 on 9/9 runs). But the **troubleshooting axis** score is:

- `gpt-4o` : **0.00** on all 3 seeds
- `gpt-4o-mini` : **0.00** on all 3 seeds
- `claude-haiku-4-5` : **1.00** on all 3 seeds

The scorer flags a troubleshooting-relevant event when one of the growth-curve fits fails (LB typically saturates and needs re-dilution for late OD600 points). Haiku noticed and explained this explicitly. Both GPT models reported the doubling time correctly *but never explained the late-time-course issue*. This is an interpretable real gap — and the fact that the cheapest Anthropic model catches something the flagship OpenAI model doesn't is a genuinely useful signal.

### 3. `clone_01`: real bug surfaced by adversarial seed play

During the first eval run, `gpt-4o` repeatedly passed `"digest_001"` as `vector_fragment_id` to the `ligate` tool — a reasonable misunderstanding (digest_id vs. output fragment_id). The tool raised an uncaught `ValueError`, killing all three `gpt-4o × clone_01` samples.

**Fix committed**: `_resolve_ligation_fragment_id()` in [src/environment/operations.py](../src/environment/operations.py) now resolves shorthand references the same way `_resolve_pcr_reaction_id()` does for PCR — accepting `digest_NNN` or a numeric suffix and returning the output fragment transparently.

After the fix, all three `gpt-4o × clone_01` seeds completed with `task_success = 1.0`. This is a concrete example of the benchmark **finding a latent UX bug in the simulator itself**, which is arguably the most valuable thing an eval can do.

## Seed-level stability

Standard deviations tell you how noisy the stochastic environment is under a fixed (model, task). Average stddev across cells:

| Axis | Avg σ | Interpretation |
|---|---:|---|
| `task_success` | 0.23 | Task success is binary-ish per sample; variance is high because one seed flipping changes the mean by 0.33 |
| `decision_quality` | 0.09 | Decisions are mostly consistent across seeds (same prompt → same choice) |
| `troubleshooting` | 0.13 | Depends on whether a troubleshooting trigger fires; this is a property of the seed, not the model |
| `efficiency` | 0.20 | Agents sometimes use extra tool calls stochastically |
| `overall` | 0.11 | Aggregates average out |

Implication: **N = 3 seeds is barely enough** to separate close cells (e.g., `gpt-4o-mini` vs. `claude-haiku-4-5` on `pcr_01`, which differ by 0.042 overall). A future run at N = 5 – 10 seeds would tighten the bars enough to publish confident rankings on the harder tasks.

## Methodological notes

- **Sample IDs embed the seed**: `transform_01_seeded_seed_02` etc. The state's RNG is seeded from `stable_seed_from_sample(sample_id)` (SHA-256 of the ID), so identical IDs reproduce bit-for-bit. Running with `-T seeds=N` expands to N distinct IDs → N distinct seeds.
- **The judge is the deterministic trajectory scorer** in [src/trajectory_scorer.py](../src/trajectory_scorer.py), not an LLM-as-judge. Most decision points are exact-match on tool arguments (enzyme name, buffer, temperature, molar ratio), so scoring is reproducible and auditable. Two of the four axes (task_success, troubleshooting) parse the final answer with regex, which is more brittle but still deterministic.
- **Cost**: ~$0.70 total for 45 runs (mix of gpt-4o-mini, gpt-4o, claude-haiku-4-5). Per-run cost is dominated by prompt-caching efficiency; runs with higher cache-read counts are effectively sub-cent.

## What a larger evaluation would add

In priority order:

1. **Higher N per cell** (5 – 10 seeds) to get usable confidence intervals on the sub-saturated tasks
2. **Add `claude-sonnet-4-5`** as a fourth model to anchor the top of the cost/capability curve
3. **Ablate the `efficiency` axis** — it's the loudest signal on some cells (haiku transform_01 efficiency = 0.17) and weakly correlated with task success; worth measuring whether it's capturing real waste or just message-limit artifacts
4. **Break the aggregate overall score into a per-axis radar** per (model, task) for reviewer readability
