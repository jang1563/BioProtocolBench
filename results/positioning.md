# BioProtocolBench vs. the State of the Art (April 2026)

Short literature-grounded audit placing BioProtocolBench against published biology-agent and lab-protocol benchmarks. The goal is to say clearly (a) what space this repo occupies, (b) where it is genuinely novel, and (c) where it is redundant with stronger prior work that a reviewer will already know about.

## Comparable benchmarks surveyed

| Benchmark | Year | Modality | Scale | Scoring | Source |
|---|---|---|---|---|---|
| **ProtocolQA** (inside LAB-Bench) | 2024 | Text-only MCQ | 108 questions | Exact-match | Laurent et al., *LAB-Bench* ([arXiv:2407.10362](https://arxiv.org/abs/2407.10362)) |
| **LAB-Bench** | 2024 | Text-only MCQ | 2,400+ questions across 8 categories | Exact-match | FutureHouse ([paper](https://arxiv.org/abs/2407.10362)) |
| **BioLP-bench** | 2024 | Text-only "find-the-fatal-mistake" | diverse protocols, 1 mistake each | Accuracy on mistake ID | Ivanov, Oxford Biosecurity Group ([bioRxiv 2024.08.21.608694](https://www.biorxiv.org/content/10.1101/2024.08.21.608694v1)) |
| **LabSafety Bench** | 2024 | Text-only MCQ (OSHA-aligned) | 765 questions | Exact-match | Zhou et al. ([arXiv:2410.14182](https://arxiv.org/abs/2410.14182)) |
| **BioProBench** | 2025 | Text-only, 5 tasks | 27K protocols → 556K instances | Rule-based per task | Liu et al. ([arXiv:2505.07889](https://arxiv.org/abs/2505.07889)) |
| **BoxingGym** | 2025 | **Interactive probabilistic environments** | 10 environments | Expected Information Gain + prediction error | Gandhi/Goodman et al. ([arXiv:2501.01540](https://arxiv.org/abs/2501.01540)) |
| **EXP-Bench** | 2025 | Interactive (repos + starter code) | 461 AI-research tasks | Multi-aspect partial credit | Kon et al. ([arXiv:2505.24785](https://arxiv.org/abs/2505.24785)) |
| **BioAgent Bench** | 2026 | Interactive bioinformatics pipelines | End-to-end RNA-seq / variant calling / metagenomics | **LLM-as-judge** grader | Fa et al. ([arXiv:2601.21800](https://arxiv.org/abs/2601.21800)) |
| **HeurekaBench (sc-HeurekaBench)** | 2026 | Interactive single-cell pipelines | Open-ended research questions | Reference-based + workflow verification | Panigrahi/Brbić et al. ([arXiv:2601.01678](https://arxiv.org/abs/2601.01678)) |
| **GPT-5 ProtocolQA Open-Ended + TroubleshootingBench** | 2025 | Text QA, some non-public | 108 open-ended + 52 protocols × 3 questions | Human PhD baseline; expert 80th percentile = 36.4% | OpenAI GPT-5 System Card ([PDF](https://cdn.openai.com/gpt-5-system-card.pdf)) |
| **OpenAI × Red Queen Bio wet-lab framework** | 2025 | **Real wet-lab** molecular cloning | 1 iterative optimisation task | Physical assay (79× cloning efficiency gain) | OpenAI announcement ([link](https://openai.com/index/accelerating-biological-research-in-the-wet-lab/)) |
| **BioProtocolBench (this repo)** | 2026 | **Interactive stochastic simulator** | 5 tasks × stochastic seeds | Deterministic hierarchical rubric + 4-axis trajectory scorer | This repo |

## Where BioProtocolBench is genuinely novel

Against the surveyed work, the defensible design points are:

1. **Interactive stochastic simulator + deterministic scorer.** Every BSL-2 biology benchmark indexed on Hugging Face Papers in 2024–2026 is either (a) text-only QA/MCQ (LAB-Bench, BioLP-bench, BioProBench, LabSafety Bench, ProtocolQA Open-Ended, TroubleshootingBench) or (b) interactive but scored by an LLM-as-judge (BioAgent Bench, HeurekaBench, sc-HeurekaBench). The combination of an interactive lab-simulator environment *plus* a fully deterministic regex/matcher-based trajectory scorer is not covered by any single comparable benchmark.
2. **Multi-axis rubric (task / decision-quality / troubleshooting / efficiency) scored separately**. BioProBench splits into five *tasks*; BoxingGym scores experimental-design vs. model-discovery; LAB-Bench reports eight *categories* but scores each as exact-match. None of these decomposes a single task into orthogonal axes the way this benchmark does. The axis decomposition is what made the ablation finding possible — you cannot detect "prompt engineering closed one axis while opening another" with a scalar score.
3. **Hierarchical citation-tier enforcement as a first-class test.** The `test_citations.py` contract (Gold/Silver/Bronze/Copper) gates every parameter, ground-truth value, and failure diagnosis on having a traceable public source. LAB-Bench and LabSafety Bench use human verification but do not enforce source provenance automatically. BioProBench uses 27K published protocols but does not expose the provenance chain at the parameter level.
4. **Seeded determinism with stochastic variance.** Same sample_id → same seed (SHA-256 hashed) → bit-identical trajectory. The 5-seed eval at N=5 exposed ~0.27 stddev on the `task_success` axis; that variance is real environmental stochasticity, not sampling noise, and it is measurable because the seeds are auditable. Most text-only benchmarks cannot surface this because there is no stochasticity in the environment to begin with.
5. **Full Inspect AI plugin compliance.** Every task registers as a standard `@task` entry point, so a reviewer can clone the repo and run `inspect eval src/inspect_task.py@clone_01 --model openai/gpt-4o` without any bespoke harness. BoxingGym, EXP-Bench, and BioAgent Bench each ship their own custom runner.

## Where BioProtocolBench is genuinely weaker than prior work

To reviewers at Anthropic / OpenAI / DeepMind who will already know the references above, the honest pre-empts are:

- **Scale is small.** BioProBench has 556K task instances (26K × ~20 derived each); BioProtocolBench has 5 tasks. Scale alone makes BioProBench a stronger test-bed for statistical claims about model capability.
- **No real wet-lab grounding.** OpenAI's Red Queen Bio collaboration executed *actual physical molecular cloning experiments* with GPT-5 and measured outcomes by physical assay. BioProtocolBench's stochastic simulator has citation-backed parameters but the agent never touches real biology. For claims about real-world capability uplift this is a hard ceiling.
- **No human baseline.** TroubleshootingBench was baselined against 12 PhD experts (80th percentile = 36.4%). Every stddev figure in this repo is agent-vs-agent. A single expert-graded seed on each task would contextualise the scores.
- **Task surface is execution-reliability-heavy.** As the analysis already admits, the hardest task (`transform_01`, mean 0.50) is mostly punishing agents for dropping one of four reported numbers or missing a consistency keyword — not for reasoning depth. BoxingGym and EXP-Bench score scientific reasoning and hypothesis revision, which is a harder and more interesting target.
- **Only one prompt-variant ablation so far.** The growth_01 ablation is a good start but a single verbose prompt is not a proper sensitivity sweep. LAB-Bench and BioProBench both include multiple prompt-formatting ablations.

## What the survey *validates* about the repo

- The scorer-as-trajectory-parser (not LLM-as-judge) approach is directly validated by AgentRewardBench ([arXiv:2504.08942](https://arxiv.org/abs/2504.08942)), which found rule-based scoring *underreports* success and LLM judges vary substantially. The repo's tradeoff (auditable + reproducible but brittle on final-answer formatting) is a well-known one in the 2025–2026 literature.
- The ablation finding — that prompt-engineering one axis can move another axis in the opposite direction — is the kind of finding that a text-only benchmark cannot surface because it has only a single scoring axis. This is a genuine contribution.
- The two latent infrastructure bugs surfaced by adversarial seed exploration ([src/environment/operations.py](../src/environment/operations.py) `_resolve_ligation_fragment_id`, [src/tools/lab_tools.py](../src/tools/lab_tools.py) tool-error wrapping) are exactly the class of failure mode that Multi-Docker-Eval ([arXiv:2512.06915](https://arxiv.org/abs/2512.06915)) argues is the main SWE-agent bottleneck — "environment construction." Finding two such bugs via agent traces is consistent with that literature.

## Recommended framing for a portfolio reviewer

The honest one-sentence pitch is:

> **BioProtocolBench is a small, reproducible interactive simulator for benign wet-lab reasoning with a deterministic multi-axis rubric.** It fills a gap between text-only protocol QA (LAB-Bench, BioProBench, BioLP-bench) and expensive real-world wet-lab frameworks (OpenAI × Red Queen Bio), and its axis-decomposed scoring surfaces model-vs-prompt tradeoffs that scalar benchmarks cannot.

It is *not* a BioProBench competitor on scale, *not* a BoxingGym competitor on reasoning-depth, and *not* a Red Queen Bio competitor on physical grounding. It is a different and complementary design point.

## Concrete next moves suggested by this literature scan

If the user wanted to strengthen the portfolio *against this competitive landscape* specifically, in descending leverage:

1. **Add a 1–2 person human baseline** on `transform_01` and `growth_01` (N=3–5 each). Even n=1 expert creates a publishable anchor point. TroubleshootingBench's 12-PhD baseline is the bar this aligns with.
2. **Split `transform_01` into an execution variant and a reasoning variant.** The current task is criticised fairly as execution-reliability. A sister task where the dilution strategy must be *derived* from cited stock concentrations (not given) would shift the scoring into reasoning.
3. **Write a 2–3 page methodology note** explicitly positioning against LAB-Bench and BioProBench. Cite DOIs. Reviewers at eval labs will want to see that you know the references.
4. **Run one additional prompt-sensitivity sweep** (3–5 variants, not 1) on the OpenAI growth_01 troubleshooting gap. Would turn a single-point ablation into a proper sensitivity curve.

None of these are required to ship; they are all ways of making the repo's defensive surface stronger against the specific benchmarks a senior reviewer will already have in their head.
