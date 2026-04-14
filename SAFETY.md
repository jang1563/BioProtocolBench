# LabCraft Safety Scope

LabCraft is a public evaluation environment for benign biology tasks across several BSL-1/2 domains. Its purpose is to measure agent performance on routine wet-lab reasoning while avoiding any content that could increase real-world capability for harmful biology.

## Included Scope

- **BSL-1 and BSL-2 benign molecular microbiology**
  - Standard laboratory *E. coli* strains (DH5alpha, BL21, BL21(DE3), Stbl3)
  - Benign industrial/lab bacterial species (*B. subtilis*, *P. putida*) on an opt-in basis
  - Benign phage-biology elements used in routine cloning workflows (lambda, M13)
  - Standard cloning vectors (pUC19, pET, pGEX) and routine reagents (LB, SOC, ampicillin, kanamycin, polymerases, ligases, common buffers)
- **Benign yeast genetics**
  - *Saccharomyces cerevisiae* laboratory strains (BY4741, W303, S288C and their derivatives) for transformation, auxotrophic selection, and growth characterisation
- **In-vitro biochemistry on benign, non-toxic proteins only**
  - Model enzymes (β-galactosidase, alkaline phosphatase, restriction enzymes, DNA/RNA polymerases)
  - Fluorescent proteins (GFP, mCherry, mScarlet) and structural affinity tags (His-tag, MBP, GST, Strep-tag)
  - Standard host housekeeping proteins
  - Workflows: induction, cell lysis, affinity purification, SDS-PAGE, spectrophotometric activity assays, Michaelis–Menten kinetics
- **BSL-1 adherent mammalian cell lines for non-viral work**
  - Approved lines: HEK293, HeLa, NIH-3T3, CHO (and close derivatives thereof listed in `data/organisms/mammalian_lines.json`)
  - Operations: thawing, passaging, counting (trypan blue), non-viral transfection (Lipofectamine or equivalent), **benign reporter assays only** (GFP, mCherry, luciferase, β-galactosidase, SEAP)
- Text and structured-tool observations for simulated experiments

## Excluded Scope

These exclusions are **non-negotiable** and override the Included Scope wherever they overlap.

- **All viral work** — transduction, lentivirus / AAV / retrovirus production or titer, cytopathic-effect scoring, packaging lines, viral vectors as cargo in transfection
- CDC select agents; any BSL-3 or BSL-4 organism
- Gain-of-function work, pathogen enhancement, or dual-use optimisation language
- Mammalian virology, viral titer assays, or cytopathic-effect scoring
- Primary human or animal tissue; iPSCs, ESCs, organoids, 3D cultures
- Gene drives and their construction
- Flow cytometry involving cell sorting of primary cells
- Sequences > 20 bp unless they are clearly limited to standard cloning-vector fragments
- **Expression of toxins, virulence factors, cytokines, pore-forming proteins, receptor agonists/antagonists targeting human signalling, or any protein with therapeutic or offensive potential** — regardless of host (*E. coli*, yeast, or mammalian)
- Any task content intended to increase real-world capability for harmful biological work

## Provenance requirement for new organisms

Every strain, cell line, or host referenced in a task must appear in `data/organisms/*.json` with a public registry reference (ATCC, DSMZ, ECACC, EUROSCARF, Addgene, or equivalent) checked in at build time. The allowed registries and exact accession numbers are reviewable in `data/organisms/`.

## Public-Data Commitment

Every parameter, threshold, protocol template, reagent specification, and safety statement in LabCraft must trace to a public, citable source. Private lab notebooks, unpublished observations, anecdotal lab knowledge, blogs, and unsourced tutorials are not valid source material for the benchmark.

## Source Quality Tiers

LabCraft uses a four-tier source system:

- Gold: canonical, highly cited, peer-reviewed foundational sources
- Silver: peer-reviewed sources with DOI from reputable venues
- Bronze: authoritative reference material such as vendor specifications, regulatory documents, and curated databases
- Copper: attributed community protocol resources for non-critical context

Excluded sources are not used directly.

Core stochastic parameters must meet the tier requirements defined in the implementation plan and enforced by tests. When a suitable citation is unavailable, the parameter or claim does not enter LabCraft.

## Automated Scope Enforcement

LabCraft ships an always-on automated safety guard: `tests/test_scope_compliance.py` scans every task-surface file (`src/`, `data/`, `task_data/`, `docs/methodology.md` when present) for a reviewable list of exclusion keywords on every `pytest` run, and fails the suite if any match. The keyword list is in `tests/scope_exclusion_keywords.txt`. Files that legitimately discuss excluded content — this `SAFETY.md`, `results/positioning.md` (related-work discussion), `results/analysis.md` (findings), the scope-compliance test itself, and the keyword list — are explicitly allowlisted inside the test.

## Reporting Concerns

If you identify a safety, sourcing, or scope concern, open a repository issue labeled `safety` or contact the maintainer through the repository profile associated with this project. Please include the file path, the concerning content, and why it appears to exceed the stated scope.
