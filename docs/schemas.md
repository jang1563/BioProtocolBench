# LabCraft Data Schemas

This document defines the Phase 0 schema contract for LabCraft's static JSON artifacts. The goal is not to provide executable JSON Schema files yet, but to pin the required fields, meanings, and validation expectations before Phase 1 implementation.

## 1. Parameter Files

Path pattern: `data/parameters/*.json`

Each parameter file contains one or more parameter objects. The exact top-level container can be either:

- a JSON object with a `parameters` array, or
- a JSON object keyed by parameter identifier

Whichever container style is used in Phase 1, every parameter record must expose the following fields.

### Parameter record

```json
{
  "parameter_name": "transformation_efficiency_chemical_competent",
  "description": "Transformation efficiency distribution for chemically competent E. coli.",
  "units": "CFU per microgram DNA",
  "distribution": "log_normal",
  "parameters": {
    "mu": 16.1,
    "sigma": 0.6
  },
  "minimum_tier_required": "Gold",
  "tier_satisfied": true,
  "citations": [
    {
      "title": "High efficiency transformation of Escherichia coli with plasmids",
      "doi": "10.1016/0378-1119(90)90336-P",
      "canonical_url": "https://doi.org/10.1016/0378-1119(90)90336-P",
      "year": 1990,
      "tier": "Gold",
      "citation_count_approx": 1000,
      "tier_justification": "Foundational, highly cited transformation-efficiency paper."
    }
  ],
  "notes": [
    "Optional implementation notes."
  ]
}
```

### Rules

- `parameter_name`: required string, globally unique within the file.
- `description`: required string.
- `units`: required string unless the parameter is dimensionless.
- `distribution`: required string for stochastic parameters. Deterministic thresholds may use `null` and provide a direct scalar in `parameters`.
- `parameters`: required object containing the numeric distribution or threshold values.
- `minimum_tier_required`: required enum, one of `Gold`, `Silver`, `Bronze`, `Copper`.
- `tier_satisfied`: required boolean. This can be materialized in the JSON or computed during validation, but the schema contract expects the field to exist by the time tests inspect the record.
- `citations`: required non-empty array.

### Citation object

Every citation object must contain:

```json
{
  "title": "string",
  "tier": "Gold",
  "tier_justification": "string",
  "doi": "10.xxxx/xxxx",
  "canonical_url": "https://...",
  "citation_count_approx": 250
}
```

Rules:

- `tier`: required enum, one of `Gold`, `Silver`, `Bronze`, `Copper`.
- `tier_justification`: required non-empty string.
- At least one of `doi` or `canonical_url` must be present and non-empty.
- `citation_count_approx` is required for `Gold` citations and optional otherwise.
- Parameter validation must confirm that at least one citation satisfies `minimum_tier_required`.

## 2. Ground Truth Files

Path pattern: `task_data/*/ground_truth.json`

Each task ground-truth file defines decision scoring, troubleshooting references, and efficiency expectations for a stochastic task.

### Top-level shape

```json
{
  "task_id": "transform_01",
  "decision_points": [
    {
      "id": "heat_shock_duration",
      "description": "Duration used during heat shock.",
      "matcher": {
        "tool_name": "transform",
        "match_strategy": "first_call"
      },
      "acceptable_values": {
        "type": "range",
        "min": 20,
        "max": 45,
        "optimal": 30,
        "units": "seconds"
      },
      "scoring_rule": "partial_credit",
      "citations": [
        {
          "doi": "10.1016/0378-1119(90)90336-P",
          "tier": "Gold",
          "tier_justification": "Foundational transformation protocol."
        }
      ]
    }
  ],
  "failure_diagnosis_map": {
    "no_colonies_due_to_skipped_recovery": {
      "canonical_diagnosis": "Recovery was skipped before plating.",
      "acceptable_variants": [
        "Cells needed recovery time before antibiotic selection."
      ],
      "judge_strategy": "llm_text_match",
      "citations": [
        {
          "canonical_url": "https://www.neb.com/",
          "tier": "Bronze",
          "tier_justification": "Authoritative vendor guidance for transformation workflow."
        }
      ]
    }
  },
  "efficiency_reference": {
    "optimal_tool_calls": 4,
    "max_reasonable_tool_calls": 7,
    "reagent_budget": {
      "soc_ml": 1.0,
      "plate_count": 4
    }
  }
}
```

### Rules

- `task_id`: required string matching the task directory name.
- `decision_points`: required non-empty array.
- `failure_diagnosis_map`: required object; values describe accepted troubleshooting diagnoses for known failure modes.
- `efficiency_reference`: required object.

### Decision point rules

- `id`: required unique string.
- `description`: required string.
- `matcher`: required object describing how the scorer identifies the corresponding tool call in the transcript.
- `acceptable_values`: required object. The exact shape depends on whether the decision is a range, enum set, boolean, free-text judgment target, or structured argument block.
- `scoring_rule`: required string such as `binary`, `partial_credit`, or `llm_judge`.
- `citations`: required non-empty array following the citation rules above.

### Efficiency reference rules

- `optimal_tool_calls`: required integer.
- `max_reasonable_tool_calls`: required integer.
- `reagent_budget`: required object keyed by reagent name or resource label.

## 3. Rubric Files

Path pattern: `task_data/*/rubric.json`

Rubric files store hierarchical scoring trees compatible with the existing `src/rubric_utils.py` loader.

### Top-level shape

```json
{
  "task_id": "transform_01",
  "task_title": "Transformation efficiency measurement",
  "total_leaf_nodes": 8,
  "rubric": {
    "name": "Task Evaluation",
    "weight": 1.0,
    "is_leaf": false,
    "children": [
      {
        "name": "Task Success",
        "weight": 0.4,
        "is_leaf": false,
        "children": []
      }
    ]
  }
}
```

### Rubric node rules

Each node follows the `RubricNode` contract already used in `src/rubric_utils.py`:

```json
{
  "name": "Correct heat shock timing",
  "weight": 0.5,
  "is_leaf": true,
  "category": "decision_quality",
  "requirement": "Agent selects a heat shock duration within the accepted literature range.",
  "grading_notes": "Full credit for 30 s; partial credit for 20-45 s depending on scoring rule."
}
```

Rules:

- `name`: required string.
- `weight`: required number.
- `is_leaf`: required boolean.
- `children`: required for non-leaf nodes, omitted or empty for leaf nodes.
- `category`, `requirement`, and `grading_notes`: required for leaf nodes and optional for internal nodes.

### Recommended top-level rubric dimensions

Phase 1 rubrics should use the four top-level dimensions defined in the implementation plan:

- `Task Success`
- `Decision Quality`
- `Troubleshooting`
- `Efficiency`

The weights should sum to `1.0` at every sibling level.
