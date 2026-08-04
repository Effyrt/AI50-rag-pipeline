# Project ORBIT — Status Assessment, Gap Analysis, GCP Cost Review & Agile Backlog

**Repo:** `Effyrt/AI50-rag-pipeline`
**Course:** DAMG7245 — Assignment 2, Case Study 2 (Project ORBIT, Part 1)
**Assessment date:** 2026-08-04
**Assessed branch:** `claude/repo-status-workflow-643nke` (identical to `main`, 0 commits ahead)
**GCP project:** `gen-lang-client-0653324487` (region `us-central1`)

---

## 0. How to read this document

| Section | Contents |
|---|---|
| [1. Executive summary](#1-executive-summary) | The three things that matter |
| [2. Verification basis](#2-verification-basis) | What was actually checked vs. inferred |
| [3. Gap register — what is missing](#3-gap-register--what-is-missing) | `M-xx` items: unbuilt deliverables |
| [4. Defect register — what needs fixing](#4-defect-register--what-needs-fixing) | `D-xx` items: built but wrong |
| [5. GCP cost review](#5-gcp-cost-review) | Current run-rate estimate + reduction plan |
| [6. Agile plan](#6-agile-plan) | Epics, user stories, acceptance criteria, sprints |
| [7. Risk register](#7-risk-register) | RAID log |
| [8. Working agreements](#8-working-agreements) | Definition of Ready / Done, board columns |
| [9. Traceability matrix](#9-traceability-matrix) | Finding → story → epic |

Severity scale: **P0** = blocks grade or actively costs money · **P1** = graded quality impact · **P2** = correctness/maintainability · **P3** = cosmetic.

---

## 1. Executive summary

Three findings dominate everything else in this document.

**1.1 — One graded deliverable was never produced.** `EVAL.md` is still the unedited blank template: no company rows, no rubric scores, no totals. Lab 9 explicitly requires a RAG-vs-Structured comparison across **at least 5 companies** plus a one-page reflection, and the reflection does not exist anywhere in the repo. Everything else in Labs 0–11 is substantially built. This is the single highest-value piece of work remaining.

**1.2 — The headline results are asserted, not measured.** `codelabs.md` publishes a comparison table claiming 94% vs 78% data accuracy, 2% vs 18% hallucination rate, and 100% vs 65% format consistency. Nothing in the repository produces those numbers: there is no evaluation harness, no scored output artifacts, and `src/backend/evaluator.py` is a two-line function that adds five integers. A grader reading `codelabs.md` next to the empty `EVAL.md` will see the contradiction immediately. The numbers must either be earned by running the evaluation or withdrawn.

**1.3 — Cloud Composer is very likely still billing ~$350/month for a finished project.** Composer is ~89% of the modelled GCP run-rate. If the `ai50-composer` environment has existed since the November 2025 "Last Updated" stamp and was never deleted, cumulative spend is on the order of **$2,700–$3,800**. Critically, *pausing the DAGs saves almost nothing* — Composer 2 bills for the environment, not for DAG runs. Only deleting the environment stops the charge. **Verify and act on this before any other work in this document.**

**Overall completion: ~85% of the build, ~40% of the evidence.** The engineering is real and the cloud pipeline is genuinely deployed; what is unfinished is the measurement phase — precisely the part the assignment uses to judge whether the results are good.

---

## 2. Verification basis

Stated plainly so nothing here is mistaken for a live reading.

**Directly verified in this repository:**
- Git state: clean tree, branch level with `main`, last 12 commits are README/codelabs prose edits only.
- `data/forbes_ai50_seed.json` parses as a list of **exactly 50** company objects with populated fields (rank, funding, founded_year, HQ, website, LinkedIn).
- FastAPI routes, by inspection of `src/backend/api.py`: `GET /`, `GET /companies`, `POST /dashboard/rag`, `POST /dashboard/structured`, `GET /companies/{company_name}/comparison`, `GET /test`.
- `EVAL.md` contents (empty template) and `CONTRIBUTION_ATTESTATION.txt` contents (`member1: __%` placeholders).
- All resource sizing quoted in §5 is read from the committed scripts `gcp/build_and_deploy.sh`, `gcp/setup_composer.sh`, `gcp/setup_gcp.sh`.

**Not verified — no access:**
- **Actual GCP billing.** No `gcloud`/`gsutil` binary and no credentials in the assessment environment. Every dollar figure in §5 is a **model built from committed resource specs and public list prices**, not a billing-API reading. Commands to obtain the real number are in §5.6.
- **Live state of deployed resources** — whether the Composer environment, Cloud Run Jobs, and buckets still exist, and whether any Cloud Run *services* (as opposed to Jobs) were ever deployed for FastAPI/Streamlit.
- **Runtime behaviour.** No `OPENAI_API_KEY`, no GCP credentials, and no `data/raw|structured|payloads` (all gitignored), so no pipeline was executed end-to-end.

---

## 3. Gap register — what is missing

| ID | Severity | Gap | Evidence | Assignment ref |
|---|---|---|---|---|
| **M-01** | **P0** | RAG-vs-Structured evaluation not performed. `EVAL.md` is the blank template — zero companies scored against the 10-point rubric. | `EVAL.md` (whole file) | Lab 9, Deliverable 6 |
| **M-02** | **P0** | One-page reflection does not exist. | No file in repo matches; only `Assignment.md` mentions "reflection" | Lab 9 |
| **M-03** | **P1** | No evaluation harness. Nothing can generate, score, or persist a comparison. | `src/backend/evaluator.py` is 2 lines: `score_dashboard()` sums five ints | Lab 9 |
| **M-04** | **P1** | `GET /rag/search` retrieval-test endpoint not exposed. `RAGPipeline.search()` exists at `rag_pipeline.py:179` but no route calls it. | `src/backend/api.py` route list | Lab 4, task 3 |
| **M-05** | **P1** | Contribution attestation file left as placeholders. Names/percentages exist only in `README.md`; the submitted artifact says `member1: __%`. | `CONTRIBUTION_ATTESTATION.txt` | Deliverable 8 |
| **M-06** | **P1** | No Cloud Run **service** URLs for FastAPI/Streamlit recorded anywhere. Only Cloud Run **Jobs** (batch) are scripted; README quick-start is localhost-only. The graded requirement is a *hosted* app. | `gcp/build_and_deploy.sh` creates jobs only; no `run deploy` anywhere | Lab 10, Deliverable 2/3 |
| **M-07** | **P2** | No evidence artifacts committed — no sample dashboard pair per pipeline, no DAG success screenshots, no run logs to substantiate "runs successfully". | `data/dashboards/` gitignored; no `docs/evidence/` | Labs 2/3/7/8 checkpoints |
| **M-08** | **P2** | No `.env.example`, though both README and `codelabs.md` instruct `cp .env.example .env`. First-run instructions fail literally. | `README.md` Local Setup; `codelabs.md` Step 1 | Lab 0 (reproducibility) |
| **M-09** | **P2** | No automated test suite. `test_backend.py` is a print-based import smoke script, not assertions, and is not wired to any runner. | `test_backend.py` | — |
| **M-10** | **P2** | No GCP budget or billing alert configured (none scripted, none documented). | `gcp/setup_gcp.sh` | — (FinOps) |
| **M-11** | **P3** | No true delta detection in the "daily refresh" DAG despite Lab 3 asking to "re-scrape only changed or key pages". It unconditionally re-scrapes every company into a new dated folder. | `dags/ai50_daily_refresh_dag.py:41-100` | Lab 3, task 3 |
| **M-12** | **P3** | Repo name is `AI50-rag-pipeline`; deliverable 1 specifies `pe-dashboard-ai50`. | Repo metadata | Deliverable 1 |

---

## 4. Defect register — what needs fixing

### 4.1 Cost and correctness defects

| ID | Severity | Defect | Location | Impact |
|---|---|---|---|---|
| **D-01** | **P0** | RAG pipeline hard-codes legacy `gpt-4` (8k context, $30/1M input · $60/1M output) while all documentation claims `gpt-4o-mini` ($0.15/$0.60). ~150–200× the input price per dashboard. | `src/backend/rag_pipeline.py:88` | ~$0.35/dashboard vs ~$0.002. Also risks 8k-context overflow at `top_k=15` |
| **D-02** | **P0** | Composer creation flags are Composer **1** syntax passed to a Composer **2** image: `--python-version=3.11` and `--web-server-machine-type=composer-n1-webserver-2`. Both are invalid for `composer-2.9.0-airflow-2.9.3`. Because the call ends in `|| echo "Composer environment already exists"`, a genuine failure is swallowed and reported as success. | `gcp/setup_composer.sh:24-33` | Silent-failure masking; script is not reproducible as committed |
| **D-03** | **P1** | Extractor job uses `--timeout=1800`; the valid Cloud Run **Jobs** flag is `--task-timeout`. Same `\|\| echo` pattern hides the rejection. Additionally the extractor runs as a **single task** for all 50 companies × 5 passes — 30 min is very likely insufficient. | `gcp/build_and_deploy.sh:56-64` | Job may be created without intended timeout, then fail mid-run |
| **D-04** | **P1** | The two `dags/*.py` DAGs execute scraping and embedding **in-process inside the Airflow worker**, contradicting `docs/AIRFLOW_USAGE_GUIDE.md`, which describes Cloud Run Job execution. Only `airflow/dags/ai50_structured_dag.py` actually uses Cloud Run operators. | `dags/ai50_daily_refresh_dag.py:41`, `dags/ai50_full_ingest_dag.py:42` | 50 Playwright browsers + sentence-transformers on the Composer worker: OOM risk, and forces a larger/pricier environment than needed |
| **D-05** | **P1** | Bare imports (`from scraper import CompanyScraper`, `from rag_pipeline import RAGPipeline`) will not resolve in Composer, where only `airflow/dags/*.py` is uploaded — the `src/backend/` package is never shipped. | `dags/ai50_daily_refresh_dag.py:43,109` | Those DAGs cannot succeed as deployed |
| **D-06** | **P1** | Dashboards bucket is made world-readable **and** configured as a public website. | `gcp/setup_gcp.sh:71-72` (`gsutil iam ch allUsers:objectViewer`) | Uncapped egress exposure + unintended public disclosure of generated content |
| **D-07** | **P2** | Duplicated DAG trees: `dags/` and `airflow/dags/` hold divergent copies. `setup_composer.sh` uploads only `airflow/dags/*`, so `dags/` is dead code that still looks authoritative. Three DAGs total with conflicting schedules. | `dags/`, `airflow/dags/` | Ambiguity about which DAG is real |
| **D-08** | **P2** | Schedule contradiction: `docs/AIRFLOW_USAGE_GUIDE.md` says `ai50_daily_refresh` is `schedule_interval=None` (manual only); `dags/ai50_daily_refresh_dag.py:198` sets `0 3 * * *`. | Both files | Either an unexpected daily bill or an unmet Lab 3 requirement |
| **D-09** | **P2** | `api.py` reads structured data and payloads from local `data/structured` / `data/payloads`, both gitignored and absent in any container, while the module also initialises a GCS client. Two sources of truth, only one populated. | `src/backend/api.py:66-80` | Structured endpoint silently degrades in deployment |
| **D-10** | **P2** | Streamlit ships a hard-coded 5-company fallback list that renders as though real data when `/companies` fails. | `src/frontend/streamlit_app.py:26-30` | Masks outages; risks demoing fake data |
| **D-11** | **P2** | `structured_pipeline.py` silently falls back to `data/starter_payload.json` for **any** missing company, returning starter data labelled as the requested company. | `src/backend/structured_pipeline.py:9-12` | Wrong-company data with no error signal |
| **D-12** | **P3** | `requirements.txt` is mostly unpinned and carries unused/conflicting heavyweights: `selenium` + `webdriver-manager` (code uses Playwright), `faiss-cpu` (code uses Chroma). This whole file is pushed into Composer via `--update-pypi-packages-from-file`, triggering slow, failure-prone environment rebuilds. | `requirements.txt`; `gcp/setup_composer.sh:37-40` | Non-reproducible builds; Composer rebuild risk |

### 4.2 Documentation-vs-code drift

| ID | Severity | Claim in docs | Reality in code |
|---|---|---|---|
| **D-13** | **P1** | README + `codelabs.md`: vector DB is **FAISS** | `Chroma` — `rag_pipeline.py:14,96,104` |
| **D-14** | **P1** | README + `codelabs.md`: embeddings are OpenAI `text-embedding-3-small`, 1536-dim | HuggingFace `sentence-transformers/all-MiniLM-L6-v2`, 384-dim — `rag_pipeline.py:13,36` |
| **D-15** | **P1** | README + `codelabs.md`: LLM is `gpt-4o-mini` | `gpt-4` — `rag_pipeline.py:88` (see D-01) |
| **D-16** | **P1** | `codelabs.md` §12: 94%/78% accuracy, 2%/18% hallucination, 100%/65% consistency, "Real Production Results" | No harness, no scored artifacts, `EVAL.md` empty |
| **D-17** | **P2** | README quick-start: `uvicorn src.api:app`, `streamlit run src/streamlit_app.py` | Paths deleted in the `src/backend` + `src/frontend` restructure (commit `c9632b9`). `docker-compose.yml` has the correct paths |
| **D-18** | **P2** | README "Project Structure" block lists flat `src/*.py` | Pre-restructure; stale |
| **D-19** | **P2** | README references `TEAMMATE_RAG_GUIDE.md` | File does not exist |
| **D-20** | **P2** | `PROJECT_STRUCTURE.txt` marks `EVAL.md`, `Assignment.md`, `docs/PE_Dashboard.md` as gitignored | All three are tracked (`git ls-files` confirms) |
| **D-21** | **P2** | `setup_gcp.sh` header comment / README claim 4 buckets incl. `payloads` and `vector-index` | Script creates 3: `raw-data`, `structured-data`, `dashboards` |
| **D-22** | **P3** | `.DS_Store` committed at repo root | Should be ignored and removed from tracking |

---

## 5. GCP cost review

> **Basis:** modelled from committed resource specs (`gcp/*.sh`) against public `us-central1` list prices. **Not a billing-API reading** — see §2 and §5.6.

### 5.1 Resources as configured

| Resource | Spec (source) |
|---|---|
| Cloud Composer 2 | `ai50-composer`, `composer-2.9.0-airflow-2.9.3`, `--environment-size=small`, scheduler 2 vCPU / 4 GB / 5 GB, 1 scheduler (`setup_composer.sh`) |
| Cloud Run Job `ai50-scraper` | 4 GiB, 4 vCPU, `--task-count=50`, `--parallelism=10`, `--task-timeout=7200` (`build_and_deploy.sh`) |
| Cloud Run Job `ai50-extractor` | 4 GiB, 2 vCPU, single task, `--max-retries=2` (`build_and_deploy.sh`) |
| GCS | 3 Standard buckets; Nearline lifecycle at 90d on `raw-data` only; **no delete rule anywhere** (`setup_gcp.sh`) |
| Artifact Registry / GCR | 2 images; Playwright+Chromium scraper image is large; `:latest` re-pushed per build, **no cleanup policy** |
| Cloud Build | 2 builds per deploy |
| Secret Manager | 1 secret (`openai-api-key`) |
| Egress | `dashboards` bucket public (`allUsers:objectViewer`) |

### 5.2 Modelled monthly run-rate (daily schedule active)

Assumption for Cloud Run: ~5 min per scraper task; ~30 min for the extractor.

| Line item | Basis | Monthly | Share |
|---|---|---:|---:|
| **Cloud Composer 2 (small, 24/7)** | environment fee + GKE Autopilot compute + Cloud SQL metadata DB; ~$0.42–0.55/hr | **$300 – $420** (≈**$350**) | **~89%** |
| Cloud Run — scraper | 50 tasks × 5 min × 4 vCPU/4 GiB ≈ 16.7 vCPU-h + 16.7 GiB-h per run ≈ $1.20/run × 30 | $36 – $48 | ~9% |
| Cloud Run — extractor | 1 task × 30 min × 2 vCPU/4 GiB ≈ $0.08/run × 30 | $2 – $3 | <1% |
| GCS storage | ~275 MB/full run → ~8 GB/mo accretion @ $0.020/GB-mo | $1 – $3 (rising monthly) | <1% |
| Artifact Registry | ~15 GB retained incl. untagged layers @ $0.10/GB-mo | $1 – $2 | <1% |
| Cloud Build | ~12 min/build, within 120 free min/day | ~$0 | 0% |
| Secret Manager | 1 version @ $0.06 + access ops | <$0.10 | 0% |
| Egress (public bucket) | low volume assumed | <$1 | 0% |
| **Total** | | **≈ $340 – $475/mo (≈$395)** | 100% |

**The load-bearing fact:** Composer 2 bills for the *environment*, not for DAG runs. Pausing every DAG drops the bill from ~$395 to ~$355 — a **~10% saving**. Deleting the environment drops it to **~$45**. Any cost conversation that does not address the Composer environment itself is not a cost conversation.

### 5.3 Cumulative spend to date — scenario, not measurement

`README.md` is stamped "Last Updated: November 2025"; assessment date is 2026-08-04, ≈ **9 months**.

| Scenario | Cumulative GCP |
|---|---|
| Composer created ~Nov 2025, never deleted, DAGs daily | **~$3,100 – $3,800** |
| Composer created ~Nov 2025, never deleted, DAGs paused | **~$2,700 – $3,400** |
| Composer deleted shortly after submission | **~$400 – $700** total, then ~$3/mo idle |

Offset by any Free Tier / $300 trial credit still active. **Confirm which scenario is real before anything else** (§5.6). If it is one of the first two, the remediation in §5.4 pays for itself the day it lands.

### 5.4 Cost reduction plan — ranked by saving per unit of effort

| # | Action | Monthly saving | Effort | Trade-off |
|---|---|---:|---|---|
| **1** | **Delete the Composer environment.** Keep DAG code in-repo as the graded artifact; run Airflow locally (`docker compose` + `airflow standalone`) for demos, or recreate Composer for ~2 hours (~$1) when a live run is needed. | **~$350 (89%)** | S | No always-on managed Airflow UI |
| **2** | **If managed orchestration must persist:** replace Composer with **Cloud Scheduler → Cloud Run Jobs** (direct invoke). The real DAG is two sequential job triggers; that does not need Airflow. Cloud Scheduler is $0.10/job/mo after 3 free jobs. | **~$350 (89%)** | M | Loses Airflow UI/XCom; conflicts with the Airflow requirement unless DAGs are retained for grading |
| **3** | **`gpt-4` → `gpt-4o-mini`** at `rag_pipeline.py:88`. | ~99% of RAG LLM spend (~$0.35 → ~$0.002 per dashboard) | XS | Fixes D-01 and D-15 simultaneously; also removes 8k-context overflow risk |
| **4** | **Daily → weekly** schedule. Fifty company websites do not change materially every 24h. | ~$31 of Cloud Run + 7× less LLM and storage growth | XS | Staler data; Lab 3 requires the DAG to *exist* on `0 3 * * *`, not to run forever — keep the schedule in code, pause the deployment |
| **5** | **Content-hash delta skip** — store an ETag/SHA per page; skip extraction when unchanged. Also closes M-11. | 60–80% of remaining scrape+extract compute | M | Needs a small state store (GCS side-file is sufficient) |
| **6** | **Right-size the scraper**: 4 vCPU/4 GiB → 2 vCPU/2 GiB. Playwright page fetches are I/O-bound. | ~$18 – $24 | XS | Slightly longer per-task wall time |
| **7** | **GCS lifecycle**: Nearline at 7d (not 90d) and **delete at 30–60d** on `raw-data`; add rules to the other two buckets. | Caps unbounded accretion | XS | Older raw snapshots unrecoverable |
| **8** | **Artifact Registry cleanup policy**: keep 3 most-recent versions, delete untagged. | ~$1 – $2 | XS | None |
| **9** | **Remove `allUsers:objectViewer`** from the dashboards bucket; serve via the API instead. Closes D-06. | Caps egress tail risk | XS | Public link stops working |
| **10** | **Budget + alerts** at $25 / $50 / $100 with email to all three members. Closes M-10. | Prevents recurrence | XS | None |

**Projected end state:** ~$395/mo → **~$5–10/mo** with weekly runs and no Composer — a **~97–98% reduction**. Actions 1, 3, 4, 9, 10 alone are under two hours of work and capture the overwhelming majority of it.

### 5.5 Non-GCP: OpenAI spend

Tracked here because it is the other real cost and because D-01 makes it needlessly large.

| Workload | Current | After D-01 fix |
|---|---|---|
| Full extraction (5 passes × 50 companies, `gpt-4o-mini`) | ~$0.50 – $1.50/run | unchanged (already mini) |
| One RAG dashboard (`top_k=15` ≈ 7.5k in + ~2k out) | **~$0.30 – $0.40** on legacy `gpt-4` | **~$0.002** on `gpt-4o-mini` |
| 50 RAG dashboards | **~$17** | **~$0.12** |

Embeddings are already free — local `all-MiniLM-L6-v2`, no API cost. That is a genuinely good choice; do **not** "fix" it toward OpenAI embeddings. It does, however, need the docs corrected (D-14).

### 5.6 Getting the real numbers — run these first

```bash
# 0. Auth
gcloud auth login && gcloud config set project gen-lang-client-0653324487

# 1. THE question: does the Composer environment still exist?  (~$350/mo if yes)
gcloud composer environments list --locations=us-central1

# 2. Billing account + current spend (console gives the authoritative graph)
gcloud billing accounts list
gcloud beta billing projects describe gen-lang-client-0653324487
#    → console.cloud.google.com/billing → Reports → filter project, group by SKU, last 12 months

# 3. What else is running
gcloud run jobs list --region=us-central1
gcloud run services list --region=us-central1          # confirms whether the app was ever hosted
gcloud run jobs executions list --region=us-central1 --limit=20

# 4. Storage footprint and growth
gsutil du -sh gs://gen-lang-client-0653324487-raw-data \
              gs://gen-lang-client-0653324487-structured-data \
              gs://gen-lang-client-0653324487-dashboards

# 5. Container image bloat
gcloud artifacts docker images list gcr.io/gen-lang-client-0653324487 --include-tags

# 6. Existing guardrails (expected: none)
gcloud billing budgets list --billing-account=<BILLING_ACCOUNT_ID>
```

Record the outputs in `docs/evidence/cost-baseline-2026-08.md` (ORB-201) so §5.2 can be replaced with measurements rather than a model.

---

## 6. Agile plan

### 6.1 Team and capacity

| Member | Role | Focus (per README attestation) |
|---|---|---|
| Hemanth Rayudu | Data/Platform Eng | Structured pipeline, Airflow DAGs, GCP/FinOps |
| PeiYing Chen | ML Eng | RAG pipeline, embeddings, retrieval |
| Om Shailesh Raut | App Eng | FastAPI + Streamlit, Docker |

**Assumed capacity:** ~20 story points per member per sprint · **60 points/sprint** · 1-week sprints. Scale to actual availability before committing.

### 6.2 Epics

| Epic | Title | Goal | Points | Priority |
|---|---|---|---:|---|
| **E1** | Stop the Bleeding — GCP Cost Containment | Cut run-rate ~$395/mo → <$10/mo and prevent recurrence | 21 | **P0** |
| **E2** | Close the Graded Deliverable Gap | Produce the Lab 9 evaluation + reflection with real, reproducible numbers | 34 | **P0** |
| **E3** | Documentation Truthfulness | Every claim in README/codelabs traceable to code or a committed artifact | 18 | **P1** |
| **E4** | Pipeline Correctness & Deployability | DAGs and jobs that actually run as documented | 26 | **P1** |
| **E5** | Security & Access Hardening | No public data surfaces, least-privilege IAM, no secrets in repo | 10 | **P1** |
| **E6** | Repo Hygiene & Reproducibility | Clean clone → working local run, no dead code, pinned deps | 16 | **P2** |
| | | **Total** | **125** | |

Sequencing rationale: **E1 first** because it is the only epic where every day of delay has a dollar cost. **E2 second** because it is the only epic that changes the grade. E3 depends on E2 (can't correct the results table until real results exist) and on E4 (can't document the architecture until the DAG story is settled).

---

### 6.3 EPIC E1 — Stop the Bleeding: GCP Cost Containment

> *As the team's budget owner, I want the GCP run-rate reduced to near zero for a completed project, so that a finished assignment stops consuming money and no one is surprised by a bill.*

---

**ORB-101 — Establish the cost baseline** · 3 pts · P0 · Hemanth

> *As a budget owner, I want to know exactly what we are spending and on what, so that remediation is aimed at the real driver rather than a guess.*

**Acceptance criteria**
- [ ] All commands in §5.6 executed; raw output captured.
- [ ] `docs/evidence/cost-baseline-2026-08.md` committed with: billing total to date, month-by-month spend, top 5 SKUs by cost, and a definitive yes/no on whether `ai50-composer` still exists.
- [ ] §5.2 and §5.3 of this document updated to replace modelled figures with measured ones, with an explicit "measured on <date>" note.
- [ ] Which scenario in §5.3 is real is stated in one sentence.

**Blocks:** ORB-102, ORB-103. **DoR:** billing-account viewer access confirmed for at least one member.

---

**ORB-102 — Decommission Cloud Composer** · 5 pts · P0 · Hemanth
**Depends on:** ORB-101

> *As a budget owner, I want the always-on Airflow environment removed, so that we stop paying ~$350/month for orchestration that runs for 40 minutes a day.*

**Acceptance criteria**
- [ ] Composer environment snapshot taken and stored in GCS **before** deletion (`gcloud composer environments snapshots save`).
- [ ] DAG files, Airflow variables/connections, and the Airflow UI URI recorded in `docs/evidence/composer-teardown.md`.
- [ ] Screenshots of successful DAG runs captured **before** teardown (feeds ORB-107 — this evidence is unrecoverable afterwards).
- [ ] Environment deleted; `gcloud composer environments list --locations=us-central1` returns empty.
- [ ] `docs/AIRFLOW_USAGE_GUIDE.md` updated: the live UI URL replaced with local-Airflow instructions plus a documented recreate path.
- [ ] Post-teardown billing checked after 48h to confirm the Composer SKU has stopped accruing.

**Note:** Do **not** merely pause the DAGs — §5.2 shows that saves ~10%, not ~89%.

---

**ORB-103 — Local Airflow for demo and development** · 5 pts · P0 · Hemanth
**Depends on:** ORB-102

> *As a team member, I want to run and demonstrate both DAGs without a managed environment, so that decommissioning Composer costs us no marks and no capability.*

**Acceptance criteria**
- [ ] `docker/docker-compose.airflow.yml` starts Airflow (standalone or LocalExecutor) with `airflow/dags/` mounted.
- [ ] Both `ai50_full_ingest_dag` and `ai50_daily_refresh_dag` parse with zero import errors (`airflow dags list-import-errors` is empty).
- [ ] Documented commands to trigger each DAG locally and view the graph.
- [ ] Documented one-command Composer recreate path (~$1 for a 2-hour window) for any live-demo requirement.

---

**ORB-104 — Cut the per-dashboard LLM cost** · 1 pt · P0 · PeiYing

> *As a budget owner, I want the RAG pipeline on the model our documentation already claims, so that each dashboard costs ~$0.002 instead of ~$0.35.*

**Acceptance criteria**
- [ ] `rag_pipeline.py:88` reads `model_name="gpt-4o-mini"`, sourced from env var `RAG_LLM_MODEL` with `gpt-4o-mini` as default.
- [ ] Verified no other hard-coded model string remains (`grep -rn 'gpt-4"' src/`).
- [ ] One dashboard regenerated and quality spot-checked against a pre-change sample.
- [ ] Recorded per-dashboard token counts and cost before/after in the evidence folder.

**Note:** this is a one-line change that also removes the 8k-context overflow risk at `top_k=15`, and resolves D-15.

---

**ORB-105 — Right-size and reschedule the pipeline jobs** · 3 pts · P1 · Hemanth

> *As a budget owner, I want compute matched to the actual workload and a sane refresh cadence, so that we are not paying for idle vCPU or for re-scraping unchanged sites 30 times a month.*

**Acceptance criteria**
- [ ] Scraper job reduced to 2 vCPU / 2 GiB; a full 50-company run still completes within the task timeout (measured, not assumed).
- [ ] Extractor `--timeout=1800` corrected to `--task-timeout` (closes D-03) and the value justified against a measured 50-company run.
- [ ] Deployment schedule changed to weekly; the `0 3 * * *` definition retained in DAG code for the Lab 3 requirement, with the divergence explained in one comment.
- [ ] `|| echo "already exists"` patterns replaced with explicit `describe`-then-`create`-or-`update` logic so real failures surface (closes D-02's masking behaviour).

---

**ORB-106 — Storage and image lifecycle policies** · 2 pts · P1 · Hemanth

> *As a budget owner, I want old data and container layers expired automatically, so that storage cost cannot grow without bound.*

**Acceptance criteria**
- [ ] `raw-data`: Nearline at 7d, Coldline at 30d, **delete at 60d**.
- [ ] `structured-data` and `dashboards`: lifecycle rules defined (versioned retention as appropriate).
- [ ] Artifact Registry cleanup policy: keep 3 most-recent versions, delete untagged older than 7d.
- [ ] Policies committed as JSON under `gcp/lifecycle/` and applied by `setup_gcp.sh` — not hand-clicked in the console.

---

**ORB-107 — Budget guardrails** · 2 pts · P0 · Hemanth

> *As a team member, I want to be alerted before spend becomes a problem, so that we never again discover a months-old charge retroactively.*

**Acceptance criteria**
- [ ] Budget created on the billing account with thresholds at 50% / 90% / 100% of **$25/month**.
- [ ] Email notifications to all three members verified (test alert received).
- [ ] Budget creation scripted in `gcp/setup_budget.sh` and referenced from `setup_gcp.sh`.
- [ ] `docs/GCP_DEPLOYMENT_GUIDE.md` gains a "Cost & Teardown" section listing every billable resource and its delete command.

---

### 6.4 EPIC E2 — Close the Graded Deliverable Gap

> *As a student team, we want the RAG-vs-Structured comparison performed and documented with reproducible numbers, so that the assignment's central question is actually answered.*

---

**ORB-201 — Build the evaluation harness** · 8 pts · P1 · PeiYing + Om
**Depends on:** ORB-104 (fix the model before scoring the outputs)

> *As an evaluator, I want a repeatable script that generates and scores both dashboards for a given company, so that our comparison is reproducible rather than anecdotal.*

**Acceptance criteria**
- [ ] `src/backend/evaluator.py` expanded beyond the current 2-line sum to implement the full rubric: factual (0–3), schema (0–2), provenance (0–2), hallucination (0–2), readability (0–1).
- [ ] Schema adherence scored **automatically** — verifies all 8 required section headings, in order, and that `## Disclosure Gaps` is present.
- [ ] Hallucination check flags any ARR/MRR/valuation/customer-logo claim absent from source text.
- [ ] `scripts/run_eval.py --companies a,b,c,d,e` writes both dashboards plus a scores JSON to `data/eval/<company>/`.
- [ ] Token counts, wall-clock latency, and USD cost captured per generation — these are the numbers `codelabs.md` currently asserts without evidence.
- [ ] Manual-judgement fields (factual, provenance, readability) are explicitly marked as human-scored, with the scorer named.

---

**ORB-202 — Score 5+ companies and populate EVAL.md** · 8 pts · P0 · all three
**Depends on:** ORB-201

> *As a grader, I want to see at least 5 companies scored on both pipelines, so that I can verify the comparison claim.*

**Acceptance criteria**
- [ ] ≥5 companies evaluated on **both** pipelines (recommend a deliberate spread: one very well documented — e.g. Anthropic or Databricks — and one thin-website company, so disclosure-gap handling is genuinely exercised).
- [ ] `EVAL.md` fully populated: one row per company per method, all five sub-scores, totals out of 10.
- [ ] Aggregate comparison table with mean scores per pipeline.
- [ ] Scoring rationale recorded per company (1–2 sentences), so the numbers are defensible under questioning.
- [ ] The 10 generated dashboards committed under `data/eval/` as evidence (add a `!data/eval/` negation to `.gitignore`).
- [ ] `"Not disclosed."` handling verified in output for at least one thin-data company (Lab 7 checkpoint).

---

**ORB-203 — Write the one-page reflection** · 3 pts · P1 · all three
**Depends on:** ORB-202

> *As a grader, I want a reflection explaining which pipeline won and why, so that I can assess understanding rather than just output.*

**Acceptance criteria**
- [ ] `docs/REFLECTION.md`, ~1 page, citing **measured** results from ORB-202 — no unsourced figures.
- [ ] Covers: which pipeline scored higher and why; where each failed; cost/latency trade-off; what we would change with more time.
- [ ] Honest about limitations (n=5, single scorer, single-run variance).
- [ ] Linked from `README.md`.

---

**ORB-204 — Expose `GET /rag/search`** · 2 pts · P1 · Om

> *As a developer, I want to query the vector index directly over HTTP, so that retrieval quality can be tested independently of dashboard generation (Lab 4 checkpoint).*

**Acceptance criteria**
- [ ] `GET /rag/search?q=<query>&company=<id>&k=<n>` implemented, wrapping the existing `RAGPipeline.search()` (`rag_pipeline.py:179`).
- [ ] Response includes chunk text, company, source URL, and similarity score.
- [ ] Lab 4 checkpoint demonstrated: searching `"funding"` and `"leadership"` returns topically correct chunks; the transcript is committed as evidence.
- [ ] Endpoint appears in the OpenAPI docs at `/docs`.

---

**ORB-205 — Complete the contribution attestation** · 1 pt · P0 · Hemanth

> *As a grader, I want the signed attestation artifact filled in, so that the submission is complete.*

**Acceptance criteria**
- [ ] `CONTRIBUTION_ATTESTATION.txt` placeholders replaced with real names and percentages summing to 100%.
- [ ] Matches the README table (Hemanth 33.33% / PeiYing 33.33% / Om 33.33%).
- [ ] Attestation statement text left verbatim as provided.

---

**ORB-206 — Host the FastAPI + Streamlit apps (or state they are local)** · 5 pts · P1 · Om

> *As a grader, I want to open the dashboard app at a URL, so that the "cloud-hosted" requirement is demonstrably met.*

**Acceptance criteria**
- [ ] **Decide and document one of:** (a) deploy both as Cloud Run **services** with `min-instances=0` (scale-to-zero — pennies/month, closing M-06), or (b) explicitly declare the app local-only via `docker compose` and justify it against Lab 10.
- [ ] If (a): both service URLs recorded in README; Streamlit's `API_BASE` points at the API service URL; `gcp/build_and_deploy.sh` gains the `run deploy` commands; cost impact confirmed <$2/mo.
- [ ] If (b): README quick-start corrected (closes D-17) and the deviation flagged prominently for the grader.
- [ ] Either way, `docker compose up` from a clean clone starts FastAPI on :8000 and Streamlit on :8501 (Lab 10 checkpoint), with the command transcript committed.

**Recommendation:** (a). Cloud Run services at `min-instances=0` cost almost nothing and directly satisfy a graded requirement — it is the cheapest available mark in this backlog.

---

### 6.5 EPIC E3 — Documentation Truthfulness

> *As a grader or new contributor, I want every documented claim to match the code, so that the documentation is a reliable guide rather than an aspiration.*

---

**ORB-301 — Correct the RAG architecture claims** · 3 pts · P1 · PeiYing

> *As a reader, I want the stated vector DB, embedding model, and LLM to match what runs, so that I can trust the rest of the document.*

**Acceptance criteria**
- [ ] README and `codelabs.md` state **Chroma** (not FAISS) — closes D-13.
- [ ] Both state **`sentence-transformers/all-MiniLM-L6-v2`, 384-dim, local/no API cost** (not OpenAI `text-embedding-3-small`, 1536-dim) — closes D-14.
- [ ] Both state the actual generation model post-ORB-104 — closes D-15.
- [ ] The codelab's "~7,000+ chunks indexed" claim is either measured and cited or removed.
- [ ] `faiss-cpu` removed from `requirements.txt` if genuinely unused (verify by grep first).

---

**ORB-302 — Replace the unsubstantiated results table** · 5 pts · P1 · all three
**Depends on:** ORB-202

> *As a grader, I want the comparison table backed by our evaluation, so that the codelab's central claim is defensible.*

**Acceptance criteria**
- [ ] `codelabs.md` §12 figures (94%/78%, 2%/18%, 100%/65%, token and latency numbers) **replaced with measured values from ORB-202**, or deleted.
- [ ] Every retained number carries a source: `n=5, see EVAL.md`.
- [ ] The "Real Production Results" heading either gains real results or is removed.
- [ ] Sample dashboard excerpts in the codelab are replaced with genuine generated output (the current OpenAI example is illustrative and OpenAI is not in the Forbes AI 50 seed list — a grader will notice).

---

**ORB-303 — Fix run instructions and structure docs** · 3 pts · P2 · Om

> *As a new contributor, I want the quick-start commands to work on a clean clone, so that I can run the project.*

**Acceptance criteria**
- [ ] README run commands corrected to `src.backend.api:app` and `src/frontend/streamlit_app.py` (closes D-17).
- [ ] README "Project Structure" regenerated post-restructure (closes D-18).
- [ ] Dead `TEAMMATE_RAG_GUIDE.md` reference removed or the file written (closes D-19).
- [ ] `PROJECT_STRUCTURE.txt` corrected or deleted — it currently misstates which files are tracked (closes D-20). Recommend deleting: it duplicates the README and will drift again.
- [ ] Bucket count/names in README and `setup_gcp.sh` comments reconciled with the 3 actually created (closes D-21).
- [ ] A clean-clone walkthrough is performed by someone who did not write the docs, and their transcript is committed.

---

**ORB-304 — Add `.env.example`** · 1 pt · P2 · Om

> *As a new contributor, I want a template environment file, so that the documented `cp .env.example .env` step works.*

**Acceptance criteria**
- [ ] `.env.example` committed with every variable the code reads: `OPENAI_API_KEY`, `GCP_PROJECT_ID`, `GCS_BUCKET_NAME`, `GOOGLE_APPLICATION_CREDENTIALS`, `API_BASE`, `RAG_LLM_MODEL`.
- [ ] Placeholder values only — **no real keys** (closes M-08).
- [ ] Each variable carries a one-line comment on purpose and whether it is required.
- [ ] Verified: a clean clone following README reaches a running API.

---

**ORB-305 — Document the architecture as-built** · 6 pts · P2 · Hemanth
**Depends on:** ORB-102, ORB-401

> *As a grader, I want one accurate architecture diagram, so that the three conflicting descriptions in the repo are replaced by the truth.*

**Acceptance criteria**
- [ ] Single canonical diagram reflecting the post-decommission reality (what orchestrates, what executes where, which buckets exist).
- [ ] README, `codelabs.md`, and `docs/GCP_DEPLOYMENT_GUIDE.md` all reference that one diagram — no divergent copies.
- [ ] Explicitly documents which DAG is authoritative and which execution model it uses (closes D-04's documentation half, D-08).

---

### 6.6 EPIC E4 — Pipeline Correctness & Deployability

> *As a data engineer, I want the DAGs and jobs to run as documented, so that "the pipeline works" is a verified statement.*

---

**ORB-401 — Consolidate to one DAG directory** · 3 pts · P1 · Hemanth

> *As a maintainer, I want exactly one authoritative copy of each DAG, so that nobody edits the copy that is never deployed.*

**Acceptance criteria**
- [ ] Single DAG source of truth (recommend `airflow/dags/` — it is what `setup_composer.sh` actually uploads).
- [ ] Duplicate `dags/` tree deleted, or reduced to a symlink/README pointer (closes D-07).
- [ ] Exactly the DAGs Deliverable 4 requires are present and correctly named: `ai50_full_ingest_dag.py`, `ai50_daily_refresh_dag.py`.
- [ ] The third DAG (`ai50_structured_dag.py`) is either merged in or documented as intentional.
- [ ] Schedule contradiction resolved: `@once` for full ingest, `0 3 * * *` for daily refresh, and the docs match (closes D-08).

---

**ORB-402 — Make DAGs importable and delegate work to Cloud Run** · 8 pts · P1 · Hemanth
**Depends on:** ORB-401

> *As a data engineer, I want DAG tasks to trigger Cloud Run Jobs rather than run scraping in-process, so that the DAGs match the documentation and cannot exhaust the worker.*

**Acceptance criteria**
- [ ] `from scraper import ...` / `from rag_pipeline import ...` bare imports removed; DAGs no longer depend on un-shipped `src/backend/` modules (closes D-05).
- [ ] Heavy work (Playwright scraping, embedding) delegated to Cloud Run Jobs via operators, matching `docs/AIRFLOW_USAGE_GUIDE.md` and the pattern already used in `ai50_structured_dag.py` (closes D-04).
- [ ] `airflow dags list-import-errors` returns empty against the local Airflow from ORB-103.
- [ ] Per-company success/failure logging retained (Lab 3 requirement).
- [ ] End-to-end local run over a **3-company subset** completes green, with the log committed as evidence.

---

**ORB-403 — Single source of truth for data access** · 5 pts · P2 · Om

> *As an API consumer, I want the API to read from one well-defined location, so that endpoints do not silently degrade depending on where they run.*

**Acceptance criteria**
- [ ] `api.py` reads payloads/structured data from GCS when configured, local disk otherwise, with the active mode logged at startup (closes D-09).
- [ ] Missing company data returns **HTTP 404 with a clear message** — never starter-payload data mislabelled as the requested company (closes D-11).
- [ ] Streamlit's hard-coded 5-company fallback removed; a failed `/companies` call surfaces a visible error instead of plausible-looking fake data (closes D-10).
- [ ] Lab 11 checkpoint verified: after a DAG run writes payloads, the Streamlit company list reflects the new data.

---

**ORB-404 — True delta refresh** · 5 pts · P2 · Hemanth
**Depends on:** ORB-402

> *As a budget owner, I want unchanged pages skipped, so that daily refreshes cost a fraction of a full re-scrape (Lab 3, task 3).*

**Acceptance criteria**
- [ ] Per-page content hash (or HTTP ETag/Last-Modified) persisted between runs in a GCS side-file.
- [ ] Extraction skipped when a page hash is unchanged; skips are logged and counted.
- [ ] Measured compute reduction on a second consecutive run reported in the evidence folder (closes M-11, delivers reduction lever #5).
- [ ] Dated per-run subfolders retained, as Lab 3 requires.

---

**ORB-405 — Real smoke tests in CI** · 5 pts · P2 · Om

> *As a maintainer, I want automated tests, so that regressions are caught before a demo.*

**Acceptance criteria**
- [ ] `test_backend.py` converted from print-based script to `pytest` with real assertions (closes M-09).
- [ ] Coverage of: seed file loads 50 companies; all Pydantic models validate the starter payload; every API route returns its expected status with mocked data; the 8-section schema validator accepts a good dashboard and rejects one with a missing section.
- [ ] `.github/workflows/ci.yml` runs `pytest` plus DAG import checks on push.
- [ ] Tests pass with **no** `OPENAI_API_KEY` and **no** GCP credentials present (all external calls mocked) — otherwise CI is unusable.

---

### 6.7 EPIC E5 — Security & Access Hardening

**ORB-501 — Remove public bucket access** · 2 pts · P1 · Hemanth

> *As a data owner, I want generated dashboards off the public internet, so that content is not unintentionally disclosed and egress is not unbounded.*

**Acceptance criteria**
- [ ] `allUsers:objectViewer` removed from the dashboards bucket; `gsutil web set` website config removed (closes D-06).
- [ ] `gcp/setup_gcp.sh:71-72` updated so a fresh run never creates a public bucket.
- [ ] Dashboards served through the authenticated API (or signed URLs) instead.
- [ ] `gsutil iam get` on all three buckets confirms no `allUsers`/`allAuthenticatedUsers` bindings.

---

**ORB-502 — Secret and credential audit** · 3 pts · P1 · Hemanth

> *As a security-conscious team, I want to confirm no credentials were ever committed, so that we can hand the repo over safely.*

**Acceptance criteria**
- [ ] Full git **history** scanned for keys (`OPENAI_API_KEY`, `sk-`, service-account JSON, `credentials.json`) — not just the working tree.
- [ ] `.gitignore` confirmed to cover `.env`, `credentials.json`, `*-key.json`.
- [ ] If any key is found in history: rotated immediately, then history remediation assessed.
- [ ] Personal email in `docs/AIRFLOW_USAGE_GUIDE.md:7` reviewed for whether it belongs in a public repo.

---

**ORB-503 — Least-privilege service accounts** · 5 pts · P2 · Hemanth

> *As a platform owner, I want jobs running as purpose-built service accounts, so that a compromise is contained.*

**Acceptance criteria**
- [ ] Cloud Run Jobs stop using the default `<PROJECT_NUMBER>-compute@developer.gserviceaccount.com` (currently granted secret access in `setup_gcp.sh:84-88`).
- [ ] Dedicated SAs per job with only the bucket and secret access each needs.
- [ ] IAM changes scripted in `setup_gcp.sh`, not console-applied.

---

### 6.8 EPIC E6 — Repo Hygiene & Reproducibility

**ORB-601 — Pin and prune dependencies** · 5 pts · P2 · PeiYing

> *As a contributor, I want a reproducible dependency set, so that builds are deterministic and Composer/Docker installs stop being a coin flip.*

**Acceptance criteria**
- [ ] All packages version-pinned (closes half of D-12).
- [ ] Unused removed after verification: `selenium`, `webdriver-manager` (Playwright is used), `faiss-cpu` (Chroma is used); duplicate `google-cloud-storage` entry de-duplicated.
- [ ] Split into `requirements.txt` (runtime) and `requirements-dev.txt` (pytest, tooling) so heavyweight dev deps are not pushed into Airflow.
- [ ] `docker compose build` succeeds from a clean clone with no network-order flakiness.

---

**ORB-602 — Remove committed cruft** · 1 pt · P3 · Om

**Acceptance criteria**
- [ ] `.DS_Store` untracked and added to `.gitignore` (closes D-22).
- [ ] Whether `Assignment.md` belongs in the deliverable repo is decided deliberately (it is currently tracked).
- [ ] `git status` clean on a fresh clone (Lab 0 checkpoint).

---

**ORB-603 — Repository naming** · 2 pts · P3 · Hemanth

> *As a grader, I want the repo named as specified, so that submission matching is unambiguous.*

**Acceptance criteria**
- [ ] Deliverable 1 specifies `pe-dashboard-ai50`; current name is `AI50-rag-pipeline`.
- [ ] **Either** rename (GitHub redirects old URLs, but the codelab's raw-content link and README clone commands must be updated), **or** note the deviation for the grader.
- [ ] **Decision required from the team** — a rename late in the cycle breaks the `codelabs-preview.appspot.com` link in `README.md:17` unless updated in the same change. Recommend: keep the name, note the deviation. Low value, non-trivial breakage risk.

---

### 6.9 Sprint plan

**Sprint 1 — "Stop the bleeding, close the grade gap"** · 44 pts

| Story | Pts | Owner | Why now |
|---|---:|---|---|
| ORB-101 Cost baseline | 3 | Hemanth | Every day of delay costs ~$12 |
| ORB-102 Decommission Composer | 5 | Hemanth | The ~89% saving |
| ORB-107 Budget guardrails | 2 | Hemanth | Prevents recurrence; do it alongside 101 |
| ORB-104 `gpt-4` → `gpt-4o-mini` | 1 | PeiYing | One line; blocks ORB-201 |
| ORB-205 Attestation | 1 | Hemanth | One line, graded deliverable |
| ORB-201 Evaluation harness | 8 | PeiYing + Om | Longest lead time on the critical path |
| ORB-202 Score 5+ companies | 8 | All | The missing deliverable |
| ORB-203 Reflection | 3 | All | Completes Lab 9 |
| ORB-204 `/rag/search` | 2 | Om | Small, closes a Lab 4 checkpoint |
| ORB-103 Local Airflow | 5 | Hemanth | Protects the DAG demo after teardown |
| ORB-206 Host apps / declare local | 5 | Om | Cheapest remaining graded mark |
| ORB-501 Remove public bucket | 2 | Hemanth | Trivial, P1 security |

**Sprint goal:** GCP run-rate below $10/month, and every graded deliverable present in the repo.
**Order matters:** ORB-102's acceptance criteria require capturing DAG-run screenshots *before* teardown. Do not delete the environment first.

---

**Sprint 2 — "Make the docs true, make the pipeline run"** · 43 pts

| Story | Pts | Owner |
|---|---:|---|
| ORB-302 Replace results table | 5 | All |
| ORB-301 Correct RAG claims | 3 | PeiYing |
| ORB-303 Fix run instructions | 3 | Om |
| ORB-304 `.env.example` | 1 | Om |
| ORB-401 Consolidate DAGs | 3 | Hemanth |
| ORB-402 Importable DAGs → Cloud Run | 8 | Hemanth |
| ORB-403 Single data source of truth | 5 | Om |
| ORB-405 Real smoke tests + CI | 5 | Om |
| ORB-105 Right-size and reschedule | 3 | Hemanth |
| ORB-106 Lifecycle policies | 2 | Hemanth |
| ORB-502 Secret audit | 3 | Hemanth |
| ORB-601 Pin dependencies | 5 | PeiYing |

**Sprint goal:** no claim in the repo contradicts the code; DAGs import and run clean.

---

**Sprint 3 — "Harden and hand over"** · 21 pts (+ stretch)

| Story | Pts | Owner |
|---|---:|---|
| ORB-305 Architecture as-built | 6 | Hemanth |
| ORB-404 True delta refresh | 5 | Hemanth |
| ORB-503 Least-privilege SAs | 5 | Hemanth |
| ORB-602 Remove cruft | 1 | Om |
| ORB-603 Repo naming decision | 2 | Hemanth |
| M-07 Evidence pack consolidation | 2 | All |

**Sprint goal:** a clean clone runs, a new owner can operate it, and cost stays flat.

---

### 6.10 MoSCoW

| Must | Should | Could | Won't (this cycle) |
|---|---|---|---|
| ORB-101, 102, 104, 107, 201, 202, 203, 205 | ORB-103, 105, 106, 204, 206, 301, 302, 303, 401, 402, 501, 502 | ORB-304, 403, 404, 405, 601, 602, 305, 503 | ORB-603 (rename), multi-scorer inter-rater reliability, Part 2 scope |

---

## 7. Risk register

| ID | Risk | Prob. | Impact | Exposure | Mitigation | Owner |
|---|---|---|---|---|---|---|
| **R-01** | Composer has been billing since Nov 2025 → ~$3k+ already spent | **High** | **High** | **Critical** | ORB-101 today; ORB-102 immediately after. Check for unspent trial credit | Hemanth |
| **R-02** | Deleting Composer destroys the only evidence that DAGs ran | Medium | High | High | ORB-102 AC mandates snapshot + screenshots **before** deletion | Hemanth |
| **R-03** | Empty `EVAL.md` beside the codelab's confident metrics reads as fabricated results | **High** | **High** | **Critical** | ORB-202 then ORB-302, in that order. Never publish the table without the data | All |
| **R-04** | Legacy `gpt-4` 8k context overflows at `top_k=15`, so RAG dashboards fail *and* cost the most | Medium | Medium | Medium | ORB-104 fixes both; verify with the longest-context company | PeiYing |
| **R-05** | Evaluation reveals RAG genuinely outperforms Structured, contradicting the codelab's thesis | Low-Med | Medium | Medium | Report what the data shows. A well-argued unexpected result scores better than a defended unsupported one | All |
| **R-06** | Deployed Cloud Run Jobs cannot be re-run after teardown, so results are unreproducible | Medium | Medium | Medium | ORB-402/ORB-103 make a 3-company local run sufficient for reproduction | Hemanth |
| **R-07** | Composer scripts fail on rerun (D-02 invalid flags, masked by `\|\| echo`) | **High** | Low | Medium | ORB-105 removes error masking; ORB-103 removes the dependency entirely | Hemanth |
| **R-08** | Only one person has GCP billing access → cost work blocks | Medium | High | High | Confirm access as ORB-101's Definition of Ready; add a second viewer | Hemanth |
| **R-09** | Public dashboards bucket is indexed/crawled → egress cost + disclosure | Low | Medium | Low-Med | ORB-501 | Hemanth |
| **R-10** | Scope creep into fixing everything at once, delivering nothing | Medium | High | High | Sprint 1 is deliberately only cost + graded gap. Everything else waits | Scrum lead |

---

## 8. Working agreements

**Definition of Ready** — a story enters a sprint only when it has: a user-story statement, testable acceptance criteria, an owner, an estimate, dependencies identified, and any required access confirmed.

**Definition of Done**
1. Acceptance criteria all met and checked off.
2. Code committed to `claude/repo-status-workflow-643nke` (never directly to `main`).
3. Reviewed by one other member.
4. `pytest` green and DAGs import cleanly (once ORB-405 lands).
5. Documentation updated **in the same commit** as the behaviour change — this repo's core failure mode is docs drifting from code.
6. Any cost-affecting change verified against billing within 48h.
7. Evidence (log, screenshot, transcript) committed under `docs/evidence/` where the AC calls for it.
8. This document's finding registers updated to mark the item closed.

**Board columns:** `Backlog → Ready → In Progress (WIP limit 2/person) → In Review → Verified → Done`

**Ceremonies:** daily 10-min standup · sprint planning Monday · review + retro Friday · this document re-reviewed at each sprint boundary.

**Labels:** `cost` · `graded-deliverable` · `doc-drift` · `correctness` · `security` · `hygiene` · `P0`–`P3`

---

## 9. Traceability matrix

| Finding | Story | Epic |
|---|---|---|
| M-01 Empty EVAL.md | ORB-202 | E2 |
| M-02 No reflection | ORB-203 | E2 |
| M-03 No eval harness | ORB-201 | E2 |
| M-04 No `/rag/search` | ORB-204 | E2 |
| M-05 Attestation placeholders | ORB-205 | E2 |
| M-06 No hosted app URLs | ORB-206 | E2 |
| M-07 No evidence artifacts | ORB-102, ORB-202, Sprint 3 | E1/E2 |
| M-08 No `.env.example` | ORB-304 | E3 |
| M-09 No test suite | ORB-405 | E4 |
| M-10 No budget alerts | ORB-107 | E1 |
| M-11 No delta detection | ORB-404 | E4 |
| M-12 Repo name | ORB-603 | E6 |
| D-01 `gpt-4` hard-coded | ORB-104 | E1 |
| D-02 Composer 1 flags / masked failure | ORB-105, ORB-103 | E1 |
| D-03 Wrong timeout flag | ORB-105 | E1 |
| D-04 In-process DAG execution | ORB-402 | E4 |
| D-05 Bare imports in DAGs | ORB-402 | E4 |
| D-06 Public bucket | ORB-501 | E5 |
| D-07 Duplicated DAG dirs | ORB-401 | E4 |
| D-08 Schedule contradiction | ORB-401, ORB-305 | E4/E3 |
| D-09 Dual data sources | ORB-403 | E4 |
| D-10 Fake Streamlit fallback | ORB-403 | E4 |
| D-11 Starter-payload fallback | ORB-403 | E4 |
| D-12 Unpinned/unused deps | ORB-601 | E6 |
| D-13 FAISS vs Chroma | ORB-301 | E3 |
| D-14 Embedding model claim | ORB-301 | E3 |
| D-15 Model name claim | ORB-104, ORB-301 | E1/E3 |
| D-16 Unsubstantiated metrics | ORB-302 | E3 |
| D-17 Broken run commands | ORB-303 | E3 |
| D-18 Stale structure block | ORB-303 | E3 |
| D-19 Missing guide reference | ORB-303 | E3 |
| D-20 Wrong ignore claims | ORB-303 | E3 |
| D-21 Bucket count mismatch | ORB-303 | E3 |
| D-22 `.DS_Store` | ORB-602 | E6 |

---

## 10. Do this first

1. **Run `gcloud composer environments list --locations=us-central1`.** If it returns an environment, you are spending ~$350/month on a finished project — that single command is the highest-value action in this document.
2. Open the billing report and record the real total (ORB-101).
3. Change one line at `src/backend/rag_pipeline.py:88` (ORB-104).
4. Capture DAG-run screenshots, snapshot Composer, then delete it (ORB-102).
5. Start the evaluation harness (ORB-201) — it has the longest lead time on the graded critical path.

---

*Assessment based on repository state at commit `648193e`. Cost figures in §5 are modelled from committed resource specifications and public list prices, not from a billing-API reading; replace them with measured values via ORB-101.*
