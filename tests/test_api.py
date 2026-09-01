"""API route tests. All external calls are mocked; no credentials required."""
from __future__ import annotations

import pytest


class TestRootEndpoint:
    def test_root_reports_healthy(self, api_client):
        r = api_client.get("/")
        assert r.status_code == 200
        assert r.json()["status"] == "operational"

    def test_root_reports_data_source(self, api_client):
        """Which data source is active must never be ambiguous."""
        body = api_client.get("/").json()
        assert "data_source" in body
        assert "local disk" in body["data_source"]  # no GCS_BUCKET_NAME in tests

    def test_root_advertises_rag_search(self, api_client):
        assert "rag_search" in api_client.get("/").json()["endpoints"]


class TestCompaniesEndpoint:
    def test_returns_all_fifty(self, api_client):
        r = api_client.get("/companies")
        assert r.status_code == 200
        assert r.json()["total_count"] == 50

    def test_company_entries_are_populated(self, api_client):
        companies = api_client.get("/companies").json()["companies"]
        first = companies[0]
        assert first["company_name"]
        assert first["company_id"]


class TestRagSearchEndpoint:
    """Lab 4 task 3: the retrieval-test endpoint."""

    def test_search_returns_hits(self, api_client):
        r = api_client.get("/rag/search", params={"q": "funding", "k": 3})
        assert r.status_code == 200
        body = r.json()
        assert body["query"] == "funding"
        assert body["hit_count"] == 3
        assert len(body["hits"]) == 3

    def test_hits_expose_source_and_score(self, api_client):
        hit = api_client.get("/rag/search", params={"q": "leadership"}).json()["hits"][0]
        assert hit["source"].startswith("http")
        assert hit["score"] is not None
        assert hit["content"]

    def test_company_filter_is_passed_through(self, api_client):
        body = api_client.get(
            "/rag/search", params={"q": "funding", "company": "Abridge"}
        ).json()
        assert body["company"] == "Abridge"
        assert body["hits"][0]["company"] == "Abridge"

    def test_empty_query_rejected(self, api_client):
        assert api_client.get("/rag/search", params={"q": "   "}).status_code == 422

    def test_missing_query_rejected(self, api_client):
        assert api_client.get("/rag/search").status_code == 422

    @pytest.mark.parametrize("k", [0, -1, 51])
    def test_out_of_range_k_rejected(self, api_client, k):
        assert api_client.get("/rag/search", params={"q": "x", "k": k}).status_code == 422


class TestStructuredDashboardEndpoint:
    def test_missing_company_returns_404_not_500(self, api_client):
        """Regression test.

        The 404 raised for a missing company was caught by a bare `except Exception`
        wrapping the whole handler and re-raised as a 500 with the 404 text embedded.
        """
        r = api_client.post(
            "/dashboard/structured", json={"company_name": "No Such Company Ltd"}
        )
        assert r.status_code == 404
        assert "not found" in r.json()["detail"].lower()

    def test_404_detail_names_the_data_source(self, api_client):
        detail = api_client.post(
            "/dashboard/structured", json={"company_name": "No Such Company Ltd"}
        ).json()["detail"]
        assert "local disk" in detail or "GCS" in detail


class TestRagDashboardEndpoint:
    def test_generates_dashboard(self, api_client):
        r = api_client.post("/dashboard/rag", json={"company_name": "Abridge", "top_k": 5})
        assert r.status_code == 200
        body = r.json()
        assert body["company_name"] == "Abridge"
        assert "## Company Overview" in body["dashboard"]


def test_openapi_lists_rag_search(api_client):
    """The endpoint must be discoverable at /docs."""
    paths = api_client.get("/openapi.json").json()["paths"]
    assert "/rag/search" in paths
    assert "get" in paths["/rag/search"]
