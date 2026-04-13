"""LLM judge for grading individual rubric leaf nodes."""

from __future__ import annotations

JUDGE_SYSTEM_PROMPT = """\
You are an expert laboratory scientist grading an AI agent's analysis of a \
laboratory protocol. You will evaluate whether the agent's response satisfies \
a specific rubric requirement.

You must output EXACTLY one of these grades:
- GRADE: PASS — the requirement is clearly satisfied
- GRADE: FAIL — the requirement is not satisfied

Follow the grade with a brief explanation of your reasoning."""

JUDGE_TEMPLATE = """\
## Protocol Under Analysis
{protocol_text}

## Agent's Response
{agent_response}

## Rubric Requirement to Evaluate
**Leaf Node**: {leaf_name}
**Category**: {category}
**Requirement**: {requirement}
**Grading Notes**: {grading_notes}

## Instructions
Evaluate whether the agent's response satisfies the requirement above.
Consider partial matches — if the agent identifies the core issue but uses \
slightly different terminology, that may still satisfy the requirement.
Refer to the grading notes for guidance on what constitutes acceptable answers.

Output your grade as: GRADE: PASS or GRADE: FAIL
Then provide a one-sentence explanation."""


def format_judge_prompt(
    protocol_text: str,
    agent_response: str,
    leaf_name: str,
    category: str,
    requirement: str,
    grading_notes: str,
) -> str:
    """Format the judge prompt for a single leaf node evaluation."""
    return JUDGE_TEMPLATE.format(
        protocol_text=protocol_text,
        agent_response=agent_response,
        leaf_name=leaf_name,
        category=category,
        requirement=requirement,
        grading_notes=grading_notes,
    )


def parse_judge_grade(response: str) -> float:
    """Parse the judge's response to extract a binary grade.

    Returns:
        1.0 for PASS, 0.0 for FAIL
    """
    response_upper = response.upper()
    if "GRADE: PASS" in response_upper or "GRADE:PASS" in response_upper:
        return 1.0
    if "GRADE: FAIL" in response_upper or "GRADE:FAIL" in response_upper:
        return 0.0
    # Fallback: look for PASS/FAIL anywhere
    if "PASS" in response_upper and "FAIL" not in response_upper:
        return 1.0
    return 0.0
