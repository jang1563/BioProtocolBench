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

## Tasks

| Task | Domain | Objective |
|---|---|---|
| `transform_01` | Chemical transformation of *E. coli* | Measure CFU/µg across four DNA masses (10 pg → 10 ng) |
| `growth_01` | Liquid-culture growth characterization | Determine growth parameters from OD600 time-course |
| `pcr_01` | PCR optimization | Choose conditions that yield specific amplification |

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
