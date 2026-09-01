"""Dashboard evaluation (Lab 9).

Implements the 10-point rubric used to compare the RAG and Structured pipelines:

    factual correctness   0-3   human-scored
    schema adherence      0-2   automated
    provenance use        0-2   automated
    hallucination control 0-2   automated
    readability           0-1   human-scored

The automated components are deterministic and need no API key, so they run in CI.
The human-scored components must be supplied by a named scorer: they are never
guessed, and a score submitted without a scorer is rejected so every number in
EVAL.md is attributable.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Iterable, Optional

# The exact 8 sections the dashboard prompt must emit, in order (Lab 7).
REQUIRED_SECTIONS: tuple[str, ...] = (
    "Company Overview",
    "Business Model and GTM",
    "Funding & Investor Profile",
    "Growth Momentum",
    "Visibility & Market Sentiment",
    "Risks and Challenges",
    "Outlook",
    "Disclosure Gaps",
)

# Figures the assignment forbids inventing ("Never invent ARR, MRR, valuation,
# customer logos, or pipeline").
UNVERIFIABLE_CLAIM_PATTERNS: tuple[tuple[str, str], ...] = (
    ("ARR", r"\bARR\b"),
    ("MRR", r"\bMRR\b"),
    ("valuation", r"\bvaluation\b"),
    ("revenue", r"\brevenue\b"),
)

# A monetary amount, e.g. $1.6B, $86 billion, $11,300,000.
MONEY_PATTERN = re.compile(
    r"\$\s?\d[\d,]*(?:\.\d+)?\s*(?:[KMB]\b|thousand|million|billion|trillion)?",
    re.IGNORECASE,
)

NOT_DISCLOSED = "not disclosed"


def extract_sections(dashboard: str) -> list[str]:
    """Return the level-2 headings of a dashboard, in document order."""
    return [m.strip() for m in re.findall(r"^##\s+(.+?)\s*$", dashboard, re.MULTILINE)]


def section_body(dashboard: str, section: str) -> str:
    """Return the text under a given level-2 heading, or '' when absent."""
    pattern = re.compile(
        rf"^##\s+{re.escape(section)}\s*$(.*?)(?=^##\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(dashboard)
    return match.group(1).strip() if match else ""


def score_schema(dashboard: str) -> tuple[int, list[str]]:
    """Score schema adherence out of 2.

    2 - all 8 required sections present, in order, with Disclosure Gaps non-empty
    1 - all 8 present but out of order, or Disclosure Gaps empty
    0 - at least one required section missing
    """
    found = extract_sections(dashboard)
    notes: list[str] = []

    missing = [s for s in REQUIRED_SECTIONS if s not in found]
    if missing:
        notes.append(f"missing sections: {', '.join(missing)}")
        return 0, notes

    positions = [found.index(s) for s in REQUIRED_SECTIONS]
    in_order = positions == sorted(positions)
    if not in_order:
        notes.append("sections present but out of required order")

    gaps_filled = bool(section_body(dashboard, "Disclosure Gaps"))
    if not gaps_filled:
        notes.append("Disclosure Gaps section is empty")

    return (2 if in_order and gaps_filled else 1), notes


def score_provenance(dashboard: str) -> tuple[int, list[str]]:
    """Score provenance use out of 2.

    2 - at least one source URL cited AND "Not disclosed." used for missing data
    1 - one of the two
    0 - neither
    """
    notes: list[str] = []
    has_urls = bool(re.search(r"https?://", dashboard))
    uses_not_disclosed = NOT_DISCLOSED in dashboard.lower()

    if not has_urls:
        notes.append("no source URLs cited")
    if not uses_not_disclosed:
        notes.append("never uses 'Not disclosed.' for missing data")

    return int(has_urls) + int(uses_not_disclosed), notes


def find_unsupported_claims(dashboard: str, source_text: str) -> list[str]:
    """Return unverifiable financial claims not supported by the source text.

    A line is flagged when it mentions a forbidden metric (ARR, MRR, valuation,
    revenue) alongside a concrete monetary amount that does not appear in the source
    text. Lines that say "Not disclosed." are never flagged - that is the correct
    behaviour, not a hallucination.
    """
    flagged: list[str] = []
    normalised_source = re.sub(r"[\s,]", "", source_text.lower())

    for line in dashboard.splitlines():
        if NOT_DISCLOSED in line.lower():
            continue
        if not any(re.search(p, line, re.IGNORECASE) for _, p in UNVERIFIABLE_CLAIM_PATTERNS):
            continue
        for amount in MONEY_PATTERN.findall(line):
            needle = re.sub(r"[\s,$]", "", amount.lower())
            if needle and needle not in normalised_source:
                flagged.append(line.strip())
                break

    return flagged


def score_hallucination(dashboard: str, source_text: str) -> tuple[int, list[str]]:
    """Score hallucination control out of 2 (higher is better).

    2 - no unsupported financial claims
    1 - exactly one
    0 - two or more
    """
    flagged = find_unsupported_claims(dashboard, source_text)
    return max(0, 2 - len(flagged)), [f"unsupported claim: {c}" for c in flagged]


@dataclass
class DashboardScore:
    """One dashboard's rubric score."""

    company: str
    method: str  # "RAG" | "Structured"

    # Automated
    schema: int = 0
    provenance: int = 0
    hallucination: int = 0

    # Human-scored - must be supplied explicitly, with a named scorer
    factual: Optional[int] = None
    readability: Optional[int] = None
    scorer: Optional[str] = None

    # Observed at generation time. These are the figures codelabs.md quotes; they
    # must come from a real run rather than being asserted.
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    latency_seconds: Optional[float] = None

    notes: list[str] = field(default_factory=list)

    @property
    def automated_total(self) -> int:
        """The 6 points scoreable without a human."""
        return self.schema + self.provenance + self.hallucination

    @property
    def total(self) -> Optional[int]:
        """Score out of 10, or None until human scores are supplied."""
        if self.factual is None or self.readability is None:
            return None
        return self.automated_total + self.factual + self.readability

    def validate(self) -> None:
        """Reject out-of-range scores, and human scores with no named scorer."""
        bounds = {
            "schema": (0, 2),
            "provenance": (0, 2),
            "hallucination": (0, 2),
            "factual": (0, 3),
            "readability": (0, 1),
        }
        for name, (low, high) in bounds.items():
            value = getattr(self, name)
            if value is not None and not low <= value <= high:
                raise ValueError(f"{name}={value} outside valid range {low}-{high}")

        if (self.factual is not None or self.readability is not None) and not self.scorer:
            raise ValueError(
                "human-scored fields require a named scorer so the score is attributable"
            )

    def to_dict(self) -> dict:
        data = asdict(self)
        data["automated_total"] = self.automated_total
        data["total"] = self.total
        return data


