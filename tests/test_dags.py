"""DAG structure tests.

These are static (AST-based) checks. Fully parsing the DAGs requires Airflow plus the
Google provider installed; use the local Airflow stack for that:

    docker compose -f docker/docker-compose.airflow.yml up -d
    docker compose -f docker/docker-compose.airflow.yml exec airflow \\
        airflow dags list-import-errors

What is covered here is the specific defect class that broke these DAGs in Cloud
Composer: importing modules from src/backend, which is never uploaded to the DAGs
bucket, so the imports cannot resolve at parse time.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

DAG_DIR = Path(__file__).resolve().parents[1] / "airflow" / "dags"

# Modules that only exist in src/backend and are therefore unavailable in Composer.
FORBIDDEN_IMPORT_ROOTS = {
    "scraper",
    "rag_pipeline",
    "playwright_scraper",
    "extractor_v4_bi",
    "payload_assembler",
    "models",
    "src",
}

REQUIRED_DAG_IDS = {"ai50_full_ingest_dag", "ai50_daily_refresh_dag"}


def dag_files() -> list[Path]:
    return sorted(DAG_DIR.glob("*.py"))


def module_roots(tree: ast.AST) -> set[str]:
    """Collect the top-level package of every import in a module."""
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                roots.add(node.module.split(".")[0])
            elif node.level:
                roots.add(f"<relative level {node.level}>")
    return roots


def dag_kwargs(tree: ast.AST) -> list[dict[str, ast.AST]]:
    """Extract keyword arguments from every DAG(...) construction in a module."""
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name == "DAG":
                found.append({kw.arg: kw.value for kw in node.keywords if kw.arg})
    return found


def literal(node: ast.AST):
    try:
        return ast.literal_eval(node)
    except Exception:  # noqa: BLE001
        return None


def test_dag_directory_exists():
    assert DAG_DIR.is_dir(), f"{DAG_DIR} missing"
    assert dag_files(), "no DAG files found"


def test_duplicate_dags_directory_removed():
    """dags/ and airflow/dags/ previously held divergent copies.

    Only airflow/dags/ is uploaded by setup_composer.sh, so the other tree was dead
    code that still read as authoritative.
    """
    duplicate = Path(__file__).resolve().parents[1] / "dags"
    assert not duplicate.exists(), (
        "dags/ still exists alongside airflow/dags/ - one source of truth only"
    )


@pytest.mark.parametrize("path", dag_files(), ids=lambda p: p.name)
def test_dag_file_is_syntactically_valid(path):
    ast.parse(path.read_text(), filename=str(path))


@pytest.mark.parametrize("path", dag_files(), ids=lambda p: p.name)
def test_dag_imports_nothing_from_src_backend(path):
    """The defect that made these DAGs unrunnable in Composer."""
    tree = ast.parse(path.read_text(), filename=str(path))
    offenders = module_roots(tree) & FORBIDDEN_IMPORT_ROOTS
    assert not offenders, (
        f"{path.name} imports {sorted(offenders)}, which is not shipped to the "
        f"Composer DAGs bucket and will fail at parse time"
    )


@pytest.mark.parametrize("path", dag_files(), ids=lambda p: p.name)
def test_dag_uses_no_relative_imports(path):
    tree = ast.parse(path.read_text(), filename=str(path))
    relative = {r for r in module_roots(tree) if r.startswith("<relative")}
    assert not relative, f"{path.name} uses relative imports, unsupported in a DAGs folder"


def test_required_dags_are_present():
    """Deliverable 4 names exactly these two DAGs."""
    ids = set()
    for path in dag_files():
        for kwargs in dag_kwargs(ast.parse(path.read_text())):
            value = literal(kwargs.get("dag_id"))
            if value:
                ids.add(value)
    assert REQUIRED_DAG_IDS <= ids, f"missing {REQUIRED_DAG_IDS - ids}"


def test_full_ingest_runs_once():
    """Lab 2: schedule @once."""
    tree = ast.parse((DAG_DIR / "ai50_full_ingest_dag.py").read_text())
    for kwargs in dag_kwargs(tree):
        if literal(kwargs.get("dag_id")) == "ai50_full_ingest_dag":
            assert literal(kwargs.get("schedule")) == "@once"
            return
    pytest.fail("ai50_full_ingest_dag not found")


def test_daily_refresh_runs_at_0300_utc():
    """Lab 3: schedule 0 3 * * *."""
    tree = ast.parse((DAG_DIR / "ai50_daily_refresh_dag.py").read_text())
    for kwargs in dag_kwargs(tree):
        if literal(kwargs.get("dag_id")) == "ai50_daily_refresh_dag":
            assert literal(kwargs.get("schedule")) == "0 3 * * *"
            return
    pytest.fail("ai50_daily_refresh_dag not found")


@pytest.mark.parametrize(
    "filename,expected_tasks",
    [
        (
            "ai50_full_ingest_dag.py",
            {"load_company_list", "scrape_company_pages", "store_raw_to_cloud"},
        ),
        (
            "ai50_daily_refresh_dag.py",
            {"load_company_list", "refresh_key_pages", "log_completion"},
        ),
    ],
)
def test_dag_declares_expected_tasks(filename, expected_tasks):
    """Lab 2 names load_company_list / scrape_company_pages / store_raw_to_cloud."""
    tree = ast.parse((DAG_DIR / filename).read_text())
    task_ids = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == "task_id":
                    value = literal(kw.value)
                    if value:
                        task_ids.add(value)
    assert expected_tasks <= task_ids, f"{filename} missing {expected_tasks - task_ids}"


@pytest.mark.parametrize(
    "filename",
    ["ai50_full_ingest_dag.py", "ai50_daily_refresh_dag.py"],
)
def test_heavy_work_is_delegated_to_cloud_run(filename):
    """Scraping and embedding must not run inside the Airflow worker."""
    source = (DAG_DIR / filename).read_text()
    assert "CloudRunExecuteJobOperator" in source, (
        f"{filename} does not delegate to Cloud Run; heavy work would run in-process "
        f"on the Airflow worker"
    )
