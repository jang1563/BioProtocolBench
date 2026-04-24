# Xaira Brief

BioProtocolBench now has two complementary layers.

The original LabCraft benchmark asks whether an agent can execute benign wet-lab workflows reliably inside a seeded stochastic simulator. The new Discovery Decision Track asks a different question: whether a biomedical agent can inspect perturbation-style evidence, choose the right next experiment, and interpret that result with an auditable scorer.

Why this matters for Xaira:

- Xaira’s public site says the company is building predictive and agentic AI models across the discovery-and-development stack.
- The current BioMedical AI Research Engineer role emphasizes multi-step reasoning, tool use, robust evaluation, and integration across biomedical data sources.
- Xaira’s 2025–2026 public announcements around X-Atlas/Orion and X-Cell point toward perturbation-driven data and predictive virtual-cell modeling as core parts of the platform.

Why this repo is still useful without overclaiming:

- It is not a Biomni-style general biomedical agent.
- It is not a FutureHouse-style autonomous scientific-discovery platform.
- It is not a physical wet-lab autonomy system.
- It is a compact evaluation harness for whether an agent makes the right perturbation-follow-up decision and explains that decision cleanly.

What the Discovery Decision Track evaluates:

- `perturb_followup_01`: can the agent resolve an ambiguous hit with one orthogonal assay?
- `target_prioritize_01`: can the agent rank candidate targets by signal, translation, and liability?
- `target_validate_01`: can the agent choose the right first validation assay for the lead target and interpret it?

Why this complements BioTeam-AI instead of duplicating it:

- BioTeam-AI is the stronger end-to-end systems story around agentic biomedical workflows.
- BioProtocolBench adds the evaluation and reliability story: deterministic seeds, task-specific tools, citation-backed metadata, and explicit scoring of task success, decision quality, troubleshooting, and efficiency.
- Together they tell a better Xaira story than either project alone: one shows you can build biomedical agents, and the other shows you know how to measure whether those agents make good scientific decisions.

Relevant public sources:

- Xaira homepage: https://www.xaira.com/
- Xaira approach: https://www.xaira.com/our-approach
- Xaira BioMedical AI Research Engineer role: https://job-boards.greenhouse.io/xairatherapeutics/jobs/5005200007
- X-Atlas/Orion announcement (June 17, 2025): https://www.businesswire.com/news/home/20250617146938/en/X-AtlasOrion-Xaira-Therapeutics-Unveils-Largest-Publicly-Available-Genome-Wide-Perturb-seq-Dataset-to-Power-Next-Generation-AI-for-Biology
- X-Cell announcement (March 17, 2026): https://www.businesswire.com/news/home/20260317710096/en/Xaira-Therapeutics-Launches-X-Cell-Its-First-Virtual-Cell-Model-Trained-on-the-Largest-Ever-Genome-Wide-Perturbation-Dataset-X-AtlasPisces
- Biomni paper: https://biomni.stanford.edu/paper.pdf
- FutureHouse platform: https://www.futurehouse.org/research-announcements/launching-futurehouse-platform-ai-agents
- OpenAI wet-lab framework: https://openai.com/index/accelerating-biological-research-in-the-wet-lab/
