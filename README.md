# BioProtocolBench

An [Inspect AI](https://inspect.aisi.org.uk/) evaluation environment for measuring how well AI agents execute benign molecular-microbiology protocols inside a stochastic laboratory simulator.

Built on **LabCraft**, the underlying framework in [`src/`](src/). Each task places the agent in a seeded stochastic environment with a fixed tool set, a public protocol, and a citation-backed ground truth.

> Not to be confused with [BioProBench](https://github.com/YuyangSunshine/bioprotocolbench) (Liu et al., 2025), an NLP corpus of 556K instances. BioProtocolBench is an agent evaluation environment with three-axis trajectory scoring.

## What the agent does

Each task gives the agent:

- A **protocol prompt** (e.g., "measure transformation efficiency across four plasmid inputs")
- Access to lab-operation tools (`prepare_plate`, `transform`, `plate`, `incubate`, `count_colonies`, ...) and reference tools (`lookup_reagent`, `lookup_enzyme`, `check_safety`)
- A stochastic sample state seeded per run, with realistic noise on growth, plating, colony counts, etc.

The agent must plan the experiment, call tools in the right order, interpret observations, and report quantitative results. A trajectory scorer inspects the full interaction (tool calls, results, final answer) and grades it against a hierarchical rubric.

## Results

100 runs · 5 tasks · 4 frontier models · 5 stochastic seeds · April 2026 · total API cost ~$2.50

See **[results/analysis.md](results/analysis.md)** for per-task failure-mode analysis, [results/results.md](results/results.md) for per-sample scores, and [results/logs/](results/logs/) for the raw Inspect trajectories.

**Overall score by model × task** (mean ± stddev across 5 seeds, scored in [0, 1]):

| Task | gpt-4o-mini | gpt-4o | claude-haiku-4-5 | claude-sonnet-4-5 |
|---|---:|---:|---:|---:|
| `transform_01` | 0.570 ± 0.045 | 0.440 ± 0.108 | 0.500 ± 0.197 | 0.480 ± 0.179 |
| `growth_01` | 0.560 ± 0.152 | 0.580 ± 0.217 | 0.890 ± 0.246 | 0.880 ± 0.241 |
| `pcr_01` | 0.970 ± 0.027 | 0.950 ± 0.000 | 0.950 ± 0.000 | 0.950 ± 0.000 |
| `screen_01` | 0.900 ± 0.197 | 0.840 ± 0.219 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| `clone_01` | 0.722 ± 0.397 | 0.904 ± 0.103 | 0.940 ± 0.022 | 0.950 ± 0.000 |
| **Mean across tasks** | **0.744** | **0.743** | **0.856** | **0.852** |

Reproduce locally:

```bash
SEEDS=5 MODELS="openai/gpt-4o-mini openai/gpt-4o anthropic/claude-haiku-4-5 anthropic/claude-sonnet-4-5" \
  ./scripts/run_portfolio_eval.sh
python3 scripts/aggregate_eval_results.py        # results/logs/*.eval → results/results.md
```

## Key findings and limitations

### What this evaluation showed

1. **Provider-level behavioural differences dominate tier within this task set.** Both Anthropic models cluster at 0.85 ± 0.01; both OpenAI models cluster at 0.74 ± 0.01. The gap comes almost entirely from `growth_01`: Claude models score 1.00 on the troubleshooting axis across **10/10 seeds**, and GPT models score 0.00 on the same axis across all 10. This is not sampling noise — it is a deterministic behavioural split in how each provider's models narrate a late-time-course OD600 saturation event.

2. **`claude-sonnet-4-5` and `claude-haiku-4-5` are statistically indistinguishable on these tasks** (0.852 vs. 0.856 — haiku numerically wins by 0.004). The 6× price premium for sonnet buys nothing measurable here. This is a specific, narrow finding — it does not generalise beyond this five-task benchmark, but it is the kind of finding only a multi-seed eval can make visible.

3. **The benchmark did useful work by finding infrastructure bugs.** The eval surfaced two latent simulator issues that hand-written tests missed: (a) `ligate` rejecting the `digest_NNN` shorthand that `gpt-4o` consistently used, killing 5/5 samples; (b) tool-layer `ValueError`s propagating through Inspect as fatal task failures instead of agent-visible observations, nuking an entire 5-seed cell when a digest produced no output fragments. Both are fixed and live in [src/environment/operations.py](src/environment/operations.py) and [src/tools/lab_tools.py](src/tools/lab_tools.py). Adversarial agent exploration is doing the bug-finding work that formal tests cannot.

### Limitations I want to flag before you build on these numbers

- **N = 5 seeds is exploratory, not publishable.** Task-success stddev averages 0.27 per cell. One seed flipping changes the mean by 0.20. The haiku-vs-sonnet order could swap at N = 5 without surprise; the Anthropic-vs-OpenAI cluster gap of ~0.11 is robust.
- **`transform_01` is the single hardest task (0.50 mean), but it is execution-constrained, not reasoning-limited.** Models that fail it do so by dropping one of four CFU/µg values or missing the `"consistent"` keyword, not by getting the biology wrong. If the goal were to probe reasoning depth, this task would need a redesign.
- **The striking OpenAI growth-troubleshooting blind spot is unablated.** Is it a model-level limitation or prompt-sensitivity? I have not yet tested prompt variants that spell out the expected troubleshooting discussion. If a prompt tweak closes the gap, the "provider split" framing would become a "prompt-sensitivity split" — a materially different story.
- **The scorer is deterministic regex + exact-match on tool arguments**, not LLM-as-judge. That makes scoring reproducible and auditable, but final-answer parsing is brittle (e.g., `gpt-4o` seed 01 on `screen_01` malformed one field and lost task_success despite correct content).

These limitations are the top of the next-iteration backlog, documented in [results/analysis.md § "What a larger evaluation would add"](results/analysis.md).

## Tasks

| Task | Domain | Objective |
|---|---|---|
| `transform_01` | Chemical transformation of *E. coli* | Measure CFU/µg across four DNA masses (10 pg → 10 ng) |
| `growth_01` | Liquid-culture growth characterization | Determine growth parameters from OD600 time-course |
| `pcr_01` | PCR optimization | Choose conditions that yield specific amplification |
| `screen_01` | pUC blue-white colony screening | Confirm recombinants by colony PCR with ≥95% confidence |
| `clone_01` | Restriction cloning end-to-end | Digest + ligate 950 bp insert into pUC19 with EcoRI/BamHI, transform, and confirm recombinants |

Each task directory (`task_data/<task_id>/`) contains `rubric.json` (hierarchical scoring tree), `ground_truth.json` (expected values with citation metadata), and `SOURCES.md` (citations).

## Scoring

Trajectory scoring (see [src/trajectory_scorer.py](src/trajectory_scorer.py)) produces three axes per task:

- **Task success** — were the requested values reported, within tolerance of ground truth?
- **Decision quality** — were the experimental choices (dilutions, controls, replicates) sound?
- **Troubleshooting** — did the agent recognize and recover from stochastic failures (uncountable plates, contamination, etc.)?

Rubrics follow the hierarchical-tree methodology from [PaperBench](https://openai.com/index/paperbench/): leaf nodes are binary pass/fail, internal nodes are weighted averages.

$$S = \frac{\sum_j w_j \cdot s_j}{\sum_j w_j}$$

## Installation

```bash
git clone https://github.com/jang1563/BioProtocolBench.git
cd BioProtocolBench
pip install -e ".[dev]"
```

## Running

```bash
# Single task
inspect eval src.inspect_task:transform_01 --model openai/gpt-4o
inspect eval src.inspect_task:growth_01   --model anthropic/claude-sonnet-4-5
inspect eval src.inspect_task:pcr_01      --model openai/gpt-4o
inspect eval src.inspect_task:screen_01   --model openai/gpt-4o-mini
inspect eval src.inspect_task:clone_01    --model openai/gpt-4o-mini

# With a different grader model (trajectory scorer uses LLM-as-judge for some rubric leaves)
inspect eval src.inspect_task:transform_01 \
    --model anthropic/claude-sonnet-4-5 \
    -T grader_model=openai/gpt-4o
```

Task entry points are registered via the `inspect_ai` plugin in [pyproject.toml](pyproject.toml).

## Repository layout

```
BioProtocolBench/
├── README.md
├── LICENSE
├── SAFETY.md                 # Scope and safety policy
├── pyproject.toml
├── src/
│   ├── inspect_task.py       # @task entry points: transform_01, growth_01, pcr_01
│   ├── solvers.py            # Tool-augmented solvers per task
│   ├── environment/          # Stochastic lab simulator (state, operations, noise)
│   ├── tasks/                # Per-task prompts and sample builders
│   ├── tools/                # lookup_reagent / lookup_enzyme / check_safety / lab ops
│   ├── trajectory_scorer.py  # Three-axis scorer with rubric traversal
│   ├── rubric_utils.py       # Weighted tree scoring
│   └── judge.py              # LLM-judge prompts for qualitative leaves
├── data/
│   ├── reagent_database.json     # 85 common reagents
│   ├── enzyme_database.json      # 46 enzymes
│   ├── safety_database.json      # 44 chemicals with GHS hazards
│   └── parameters/               # Stochastic parameters with citations
├── task_data/
│   ├── transform_01/         # rubric.json, ground_truth.json, SOURCES.md
│   ├── growth_01/
│   └── pcr_01/
├── environments/             # Docker sandbox
├── docs/schemas.md           # JSON schema contract
└── tests/                    # Unit tests (environment, scorer, tools, rubrics)
```

## Safety scope

BioProtocolBench is deliberately limited to BSL-1/BSL-2 benign molecular microbiology with standard *E. coli* strains, standard cloning vectors, and routine reagents. Select agents, gain-of-function work, mammalian virology, and any content aimed at increasing real-world capability for harmful biology are explicitly excluded. Full policy in [SAFETY.md](SAFETY.md).

Every stochastic parameter, ground-truth value, and safety statement traces to a public, citable source. The citation-tier system (Gold / Silver / Bronze / Copper) is documented in [SAFETY.md](SAFETY.md) and enforced by [tests/test_citations.py](tests/test_citations.py).

## Testing

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

Tests cover the stochastic environment (determinism under seed, sample isolation), rubric loading, citation enforcement, tool contracts, and trajectory scoring (transcript parsing, CFU/µg reconstruction, rubric application).

## Related work

- [PaperBench](https://openai.com/index/paperbench/) (OpenAI, 2025) — introduced hierarchical rubric trees for AI evaluation.
- [ProtocolQA / LAB-Bench](https://arxiv.org/abs/2407.10362) (FutureHouse, 2024) — multiple-choice protocol troubleshooting.
- [BioProBench](https://github.com/YuyangSunshine/bioprotocolbench) (Liu et al., 2025) — large-scale NLP corpus; different scope from this agent environment.
- [Inspect AI](https://inspect.aisi.org.uk/) (UK AISI) — the evaluation framework this benchmark plugs into.

## License

BioProtocolBench is dual-licensed:

- **Source code** (everything under `src/`, `tests/`, `environments/`, `docs/`, build config) — [Apache License 2.0](LICENSE). Commercial use permitted.
- **Benchmark content** (everything under `task_data/` and `data/` — rubrics, ground-truth values, parameter distributions, citations, reagent/enzyme/safety databases) — [Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)](LICENSE-DATA). Free for research, teaching, and other non-commercial use with attribution.

For commercial use of the benchmark content (e.g., bundling with a commercial product, or evaluating models in a commercial training pipeline without a separate arrangement), please open an issue to discuss licensing.

See [NOTICE](NOTICE) for details on which files fall under which license.
