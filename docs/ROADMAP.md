# Project ORBIT — Remediation Roadmap

**Repo:** `Effyrt/AI50-rag-pipeline`
**Baseline commit:** `648193e` · **Created:** 2026-08-04

A phase-by-phase, task-by-task plan for closing the gaps between what this repository
claims to do and what it currently does.

Work it top to bottom. Each phase ends in a gate — do not start the next phase until
the gate passes, because later phases depend on earlier output.

---

## Contents

- [Fix these first](#fix-these-first)
- [Phase overview](#phase-overview)
- [Phase 1 — Close the graded deliverable gaps](#phase-1--close-the-graded-deliverable-gaps)
- [Phase 2 — Make the pipeline actually run](#phase-2--make-the-pipeline-actually-run)
- [Phase 3 — Make the documentation true](#phase-3--make-the-documentation-true)
- [Phase 4 — Correctness and reliability](#phase-4--correctness-and-reliability)
- [Phase 5 — Security hardening](#phase-5--security-hardening)
- [Phase 6 — Cleanup and handover](#phase-6--cleanup-and-handover)
- [Task index](#task-index)
- [Progress tracker](#progress-tracker)

**Legend:** ⏱ estimate · 👤 owner · ⛓ depends on · ✅ done-when
**Owners:** **H** = Hemanth (platform / Airflow / GCP) · **P** = PeiYing (RAG / ML) · **O** = Om (API / UI / Docker)

---

## Fix these first

Five items that are individually small and disproportionately valuable. Roughly two hours total.

| # | Task | Time | Why |
|---|---|---|---|
| 1 | **T-1.5** — fill in `CONTRIBUTION_ATTESTATION.txt` | 5 min | Graded deliverable still reading `member1: __%` |
| 2 | **T-4.1** — replace hard-coded `gpt-4` at `rag_pipeline.py:88` | 20 min | The docs promise `gpt-4o-mini`; the legacy 8k model can also overflow at `top_k=15` |
| 3 | **T-1.1** — start the evaluation harness | — | Longest lead time on the critical path; everything in Phase 3 waits on its output |
| 4 | **T-3.4** — add the missing `.env.example` | 1 h | Both README and codelab tell you to `cp .env.example .env`; the file does not exist |
| 5 | **T-5.1** — remove `allUsers` from the dashboards bucket | 1 h | Generated content is currently world-readable |

---

## Phase overview

| Phase | Theme | Duration | Gate to exit |
|---|---|---|---|
| **1** | Close the graded deliverable gaps | 3–4 days | `EVAL.md` populated (5+ companies), reflection written, all 8 deliverables present |
| **2** | Make the pipeline actually run | 2–3 days | DAGs import clean and complete a 3-company end-to-end run |
| **3** | Make the documentation true | 1.5 days | No claim in the repo contradicts the code |
| **4** | Correctness and reliability | 2 days | No silent fallbacks, no masked failures, tests green in CI |
| **5** | Security hardening | 1 day | No public data surfaces, no credentials in history, least-privilege IAM |
| **6** | Cleanup and handover | 1.5 days | Clean clone → working local run, verified by a third party |

**Total ≈ 11–13 working days** across three people.

### Sequencing that matters

```
T-1.1 ──► T-1.2 ──► T-1.3 ──────────────► T-3.2
(harness)  (score 5)  (reflection)          (fix codelab results table)
                 └──────────────────────────────┘
                   Phase 3 cannot start until real
                   numbers exist to write down

T-2.1 ──► T-2.2 ──► T-2.3 ──► T-4.4
(one DAG   (imports  (Cloud Run  (delta refresh)
 dir)       resolve)  delegation)
```

Two independent chains — run them concurrently with different owners. The
evaluation chain (P and O) is the long pole; the DAG chain (H) can proceed
in parallel from day one.

**The one hard constraint:** T-3.2 rewrites the comparison table in `codelabs.md`, and
it cannot be done before T-1.2 produces measured numbers to put there.

---

## Phase 1 — Close the graded deliverable gaps

**Goal:** produce the Lab 9 comparison, which is the assignment's central question and
the one deliverable that was never started.
**Duration:** 3–4 days · **Owner:** P + O on the harness, all three on scoring

### T-1.1 — Build the evaluation harness ⏱ 1 day 👤 P + O

`src/backend/evaluator.py` is currently two lines that sum five integers. Expand it into
something that can generate, score, and persist a comparison.

**Automate what can be automated:**

| Rubric item | Points | How |
|---|---|---|
| Schema adherence | 0–2 | Assert all 8 required headings present, in order; `## Disclosure Gaps` non-empty |
| Hallucination control | 0–2 | Flag any ARR / MRR / valuation / customer-logo claim whose value does not appear in the retrieved source text — `Assignment.md` explicitly forbids inventing these |
| Provenance | 0–2 | Count source URLs / citations per section |

**Human-scored** (record the scorer's name alongside the score): factual correctness (0–3),
readability (0–1).

**Capture per generation:** input tokens, output tokens, wall-clock latency. These are the
figures `codelabs.md` currently states without any supporting artifact, and T-3.2 will need
real ones.

```bash
# New: scripts/run_eval.py
python scripts/run_eval.py --companies anthropic,databricks,abridge,hebbia,xai
# → data/eval/<company>/{rag.md,structured.md,scores.json}
```

✅ **Done when:** the script runs end-to-end for one company and emits both dashboards plus a populated `scores.json`.

### T-1.2 — Score 5+ companies and populate `EVAL.md` ⏱ 1 day 👤 all ⛓ T-1.1

`EVAL.md` is still the blank template — no rows, no scores. Lab 9 requires at least five
companies scored on both pipelines.

**Choose the sample deliberately.** Include at least one company with a rich website
(Anthropic, Databricks) *and* at least one with a thin one. The thin case is what actually
exercises `"Not disclosed."` handling and the disclosure-gaps section — which is where the
two pipelines diverge most, and where the Lab 7 checkpoint lives.

Populate: one row per company per method, all five sub-scores, totals out of 10, an
aggregate mean per pipeline, and 1–2 sentences of rationale per company so the scores hold
up under questioning.

```bash
# data/ artifacts are gitignored — negate for the eval evidence
echo '!data/eval/' >> .gitignore
```

✅ **Done when:** `EVAL.md` has ≥10 populated rows, the 10 generated dashboards are committed under `data/eval/`, and `"Not disclosed."` appears in at least one thin-data output.

### T-1.3 — Write the reflection ⏱ 3 h 👤 all ⛓ T-1.2

`docs/REFLECTION.md`, roughly one page, citing only measured results from T-1.2.

Cover: which pipeline scored higher and why · where each one failed · the latency and
token trade-off · what you would do differently with more time. Be explicit about limits —
n=5, single scorer, single-run variance.

> If the data contradicts the codelab's current thesis — if RAG actually wins — write that.
> A well-argued unexpected result reads better than a defended unsupported one, and T-3.2
> will realign the codelab to whatever you measured.

✅ **Done when:** committed, every figure traceable to `EVAL.md`, linked from `README.md`.

### T-1.4 — Expose `GET /rag/search` ⏱ 2 h 👤 O

Lab 4 task 3 asks for a retrieval-test endpoint. `RAGPipeline.search()` already exists at
`rag_pipeline.py:179`, but no route calls it — the API currently exposes only `/`,
`/companies`, `/dashboard/rag`, `/dashboard/structured`, `/companies/{name}/comparison`
and `/test`.

```python
@app.get("/rag/search")
def rag_search(q: str, company: str | None = None, k: int = 5):
    ...  # wrap RAGPipeline.search(); return chunk text, company, source URL, score
```

✅ **Done when:** searching `"funding"` and `"leadership"` returns topically correct chunks (the Lab 4 checkpoint), the transcript is committed, and the route appears at `/docs`.

### T-1.5 — Complete the contribution attestation ⏱ 5 min 👤 H

`CONTRIBUTION_ATTESTATION.txt` still contains `member1: __%` placeholders. The real split
exists only in the README table. Fill in the names and percentages (33.33% each); leave the
attestation statement verbatim.

✅ **Done when:** no `__%` remains and the file agrees with the README.

### T-1.6 — Resolve the hosting question ⏱ 4 h 👤 O

`gcp/build_and_deploy.sh` creates Cloud Run **Jobs** (batch) only. No Cloud Run **service**
was ever scripted, so the "cloud-hosted app" requirement has no URL behind it and the README
quick-start is localhost-only.

Pick one and document it:

- **(a) Recommended — deploy both as Cloud Run services** with `--min-instances=0`. Add the
  `gcloud run deploy` calls to `build_and_deploy.sh`, point Streamlit's `API_BASE`
  (`streamlit_app.py:17`) at the API service URL, and record both URLs in the README.
- **(b) Declare local-only** via `docker compose`, fix the README quick-start, and flag the
  deviation for the grader.

✅ **Done when:** either two live URLs are in the README or the deviation is documented — and either way `docker compose up` from a clean clone serves :8000 and :8501 (Lab 10 checkpoint), with the transcript committed.

### 🚪 Phase 1 gate

- [ ] `EVAL.md` populated, ≥5 companies, both pipelines
- [ ] `docs/REFLECTION.md` written from measured data
- [ ] `/rag/search` live, Lab 4 checkpoint demonstrated
- [ ] Attestation complete
- [ ] Hosting decided and documented
- [ ] Every deliverable in `Assignment.md` §Deliverables accounted for

---

## Phase 2 — Make the pipeline actually run

**Goal:** the DAGs match their documentation and can be executed by someone who did not
write them. As committed, two of the three cannot succeed.
**Duration:** 2–3 days · **Owner:** H

### T-2.1 — Consolidate to one DAG directory ⏱ 2 h 👤 H

`dags/` and `airflow/dags/` hold divergent copies of the same DAGs. `setup_composer.sh`
uploads **only** `airflow/dags/*`, so `dags/` is dead code that still reads as authoritative.

1. Adopt `airflow/dags/` as the single source of truth.
2. Delete `dags/`, or reduce it to a README pointer.
3. Keep exactly the two DAGs Deliverable 4 names: `ai50_full_ingest_dag.py`, `ai50_daily_refresh_dag.py`.
4. Decide the fate of the third, `ai50_structured_dag.py` — merge it in or document it as intentional.
5. Resolve the schedule contradiction: `docs/AIRFLOW_USAGE_GUIDE.md` describes the daily
   refresh as manual-only, while `dags/ai50_daily_refresh_dag.py:198` sets `0 3 * * *`.
   Lab 3 requires `0 3 * * *`; make the docs match.

✅ **Done when:** one DAG tree, two required DAGs, schedules consistent between code and docs.

### T-2.2 — Make the DAGs importable ⏱ 3 h 👤 H ⛓ T-2.1

`dags/ai50_daily_refresh_dag.py:43` does `from scraper import CompanyScraper` and `:109`
does `from rag_pipeline import RAGPipeline`. Neither resolves in Composer — only
`airflow/dags/*.py` is uploaded, so the `src/backend/` package never ships. **As deployed,
these DAGs cannot succeed.**

Remove the bare imports; the work moves to Cloud Run in T-2.3.

✅ **Done when:** `airflow dags list-import-errors` returns empty against the local Airflow from T-2.4.

### T-2.3 — Delegate heavy work to Cloud Run Jobs ⏱ 4 h 👤 H ⛓ T-2.2

Both `dags/*.py` DAGs run 50 Playwright browsers and sentence-transformers **in-process on
the Airflow worker** (`ai50_daily_refresh_dag.py:41`, `ai50_full_ingest_dag.py:42`). This
contradicts `docs/AIRFLOW_USAGE_GUIDE.md`, which describes Cloud Run Job execution, and
creates an OOM risk on the worker.

`airflow/dags/ai50_structured_dag.py` already uses Cloud Run operators correctly — follow
that pattern for both required DAGs. Preserve per-company success/failure logging (Lab 3).

✅ **Done when:** every heavy task is a Cloud Run Job trigger and the DAG graph matches the diagram in the Airflow guide.

### T-2.4 — Local Airflow for development and demo ⏱ 4 h 👤 H

Provide a way to run and demonstrate both DAGs without depending on a managed environment.

```bash
# docker/docker-compose.airflow.yml — new
docker compose -f docker/docker-compose.airflow.yml up
# mounts airflow/dags/, LocalExecutor or standalone
```

✅ **Done when:** both DAGs parse with zero import errors locally, and trigger commands are documented in `docs/AIRFLOW_USAGE_GUIDE.md`.

### T-2.5 — Capture DAG run evidence ⏱ 1 h 👤 H ⛓ T-2.4

The repo has no proof any DAG ever completed — no screenshots, no logs. The Lab 2 and Lab 3
checkpoints both ask for a successful run.

Capture and commit under `docs/evidence/airflow-runs/`: grid/graph view of a green run for
each DAG, task logs for one successful scrape and one successful extract, and the run
history list.

✅ **Done when:** at least one green end-to-end run per DAG is documented.

### 🚪 Phase 2 gate

- [ ] One DAG directory, two required DAGs
- [ ] `airflow dags list-import-errors` empty
- [ ] Heavy work delegated to Cloud Run
- [ ] Local Airflow runs both DAGs
- [ ] 3-company end-to-end run green, log committed
- [ ] Run evidence captured

---

## Phase 3 — Make the documentation true

**Goal:** no claim in the repo contradicts the code. Deliberately placed after Phase 1 —
the results table cannot be corrected until real results exist.
**Duration:** 1.5 days · **Owner:** P on RAG claims, O on run instructions, all on the results table

### T-3.1 — Correct the RAG architecture claims ⏱ 2 h 👤 P

Three claims are wrong in both `README.md` and `codelabs.md`:

| Documented | Actual |
|---|---|
| FAISS | **Chroma** — `rag_pipeline.py:14`, `:96`, `:104` |
| OpenAI `text-embedding-3-small`, 1536-dim | **`sentence-transformers/all-MiniLM-L6-v2`, 384-dim, runs locally** — `rag_pipeline.py:13`, `:36` |
| `gpt-4o-mini` | `gpt-4` — `rag_pipeline.py:88`; true only after T-4.1 |

Also: measure the "~7,000+ chunks indexed" figure or remove it. And drop `faiss-cpu` from
`requirements.txt` once you have grepped to confirm it is genuinely unused.

> The local embedding model is a good engineering choice — fast, no API dependency. Fix the
> documentation to match the code; do not change the code to match the documentation.

✅ **Done when:** vector DB, embedding model, dimensionality, and LLM all match the code in both documents.

### T-3.2 — Substantiate or remove the results table ⏱ 4 h 👤 all ⛓ T-1.2

`codelabs.md` §12 publishes 94% vs 78% data accuracy, 2% vs 18% hallucination rate, 100% vs
65% format consistency, plus token and latency figures, under a heading reading "Real
Production Results". Nothing in the repository produces those numbers, and `EVAL.md` — the
document that would support them — is empty.

Replace every figure with measured values from T-1.2, each carrying its source
(`n=5, see EVAL.md`), or delete the table.

Also replace the illustrative sample dashboards: the current worked example is OpenAI, which
is **not in `data/forbes_ai50_seed.json`**. A grader checking against the 50-company list
will notice.

✅ **Done when:** every quantitative claim in `codelabs.md` traces to `EVAL.md`, and no sample output is invented.

### T-3.3 — Fix run instructions and structure docs ⏱ 3 h 👤 O

| Item | Fix |
|---|---|
| README quick-start | `uvicorn src.api:app` → `src.backend.api:app`; `src/streamlit_app.py` → `src/frontend/streamlit_app.py`. Both paths broke in restructure commit `c9632b9`; `docker-compose.yml` already has them right |
| README structure block | Regenerate — still lists the pre-restructure flat `src/*.py` layout |
| `TEAMMATE_RAG_GUIDE.md` | Referenced by README, does not exist. Remove the reference or write the file |
| `PROJECT_STRUCTURE.txt` | Claims `EVAL.md`, `Assignment.md` and `docs/PE_Dashboard.md` are gitignored; all three are tracked. **Recommend deleting the file** — it duplicates the README and will drift again |
| Bucket count | README and `setup_gcp.sh` comments describe 4 buckets including `payloads` and `vector-index`; the script creates 3 |

✅ **Done when:** someone who did **not** write the docs follows the README on a clean clone and reaches a running API, with the transcript committed.

### T-3.4 — Add `.env.example` ⏱ 1 h 👤 O

README Local Setup and `codelabs.md` Step 1 both instruct `cp .env.example .env`. The file
does not exist, so the documented first step fails literally.

```bash
# .env.example — placeholders only, never real keys
OPENAI_API_KEY=sk-...                              # required: extraction + generation
GCP_PROJECT_ID=gen-lang-client-0653324487          # required for GCS mode
GCS_BUCKET_NAME=...                                # required for GCS mode
GOOGLE_APPLICATION_CREDENTIALS=./credentials.json  # optional: defaults to ADC
API_BASE=http://localhost:8000                     # Streamlit → API
RAG_LLM_MODEL=gpt-4o-mini                          # added by T-4.1
```

✅ **Done when:** every variable the code reads is present with a purpose comment, no real secrets, and a clean clone following the README reaches a running API.

### T-3.5 — One as-built architecture diagram ⏱ 4 h 👤 H ⛓ T-2.1

The repo carries three divergent architecture descriptions: the README ASCII diagram,
the `codelabs.md` diagram, and `docs/GCP_DEPLOYMENT_GUIDE.md` prose. Produce one canonical
version — what orchestrates, what executes where, which buckets actually exist — and have
all three documents reference it. State explicitly which DAG is authoritative and which
execution model it uses.

✅ **Done when:** one diagram, three references, zero divergent copies.

### 🚪 Phase 3 gate

- [ ] RAG architecture claims accurate in both documents
- [ ] Every metric traceable to `EVAL.md`
- [ ] Quick-start verified on a clean clone by a third party
- [ ] `.env.example` present
- [ ] No references to non-existent files
- [ ] One architecture diagram

---

## Phase 4 — Correctness and reliability

**Goal:** remove the silent failures — the places where the system returns plausible-looking
wrong answers instead of errors.
**Duration:** 2 days · **Owner:** P on T-4.1, O on T-4.2/T-4.5, H on the rest

### T-4.1 — Replace the hard-coded `gpt-4` ⏱ 20 min 👤 P

`src/backend/rag_pipeline.py:88` pins `model_name="gpt-4"` — the legacy 8k-context model —
while every document in the repo claims `gpt-4o-mini`.

```python
# src/backend/rag_pipeline.py — around line 88
model_name=os.getenv("RAG_LLM_MODEL", "gpt-4o-mini"),
```

```bash
grep -rn 'gpt-4"' src/ ; grep -rn 'model_name' src/    # confirm nothing else pins it
```

Beyond the documentation mismatch, this removes a live failure mode: `top_k=15` retrieved
chunks plus the system prompt can exceed the legacy model's 8k context window.

✅ **Done when:** no hard-coded `gpt-4` remains and one dashboard regenerates successfully.

### T-4.2 — One source of truth for data access ⏱ 4 h 👤 O

Three related defects with one fix:

- `api.py:66-80` reads local `data/structured` and `data/payloads` — both gitignored and
  absent from any container — while the same module also initialises a GCS client. Two
  sources of truth, only one ever populated.
- `structured_pipeline.py:9-12` silently falls back to `starter_payload.json` for **any**
  missing company, returning starter data labelled as the company that was requested.
- `streamlit_app.py:26-30` ships a hard-coded 5-company list that renders as though real
  when `/companies` fails.

Fix: read from GCS when configured, local otherwise, and log the active mode at startup.
Missing data returns **HTTP 404 with a clear message** — never mislabelled fallback data.
Remove the Streamlit fake list and surface a visible error instead.

✅ **Done when:** an unknown company returns 404, a failed `/companies` shows an error rather than plausible fake data, and the Lab 11 checkpoint holds (payloads written by a DAG run appear in the Streamlit list).

### T-4.3 — Remove error masking from the deploy scripts ⏱ 1 h 👤 H

Every `gcloud ... || echo "already exists"` in `gcp/*.sh` reports genuine failures as
success. This is how the next item stayed hidden.

```bash
if gcloud run jobs describe "$JOB" --region="$REGION" >/dev/null 2>&1; then
  gcloud run jobs update "$JOB" ... || { echo "FATAL: update failed"; exit 1; }
else
  gcloud run jobs create "$JOB" ... || { echo "FATAL: create failed"; exit 1; }
fi
```

✅ **Done when:** no `|| echo` remains in `gcp/*.sh` and every script runs `set -e` clean on a rerun.

### T-4.4 — Fix invalid gcloud flags ⏱ 1 h 👤 H ⛓ T-4.3

Two sets of invalid flags, both currently masked by T-4.3's pattern:

| File | Problem |
|---|---|
| `gcp/setup_composer.sh:24-33` | `--python-version=3.11` and `--web-server-machine-type=composer-n1-webserver-2` are Composer **1** flags passed to a Composer **2** image (`composer-2.9.0-airflow-2.9.3`). Both are rejected |
| `gcp/build_and_deploy.sh` | The extractor job uses `--timeout=1800`; the valid Cloud Run **Jobs** flag is `--task-timeout`. Note also that the extractor runs as a single task for all 50 companies × 5 passes, so 30 minutes may be too short regardless |

✅ **Done when:** both scripts run clean end-to-end from scratch, and `gcloud run jobs describe ai50-extractor --region=us-central1` shows the intended timeout.

### T-4.5 — Real tests and CI ⏱ 5 h 👤 O

`test_backend.py` is a print-based import script — no assertions, no runner, not wired to
anything.

Convert to `pytest` covering: the seed file loads exactly 50 companies · all Pydantic models
validate `starter_payload.json` · every API route returns its expected status with mocked
data · the 8-section schema validator accepts a good dashboard and rejects one with a
missing section.

Add `.github/workflows/ci.yml` running `pytest` plus `airflow dags list-import-errors`.

**Critical:** tests must pass with **no** `OPENAI_API_KEY` and **no** GCP credentials —
mock every external call, or CI is unusable.

✅ **Done when:** `pytest` is green locally and in CI with no credentials present.

### T-4.6 — True delta refresh ⏱ 5 h 👤 H ⛓ T-2.3

Lab 3 task 3 asks for re-scraping only changed pages. The current daily refresh
(`dags/ai50_daily_refresh_dag.py:41-100`) unconditionally re-scrapes all 50 companies into a
new dated folder — there is no change detection at all.

Persist a per-page content hash (or HTTP `ETag` / `Last-Modified`) in a GCS side-file, skip
extraction when unchanged, and log the skip count. Keep the dated per-run subfolders Lab 3
requires.

✅ **Done when:** a second consecutive run measurably skips unchanged pages, with the reduction recorded.

### 🚪 Phase 4 gate

- [ ] No hard-coded model strings
- [ ] No silent fallbacks anywhere in the data path
- [ ] No masked failures in deploy scripts
- [ ] All gcloud flags valid; scripts rerun clean
- [ ] CI green without credentials
- [ ] Delta refresh working

---

## Phase 5 — Security hardening

**Duration:** 1 day · **Owner:** H, with P on dependencies

### T-5.1 — Remove public bucket access ⏱ 1 h 👤 H

`gcp/setup_gcp.sh:71-72` makes the dashboards bucket world-readable and configures it as a
public website:

```bash
gsutil web set -m index.html -e 404.html gs://$DASHBOARD_BUCKET/
gsutil iam ch allUsers:objectViewer gs://$DASHBOARD_BUCKET/
```

Remove both lines and serve dashboards through the authenticated API or signed URLs.

```bash
gsutil iam ch -d allUsers:objectViewer gs://gen-lang-client-0653324487-dashboards
gsutil iam get gs://gen-lang-client-0653324487-dashboards   # expect no allUsers
```

✅ **Done when:** no bucket carries an `allUsers` or `allAuthenticatedUsers` binding, and a fresh `setup_gcp.sh` run cannot create one.

### T-5.2 — Credential audit ⏱ 2 h 👤 H

Scan the **full history**, not just the working tree:

```bash
git log -p --all | grep -nE 'sk-[A-Za-z0-9]{20,}|private_key|BEGIN PRIVATE KEY'
git log --all --diff-filter=A --name-only | grep -iE 'credentials|\.env$|key.*\.json'
```

Confirm `.gitignore` covers `.env`, `credentials.json`, `*-key.json`. **If any key is found,
rotate it immediately**, then assess whether history remediation is warranted. Also review
whether the personal email at `docs/AIRFLOW_USAGE_GUIDE.md:7` belongs in a repo that may be
made public.

✅ **Done when:** history is clean or every exposed key is rotated, and the result is recorded.

### T-5.3 — Least-privilege service accounts ⏱ 4 h 👤 H

`gcp/setup_gcp.sh:84-88` grants secret access to the **default** compute service account,
which every Cloud Run Job then runs as. Create dedicated service accounts per job with only
the buckets and secrets each one needs, scripted rather than console-applied.

✅ **Done when:** no job uses `<PROJECT_NUMBER>-compute@developer.gserviceaccount.com`, and IAM is reproducible from `setup_gcp.sh`.

### T-5.4 — Pin and prune dependencies ⏱ 4 h 👤 P

`requirements.txt` is mostly unpinned and carries unused heavyweights — and the whole file
is pushed into Composer via `--update-pypi-packages-from-file`, making environment rebuilds
slow and failure-prone.

- Pin every package.
- Remove after verifying: `selenium` and `webdriver-manager` (the code uses Playwright),
  `faiss-cpu` (the code uses Chroma). De-duplicate the repeated `google-cloud-storage`.
- Split `requirements.txt` (runtime) from `requirements-dev.txt` (pytest, tooling) so dev
  dependencies never reach Airflow.

✅ **Done when:** all pins present, `docker compose build` succeeds from a clean clone, and no unused package remains.

### 🚪 Phase 5 gate

- [ ] No public buckets
- [ ] Credential audit clean or keys rotated
- [ ] Least-privilege IAM
- [ ] Dependencies pinned and pruned

---

## Phase 6 — Cleanup and handover

**Duration:** 1.5 days · **Owner:** O on cleanup, all on verification

### T-6.1 — Remove committed cruft ⏱ 1 h 👤 O

```bash
git rm --cached .DS_Store && echo '.DS_Store' >> .gitignore
```

Decide deliberately whether `Assignment.md` belongs in the deliverable repo — it is
currently tracked. Confirm `git status` is clean on a fresh clone, which is the Lab 0
checkpoint.

✅ **Done when:** `git status` clean on a fresh clone, no OS metadata tracked.

### T-6.2 — Repository naming decision ⏱ 30 min 👤 H

Deliverable 1 specifies `pe-dashboard-ai50`; the repo is `AI50-rag-pipeline`.

**Recommendation: keep the name and note the deviation.** Renaming breaks the
`codelabs-preview.appspot.com` raw-content link at `README.md:17` unless it is updated in the
same change, and GitHub redirects make the rename largely cosmetic. Low value, non-trivial
breakage risk this late.

✅ **Done when:** the decision is recorded — and if renaming, the codelab link and every clone command are updated in the same commit.

### T-6.3 — Final handover verification ⏱ 3 h 👤 all

Performed end-to-end by whoever wrote **least** of the code:

1. Fresh clone into a new directory
2. Follow `README.md` exactly — no prior knowledge, no shortcuts
3. `docker compose up` → both services respond
4. Generate one dashboard per pipeline
5. Run both DAGs against local Airflow
6. `pytest` green

✅ **Done when:** all six steps pass with no undocumented steps, and the transcript is committed as `docs/evidence/handover-verification.md`.

### 🚪 Phase 6 gate

- [ ] No cruft tracked
- [ ] Naming decision recorded
- [ ] Clean clone verified by a third party

---

## Task index

| Task | Phase | Description | ⏱ | 👤 | ⛓ |
|---|---|---|---|---|---|
| T-1.1 | 1 | Build evaluation harness | 1 d | P+O | — |
| T-1.2 | 1 | Score 5+ companies → `EVAL.md` | 1 d | all | T-1.1 |
| T-1.3 | 1 | Write reflection | 3 h | all | T-1.2 |
| T-1.4 | 1 | `GET /rag/search` | 2 h | O | — |
| T-1.5 | 1 | Complete attestation | 5 m | H | — |
| T-1.6 | 1 | Resolve hosting question | 4 h | O | — |
| T-2.1 | 2 | Consolidate DAG directories | 2 h | H | — |
| T-2.2 | 2 | Make DAGs importable | 3 h | H | T-2.1 |
| T-2.3 | 2 | Delegate work to Cloud Run | 4 h | H | T-2.2 |
| T-2.4 | 2 | Local Airflow | 4 h | H | — |
| T-2.5 | 2 | Capture DAG run evidence | 1 h | H | T-2.4 |
| T-3.1 | 3 | Correct RAG architecture claims | 2 h | P | T-4.1 |
| T-3.2 | 3 | Substantiate results table | 4 h | all | **T-1.2** |
| T-3.3 | 3 | Fix run instructions | 3 h | O | — |
| T-3.4 | 3 | Add `.env.example` | 1 h | O | — |
| T-3.5 | 3 | As-built architecture diagram | 4 h | H | T-2.1 |
| T-4.1 | 4 | Replace hard-coded `gpt-4` | 20 m | P | — |
| T-4.2 | 4 | One data source of truth | 4 h | O | — |
| T-4.3 | 4 | Remove error masking | 1 h | H | — |
| T-4.4 | 4 | Fix invalid gcloud flags | 1 h | H | T-4.3 |
| T-4.5 | 4 | Real tests + CI | 5 h | O | — |
| T-4.6 | 4 | True delta refresh | 5 h | H | T-2.3 |
| T-5.1 | 5 | Remove public bucket access | 1 h | H | — |
| T-5.2 | 5 | Credential audit | 2 h | H | — |
| T-5.3 | 5 | Least-privilege service accounts | 4 h | H | — |
| T-5.4 | 5 | Pin + prune dependencies | 4 h | P | — |
| T-6.1 | 6 | Remove committed cruft | 1 h | O | — |
| T-6.2 | 6 | Repo naming decision | 30 m | H | — |
| T-6.3 | 6 | Final handover verification | 3 h | all | all |

**29 tasks · ~11–13 working days · 3 people**

---

## Progress tracker

Last updated: 2026-08-05.

```
Phase 1  Graded deliverables    [~][ ][ ][x][x][ ]     2/6  (+2 partial)
Phase 2  Pipeline runs          [x][x][x][x][ ]        4/5
Phase 3  Docs true              [x][x][x][x][x]        5/5
Phase 4  Correctness            [x][x][x][x][x][ ]     5/6
Phase 5  Security               [x][x][ ][x]           3/4
Phase 6  Cleanup & handover     [x][x][~]              2/3  (+1 partial)
                                                  ─────────
                                                  21/29 tasks
```

Legend: `x` complete · `~` harness/scaffolding built but blocked on credentials · ` ` not started

**Blocked on credentials or a live environment** (cannot be completed from a dev container):

| Task | What is done | What is blocked |
|---|---|---|
| T-1.1 | Harness built, unit-tested, `--dry-run` verified | Real generation needs `OPENAI_API_KEY` |
| T-1.2 | `EVAL.md` restructured with rubric + instructions | Scoring needs an API key and scraped `data/raw/` |
| T-1.3 | — | Depends on T-1.2 |
| T-1.6 | Decision documented; local compose verified | `gcloud run deploy` needs GCP credentials |
| T-2.5 | — | Needs a live Airflow run |
| T-4.6 | — | Needs a live GCS side-file store to verify against |
| T-5.3 | — | Needs GCP IAM access |
| T-6.3 | Suite + harness verified locally | Full walkthrough needs Docker and credentials |

| Metric | Baseline (`648193e`) | Now | Target |
|---|---|---|---|
| Companies scored in `EVAL.md` | 0 | 0 | **≥ 5** |
| Graded deliverables complete | 6 of 8 | 7 of 8 | **8 of 8** |
| DAGs that can succeed as deployed | 1 of 3 | 3 of 3 | **all** |
| Documented claims contradicting code | 10 | 0 | **0** |
| Silent-fallback code paths | 3 | 0 | **0** |
| Automated tests | 0 | **68 passing** | passing in CI |

Update the tracker at each phase gate.

---

## Definition of done

A task is complete when:

1. Its acceptance criteria are met and checked off.
2. Code is committed to a feature branch, never directly to `main`.
3. It has been reviewed by one other team member.
4. `pytest` is green and DAGs import cleanly (once T-4.5 lands).
5. **Documentation is updated in the same commit as the behaviour change.** This repository's
   recurring failure mode is documentation drifting away from code — Phase 3 exists entirely
   because of it. Do not reintroduce the problem while fixing it.
6. Any evidence the acceptance criteria call for is committed under `docs/evidence/`.
