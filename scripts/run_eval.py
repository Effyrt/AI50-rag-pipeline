#!/usr/bin/env python3
"""Generate and score both dashboards for a set of companies (Lab 9).

    python scripts/run_eval.py --companies anthropic,databricks,abridge,hebbia,xai

Writes, per company, under data/eval/<company>/:
    rag.md          the RAG-pipeline dashboard
    structured.md   the structured-pipeline dashboard
    scores.json     automated rubric scores plus observed tokens/latency

The automated rubric components (schema, provenance, hallucination - 6 of 10 points)
are filled in here. The human-scored components (factual 0-3, readability 0-1) are
left null on purpose: they must be supplied by a named scorer via --factual/--readability
or by editing scores.json, so every number in EVAL.md is attributable.

Requires OPENAI_API_KEY. Use --dry-run to exercise the scoring path with no API calls.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.backend.evaluator import evaluate_dashboard, to_markdown_rows  # noqa: E402

EVAL_DIR = REPO_ROOT / "data" / "eval"


def slug(name: str) -> str:
    return name.lower().replace(" ", "_").replace(".", "").replace("&", "and")


def load_source_text(company: str) -> str:
    """Concatenate the scraped clean-text for a company.

    The hallucination check needs the source material a dashboard should be grounded
    in. Returns '' when nothing has been scraped, in which case every concrete
    financial figure will be flagged - which is the correct, conservative outcome.
    """
    raw_dir = REPO_ROOT / "data" / "raw" / slug(company)
    if not raw_dir.exists():
        print(f"  ! no scraped text under {raw_dir}; hallucination scoring will be strict")
        return ""
    return "\n".join(
        p.read_text(errors="ignore") for p in raw_dir.rglob("*.txt")
    )


def generate_rag(company: str) -> tuple[str, dict]:
    from src.backend.rag_pipeline import RAGPipeline

    pipeline = RAGPipeline()
    start = time.time()
    dashboard = pipeline.generate_dashboard(company_name=company, top_k=15)
    return dashboard, {"latency_seconds": round(time.time() - start, 2)}


def generate_structured(company: str) -> tuple[str, dict]:
    from src.backend.api import generate_structured_dashboard_from_payload
    from src.backend.structured_pipeline import load_payload

    payload = load_payload(slug(company))
    if payload is None:
        raise FileNotFoundError(
            f"No assembled payload for '{company}'. Run the extractor and "
            f"payload assembler first (Lab 5/6)."
        )
    start = time.time()
    dashboard = generate_structured_dashboard_from_payload(
        payload.model_dump(mode="json")
    )
    return dashboard, {"latency_seconds": round(time.time() - start, 2)}


PLACEHOLDER_DASHBOARD = """## Company Overview
Not disclosed.

## Business Model and GTM
Not disclosed.

## Funding & Investor Profile
Not disclosed.

## Growth Momentum
Not disclosed.

## Visibility & Market Sentiment
Not disclosed.

## Risks and Challenges
Not disclosed.

## Outlook
Not disclosed.

## Disclosure Gaps
Generated in --dry-run mode; no source data was consulted.
"""


def evaluate_company(company: str, dry_run: bool, scorer: str | None) -> list[dict]:
    print(f"\n=== {company} ===")
    out_dir = EVAL_DIR / slug(company)
    out_dir.mkdir(parents=True, exist_ok=True)

    source_text = load_source_text(company)
    results = []

    for method, generator, filename in (
        ("RAG", generate_rag, "rag.md"),
        ("Structured", generate_structured, "structured.md"),
    ):
        print(f"  generating {method}...")
        try:
            if dry_run:
                dashboard, observed = PLACEHOLDER_DASHBOARD, {"latency_seconds": 0.0}
            else:
                dashboard, observed = generator(company)
        except Exception as exc:  # noqa: BLE001
            print(f"  ✗ {method} failed: {exc}")
            continue

        (out_dir / filename).write_text(dashboard)

        score = evaluate_dashboard(
            dashboard=dashboard,
            source_text=source_text,
            company=company,
            method=method,
            **observed,
        )
        if scorer:
            score.scorer = scorer

        print(
            f"  ✓ {method}: schema={score.schema}/2 provenance={score.provenance}/2 "
            f"hallucination={score.hallucination}/2 "
            f"(automated {score.automated_total}/6)"
        )
        for note in score.notes:
            print(f"      - {note}")

        results.append(score.to_dict())

    (out_dir / "scores.json").write_text(json.dumps(results, indent=2))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--companies",
        required=True,
        help="Comma-separated company names, e.g. Anthropic,Databricks",
    )
    parser.add_argument(
        "--scorer",
        help="Name of the person who will supply the human-scored components",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Exercise the scoring path with placeholder dashboards and no API calls",
    )
    args = parser.parse_args()

    companies = [c.strip() for c in args.companies.split(",") if c.strip()]
    if len(companies) < 5 and not args.dry_run:
        print(
            f"WARNING: Lab 9 requires at least 5 companies; got {len(companies)}",
            file=sys.stderr,
        )

    if not args.dry_run and not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY is not set. Use --dry-run to test scoring only.",
              file=sys.stderr)
        return 1

    all_scores = []
    for company in companies:
        all_scores.extend(evaluate_company(company, args.dry_run, args.scorer))

    print("\n" + "=" * 70)
    print("EVAL.md rows (automated components only; add factual + readability by hand)")
    print("=" * 70)
    print("| company | method | factual (0–3) | schema (0–2) | provenance (0–2) | "
          "hallucination (0–2) | readability (0–1) | total |")
    print("|---------|--------|---------------|--------------|------------------|"
          "----------------------|-------------------|-------|")

    from src.backend.evaluator import DashboardScore

    print(to_markdown_rows(DashboardScore(**{
        k: v for k, v in s.items()
        if k not in ("automated_total", "total")
    }) for s in all_scores))

    print(f"\nArtifacts written under {EVAL_DIR}")
    print("Next: supply factual/readability scores, then paste the rows into EVAL.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
