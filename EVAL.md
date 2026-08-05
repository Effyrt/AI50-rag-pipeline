# RAG vs Structured Evaluation (Lab 9)

> **STATUS: NOT YET RUN.** The rows below are empty because the evaluation has not been
> executed against real data. Nothing in this file is filled in with estimated or
> assumed values — a plausible-looking number here would be worse than a blank.
>
> To populate it, see [How to fill this in](#how-to-fill-this-in) below.

## Rubric (10 points)

| Component | Points | Scored by |
|---|---|---|
| Factual correctness | 0–3 | human — scorer must be named |
| Schema adherence | 0–2 | automated (`evaluator.score_schema`) |
| Provenance use | 0–2 | automated (`evaluator.score_provenance`) |
| Hallucination control | 0–2 | automated (`evaluator.score_hallucination`) |
| Readability / investor usefulness | 0–1 | human — scorer must be named |

## Results

Minimum 5 companies, both pipelines each (Lab 9 requirement).

| company | method | factual (0–3) | schema (0–2) | provenance (0–2) | hallucination (0–2) | readability (0–1) | total |
|---------|--------------|---------------|--------------|------------------|----------------------|-------------------|-------|
|         | RAG          |               |              |                  |                      |                   |       |
|         | Structured   |               |              |                  |                      |                   |       |
|         | RAG          |               |              |                  |                      |                   |       |
|         | Structured   |               |              |                  |                      |                   |       |
|         | RAG          |               |              |                  |                      |                   |       |
|         | Structured   |               |              |                  |                      |                   |       |
|         | RAG          |               |              |                  |                      |                   |       |
|         | Structured   |               |              |                  |                      |                   |       |
|         | RAG          |               |              |                  |                      |                   |       |
|         | Structured   |               |              |                  |                      |                   |       |

## Aggregate

| Pipeline | Mean total (/10) | Companies scored |
|---|---|---|
| RAG | | |
| Structured | | |

## Observed cost and performance

Taken from `data/eval/<company>/scores.json`, not estimated.

| Pipeline | Mean input tokens | Mean output tokens | Mean latency (s) |
|---|---|---|---|
| RAG | | |
| Structured | | |

## Per-company scoring rationale

One or two sentences per company, so each score is defensible under questioning.

<!-- e.g. Anthropic — Structured scored 2/2 on schema; RAG omitted "Growth Momentum". -->

## How to fill this in

1. **Prerequisites.** `OPENAI_API_KEY` set, and scraped text present under
   `data/raw/<company>/` (run the scraper first — the hallucination check needs the
   source material a dashboard should be grounded in). For the structured pipeline,
   assembled payloads must exist under `data/payloads/`.

2. **Choose the sample deliberately.** Include at least one company with a rich website
   (Anthropic, Databricks) *and* at least one with a thin one. The thin case is what
   actually exercises `"Not disclosed."` handling and the Disclosure Gaps section, which
   is where the two pipelines diverge most.

3. **Run the harness:**
   ```bash
   python scripts/run_eval.py \
     --companies anthropic,databricks,abridge,hebbia,xai \
     --scorer "<your name>"
   ```
   This writes `data/eval/<company>/{rag.md,structured.md,scores.json}` and prints the
   table rows to paste in above. The three automated components (6 of 10 points) are
   filled in for you.

4. **Supply the human scores.** Read each dashboard pair and score factual correctness
   (0–3) and readability (0–1). The harness rejects a human score with no named scorer,
   so every number stays attributable.

5. **Write the reflection.** `docs/REFLECTION.md`, ~1 page, citing only the figures in
   this file. Report what the data shows — including if RAG wins.

6. **Realign the codelab.** `codelabs.md` Step 12 has a metrics table with each row
   marked _to be measured_; fill it from this file.

## Known limitations to state in the reflection

- n=5 is a small sample; per-company variance will be large.
- Single scorer means no inter-rater reliability.
- Single run per pipeline; LLM output varies between runs at temperature > 0.
