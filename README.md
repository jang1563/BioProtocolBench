# ProtocolErrorBench

An [Inspect AI](https://inspect.aisi.org.uk/) evaluation environment for assessing how well AI agents can identify and fix errors in laboratory protocols.

> **Note**: This project is distinct from [BioProBench](https://github.com/YuyangSunshine/bioprotocolbench) (Liu et al., 2025), which is a large-scale NLP benchmark with 556K task instances across 5 tasks. ProtocolErrorBench is a focused agent evaluation environment with hierarchical rubric trees, database tool access, and three-axis scoring.

## Overview

ProtocolErrorBench presents AI agents with published laboratory protocols that contain 1-3 intentionally introduced errors. Agents must:

1. **Detect** the errors (which step, what is wrong)
2. **Explain** why each is an error (biochemical/practical reasoning)
3. **Correct** the error (propose a valid fix)

Agents have access to three reference databases via tools:
- `lookup_reagent` — 85 common laboratory reagents (buffers, dyes, chemicals, media)
- `lookup_enzyme` — 46 enzymes (restriction enzymes, polymerases, ligases, nucleases, etc.)
- `check_safety` — 44 chemicals with GHS hazards, PPE, and handling info

Grading uses **hierarchical rubric trees** (following [PaperBench](https://openai.com/index/paperbench/) methodology) with an LLM judge. Each leaf node is binary pass/fail; parent scores are computed as weighted averages.

## Error Categories

Errors span 10 categories with varying difficulty:

| Category | Difficulty | Example |
|---|---|---|
| Reagent concentration | Medium | 10× buffer used at 1× instead of diluted |
| Temperature error | Easy-Medium | Enzyme at 37°C when requires 16°C |
| Step ordering | Easy | Elution before wash in column purification |
| Missing critical step | Medium | No DNase treatment before RT-qPCR |
| Timing error | Medium | 30 sec extension for 5 kb PCR product |
| Reagent incompatibility | Hard | EDTA in restriction digest buffer |
| Safety violation | Easy | No fume hood for phenol-chloroform |
| Centrifugation error | Medium | Wrong g-force or rotor type |
| Storage condition | Medium | Enzyme at -80°C when requires -20°C |
| Biological implausibility | Hard | MOI of 1000 for lentiviral transduction |

## Installation

```bash
git clone <repo-url>
cd protocolerrobench
pip install -e .
```

## Running the Benchmark

```bash
# Run with GPT-4o as both agent and judge
inspect eval src.tasks:protocol_error_detection --model openai/gpt-4o

# Run with Claude as agent, GPT-4o as judge
inspect eval src.tasks:protocol_error_detection \
    --model anthropic/claude-3-5-sonnet-latest \
    -T grader_model=openai/gpt-4o

# Run on a single protocol for testing
inspect eval src.tasks:protocol_error_detection \
    --model openai/gpt-4o \
    --limit 1
```

## Repository Structure

```
protocolerrobench/
├── README.md
├── LICENSE
├── pyproject.toml
├── protocols/              # Protocol directories (50-80 total, in progress)
│   └── dna_miniprep_001/
│       ├── protocol.md              # Protocol with introduced errors (agent sees this)
│       ├── original_protocol.md     # Clean version (reference only)
│       ├── error_manifest.json      # Ground truth — what errors were introduced
│       └── rubric.json              # Hierarchical rubric tree
├── src/
│   ├── tasks.py            # Inspect @task definition
│   ├── solvers.py          # Tool-augmented solver chain
│   ├── tools.py            # lookup_reagent, lookup_enzyme, check_safety
│   ├── scorers.py          # Hierarchical rubric tree scorer with LLM judge
│   ├── judge.py            # Judge prompts and grade parsing
│   ├── rubric_utils.py     # RubricNode, weighted scoring, tree traversal
│   └── prompts.py          # System prompts
├── data/
│   ├── reagent_database.json    # 85 entries
│   ├── enzyme_database.json     # 46 entries
│   └── safety_database.json     # 44 entries
├── environments/
│   ├── Dockerfile
│   └── compose.yaml
├── tests/                  # 29 unit tests
└── research/               # Background research documents
```

## Rubric Schema

Each protocol has a `rubric.json` following this structure:

```json
{
  "protocol_id": "dna_miniprep_001",
  "num_errors_introduced": 2,
  "total_leaf_nodes": 6,
  "rubric": {
    "name": "Protocol Error Identification",
    "weight": 1.0,
    "is_leaf": false,
    "children": [
      {
        "name": "Error Detection",
        "weight": 0.4,
        "is_leaf": false,
        "children": [/* leaf nodes with category: "detection" */]
      },
      {
        "name": "Error Explanation",
        "weight": 0.3,
        "is_leaf": false,
        "children": [/* leaf nodes with category: "explanation" */]
      },
      {
        "name": "Correction Proposed",
        "weight": 0.3,
        "is_leaf": false,
        "children": [/* leaf nodes with category: "correction" */]
      }
    ]
  }
}
```

Weighted scoring formula (from PaperBench):

$$S_P = \frac{\sum_{j} w_j \cdot s_j}{\sum_{j} w_j}$$

where leaf scores are binary (pass=1, fail=0) and internal node scores are weighted averages of their children.

## Testing

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Status

**Scaffolding complete**:
- ✓ Repository structure, pyproject.toml, LICENSE
- ✓ Three reference databases (175 total entries)
- ✓ Inspect scaffolding (tasks, solvers, tools, scorers, judge, rubric_utils)
- ✓ Docker environment
- ✓ 29 unit tests passing
- ✓ First protocol (`dna_miniprep_001`) as template

**Next steps**:
- [ ] Curate 50-80 protocols with introduced errors
- [ ] Agent evaluation runs across 2-3 frontier models
- [ ] Judge validation (F1 against expert grades on 50-100 leaf nodes)
- [ ] Analysis report (per-category, per-error-type, judge reliability)

## Relation to Prior Work

- **[PaperBench](https://openai.com/index/paperbench/)** (OpenAI, 2025) — Introduced hierarchical rubric trees for AI evaluation. ProtocolErrorBench applies the same methodology to biological protocol analysis.
- **[ProtocolQA / LAB-Bench](https://arxiv.org/abs/2407.10362)** (FutureHouse, 2024) — 108 multiple-choice protocol troubleshooting questions. ProtocolErrorBench extends with hierarchical rubrics, agent tools, and three-axis scoring.
- **[BioProBench](https://github.com/YuyangSunshine/bioprotocolbench)** (Liu et al., 2025) — Large-scale NLP benchmark with 556K task instances. Fundamentally different scope: BioProBench is an NLP corpus; ProtocolErrorBench is an agent environment.
- **OpenAI GPT-5 System Card** — ProtocolQA Open-Ended (108 questions, 42% expert median) and TroubleshootingBench (52 non-public protocols, 36.4% expert 80th percentile). ProtocolErrorBench is the public, Inspect-based counterpart with richer scoring.

## License

MIT
