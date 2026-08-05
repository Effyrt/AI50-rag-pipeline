"""Shared pytest fixtures.

Every test in this suite must pass with no OPENAI_API_KEY and no GCP credentials.
External calls are mocked; nothing here reaches the network.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture(autouse=True)
def no_credentials(monkeypatch):
    """Guarantee tests never pick up real credentials from the environment."""
    for var in (
        "OPENAI_API_KEY",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GCS_BUCKET_NAME",
        "GCP_PROJECT_ID",
    ):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def seed_companies(repo_root) -> list[dict]:
    import json

    return json.loads((repo_root / "data" / "forbes_ai50_seed.json").read_text())


@pytest.fixture
def starter_payload_dict(repo_root) -> dict:
    import json

    return json.loads((repo_root / "data" / "starter_payload.json").read_text())


@pytest.fixture
def api_client(monkeypatch):
    """TestClient for the FastAPI app with the RAG pipeline stubbed out.

    RAGPipeline is never constructed: doing so downloads a sentence-transformers
    model and opens a Chroma store, neither of which belongs in a unit test.
    """
    from fastapi.testclient import TestClient

    from src.backend import api as api_module

    class StubRAG:
        def search(self, query, company_name=None, k=5):
            return [
                {
                    "content": f"chunk about {query}",
                    "metadata": {"source": "https://example.com/about"},
                    "source": "https://example.com/about",
                    "company": company_name or "ExampleCo",
                    "score": 0.42,
                }
                for _ in range(k)
            ]

        def generate_dashboard(self, company_name, top_k=15):
            return f"# {company_name}\n\n## Company Overview\nNot disclosed."

    monkeypatch.setattr(api_module, "get_rag_pipeline", lambda: StubRAG())
    monkeypatch.setattr(api_module, "get_gcs_client", lambda: None)

    return TestClient(api_module.app)
