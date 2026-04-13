# LabCraft Safety Scope

LabCraft is a public evaluation environment for benign molecular microbiology tasks. Its purpose is to measure agent performance on routine wet-lab reasoning while avoiding operationally useful content for high-risk biology.

## Included Scope

- BSL-1 and BSL-2 benign molecular microbiology only
- Standard laboratory *E. coli* strains such as DH5alpha, BL21, and Stbl3
- Benign phage-biology elements used in routine cloning workflows, including lambda and M13
- Standard cloning vectors and routine reagents such as LB, SOC, ampicillin, kanamycin, polymerases, ligases, and common buffers
- Text and structured-tool observations for simulated experiments

## Excluded Scope

- CDC select agents or any BSL-3 or BSL-4 organism
- Gain-of-function work, pathogen enhancement, or dual-use optimization language
- Mammalian virology, viral titer assays, or cytopathic-effect scoring
- Sequences longer than approximately 20 bp unless they are clearly limited to standard cloning-vector fragments
- Any task content intended to increase real-world capability for harmful biological work

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

## Reporting Concerns

If you identify a safety, sourcing, or scope concern, open a repository issue labeled `safety` or contact the maintainer through the repository profile associated with this project. Please include the file path, the concerning content, and why it appears to exceed the stated scope.
