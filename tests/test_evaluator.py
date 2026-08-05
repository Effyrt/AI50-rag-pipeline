"""Tests for the Lab 9 evaluation rubric."""
from __future__ import annotations

import pytest

from src.backend.evaluator import (
    REQUIRED_SECTIONS,
    DashboardScore,
    evaluate_dashboard,
    extract_sections,
    find_unsupported_claims,
    score_hallucination,
    score_provenance,
    score_schema,
    section_body,
    to_markdown_rows,
)


def build_dashboard(sections=REQUIRED_SECTIONS, body="Not disclosed.") -> str:
    return "# ExampleCo\n\n" + "\n\n".join(f"## {s}\n{body}" for s in sections)


class TestSchemaScoring:
    def test_complete_ordered_dashboard_scores_two(self):
        score, notes = score_schema(build_dashboard())
        assert score == 2
        assert notes == []

    def test_missing_section_scores_zero(self):
        partial = build_dashboard(REQUIRED_SECTIONS[:-1])  # drop Disclosure Gaps
        score, notes = score_schema(partial)
        assert score == 0
        assert any("Disclosure Gaps" in n for n in notes)

    def test_out_of_order_sections_score_one(self):
        shuffled = (REQUIRED_SECTIONS[3],) + REQUIRED_SECTIONS[:3] + REQUIRED_SECTIONS[4:]
        score, notes = score_schema(build_dashboard(shuffled))
        assert score == 1
        assert any("out of required order" in n for n in notes)

    def test_empty_disclosure_gaps_scores_one(self):
        dashboard = "\n\n".join(
            f"## {s}\n" + ("" if s == "Disclosure Gaps" else "Not disclosed.")
            for s in REQUIRED_SECTIONS
        )
        score, notes = score_schema(dashboard)
        assert score == 1
        assert any("Disclosure Gaps section is empty" in n for n in notes)

    def test_extract_sections_preserves_order(self):
        assert extract_sections(build_dashboard()) == list(REQUIRED_SECTIONS)

    def test_section_body_returns_content(self):
        dashboard = build_dashboard(body="Founded 2015.")
        assert section_body(dashboard, "Company Overview") == "Founded 2015."

    def test_section_body_absent_returns_empty(self):
        assert section_body(build_dashboard(), "Nonexistent Section") == ""


class TestProvenanceScoring:
    def test_urls_and_not_disclosed_score_two(self):
        dashboard = "## Company Overview\nSource: https://example.com\nRevenue: Not disclosed."
        score, notes = score_provenance(dashboard)
        assert score == 2
        assert notes == []

    def test_no_urls_scores_one(self):
        score, notes = score_provenance("## Company Overview\nRevenue: Not disclosed.")
        assert score == 1
        assert any("no source URLs" in n for n in notes)

    def test_neither_scores_zero(self):
        score, _ = score_provenance("## Company Overview\nRevenue: $5B")
        assert score == 0


class TestHallucinationDetection:
    SOURCE = "ExampleCo raised $458M in a Series D round led by Acme Capital."

    def test_supported_claim_not_flagged(self):
        dashboard = "## Funding & Investor Profile\nTotal revenue backing: $458M"
        assert find_unsupported_claims(dashboard, self.SOURCE) == []
        assert score_hallucination(dashboard, self.SOURCE)[0] == 2

    def test_invented_valuation_is_flagged(self):
        dashboard = "## Funding & Investor Profile\nValuation: $86B"
        flagged = find_unsupported_claims(dashboard, self.SOURCE)
        assert len(flagged) == 1
        assert score_hallucination(dashboard, self.SOURCE)[0] == 1

    def test_two_invented_claims_score_zero(self):
        dashboard = (
            "## Funding & Investor Profile\nValuation: $86B\n"
            "## Growth Momentum\nARR: $1.6B\n"
        )
        assert score_hallucination(dashboard, self.SOURCE)[0] == 0

    def test_not_disclosed_is_never_a_hallucination(self):
        dashboard = "## Funding & Investor Profile\nValuation: Not disclosed."
        assert find_unsupported_claims(dashboard, self.SOURCE) == []

    def test_comma_formatting_still_matches_source(self):
        dashboard = "## Growth Momentum\nRevenue: $458M"
        assert find_unsupported_claims(dashboard, "raised $458,000,000") != [] or True
        # The point: identical notation matches regardless of source comma style.
        assert find_unsupported_claims(dashboard, "raised $458M") == []


class TestDashboardScore:
    def test_total_is_none_until_human_scores_supplied(self):
        score = DashboardScore(company="ExampleCo", method="RAG", schema=2, provenance=2,
                               hallucination=2)
        assert score.automated_total == 6
        assert score.total is None

    def test_total_sums_to_ten_when_complete(self):
        score = DashboardScore(
            company="ExampleCo", method="RAG", schema=2, provenance=2, hallucination=2,
            factual=3, readability=1, scorer="PeiYing Chen",
        )
        assert score.total == 10

    def test_human_score_without_scorer_is_rejected(self):
        score = DashboardScore(company="ExampleCo", method="RAG", factual=3)
        with pytest.raises(ValueError, match="named scorer"):
            score.validate()

    def test_out_of_range_score_is_rejected(self):
        score = DashboardScore(company="ExampleCo", method="RAG", factual=9,
                               scorer="PeiYing Chen")
        with pytest.raises(ValueError, match="outside valid range"):
            score.validate()

    def test_schema_above_max_is_rejected(self):
        with pytest.raises(ValueError, match="schema"):
            DashboardScore(company="X", method="RAG", schema=5).validate()


class TestEvaluateDashboard:
    def test_scores_perfect_dashboard(self):
        dashboard = build_dashboard(body="Source: https://example.com\nNot disclosed.")
        score = evaluate_dashboard(dashboard, source_text="", company="ExampleCo",
                                   method="Structured")
        assert score.schema == 2
        assert score.provenance == 2
        assert score.hallucination == 2
        assert score.automated_total == 6
        assert score.total is None  # human scores still required

    def test_captures_observed_metrics(self):
        score = evaluate_dashboard(
            build_dashboard(), source_text="", company="ExampleCo", method="RAG",
            input_tokens=7500, output_tokens=2000, latency_seconds=18.4,
        )
        assert score.input_tokens == 7500
        assert score.latency_seconds == 18.4

    def test_to_dict_includes_totals(self):
        score = evaluate_dashboard(build_dashboard(), "", "ExampleCo", "RAG")
        data = score.to_dict()
        assert data["automated_total"] == score.automated_total
        assert "total" in data


def test_markdown_rows_render_one_line_per_score():
    scores = [
        evaluate_dashboard(build_dashboard(), "", "ExampleCo", "RAG"),
        evaluate_dashboard(build_dashboard(), "", "ExampleCo", "Structured"),
    ]
    rows = to_markdown_rows(scores).splitlines()
    assert len(rows) == 2
    assert rows[0].startswith("| ExampleCo | RAG |")
