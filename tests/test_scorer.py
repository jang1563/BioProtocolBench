"""Tests for the judge and scorer logic."""

from src.judge import parse_judge_grade, format_judge_prompt


class TestParseJudgeGrade:
    def test_pass(self):
        assert parse_judge_grade("GRADE: PASS\nThe agent correctly identified...") == 1.0

    def test_fail(self):
        assert parse_judge_grade("GRADE: FAIL\nThe agent did not...") == 0.0

    def test_pass_no_space(self):
        assert parse_judge_grade("GRADE:PASS") == 1.0

    def test_fail_no_space(self):
        assert parse_judge_grade("GRADE:FAIL") == 0.0

    def test_pass_lowercase(self):
        assert parse_judge_grade("grade: pass") == 1.0

    def test_ambiguous_defaults_to_fail(self):
        assert parse_judge_grade("I'm not sure about this response") == 0.0

    def test_pass_in_text_only(self):
        assert parse_judge_grade("The agent would PASS this requirement") == 1.0

    def test_both_pass_and_fail_defaults_to_fail(self):
        # If both PASS and FAIL appear without the GRADE: prefix, default to fail
        assert parse_judge_grade("This could PASS or FAIL") == 0.0


class TestFormatJudgePrompt:
    def test_format_contains_all_fields(self):
        prompt = format_judge_prompt(
            protocol_text="Test protocol",
            agent_response="Test response",
            leaf_name="Error 1 detected",
            category="detection",
            requirement="Agent finds the error",
            grading_notes="Must mention step 3",
        )
        assert "Test protocol" in prompt
        assert "Test response" in prompt
        assert "Error 1 detected" in prompt
        assert "detection" in prompt
        assert "Agent finds the error" in prompt
        assert "Must mention step 3" in prompt