def evaluate_dashboard(
    dashboard: str,
    source_text: str,
    company: str,
    method: str,
    **observed,
) -> DashboardScore:
    """Score the automated portion of the rubric for one dashboard."""
    schema, schema_notes = score_schema(dashboard)
    provenance, provenance_notes = score_provenance(dashboard)
    hallucination, hallucination_notes = score_hallucination(dashboard, source_text)

    score = DashboardScore(
        company=company,
        method=method,
        schema=schema,
        provenance=provenance,
        hallucination=hallucination,
        notes=schema_notes + provenance_notes + hallucination_notes,
        **observed,
    )
    score.validate()
    return score


def score_dashboard(
    factual: int, schema: int, provenance: int, hallucination: int, readability: int
) -> int:
    """Sum the five rubric components into a score out of 10.

    Retained for compatibility with the original implementation.
    """
    return factual + schema + provenance + hallucination + readability


def to_markdown_rows(scores: Iterable[DashboardScore]) -> str:
    """Render scores as EVAL.md table rows."""
    return "\n".join(
        "| {company} | {method} | {factual} | {schema} | {provenance} | "
        "{hallucination} | {readability} | {total} |".format(
            company=s.company,
            method=s.method,
            factual="—" if s.factual is None else s.factual,
            schema=s.schema,
            provenance=s.provenance,
            hallucination=s.hallucination,
            readability="—" if s.readability is None else s.readability,
            total="—" if s.total is None else s.total,
        )
        for s in scores
    )
