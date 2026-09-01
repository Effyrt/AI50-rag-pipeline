"""Data contract tests: the seed list, the Pydantic models, and payload shape."""
from __future__ import annotations

import json

import pytest


def test_seed_contains_all_fifty_companies(seed_companies):
    """The assignment requires all 50 Forbes AI 50 companies."""
    assert isinstance(seed_companies, list)
    assert len(seed_companies) == 50


def test_seed_entries_have_required_fields(seed_companies):
    for company in seed_companies:
        assert company.get("company_name"), f"missing company_name in {company}"
        assert company.get("company_id"), f"missing company_id for {company.get('company_name')}"
        assert company.get("website"), f"missing website for {company.get('company_name')}"


def test_seed_company_ids_are_unique(seed_companies):
    ids = [c["company_id"] for c in seed_companies]
    assert len(ids) == len(set(ids))


def test_starter_payload_validates_against_model(repo_root):
    from src.backend.models import Payload

    payload = Payload.model_validate_json(
        (repo_root / "data" / "starter_payload.json").read_text()
    )
    assert payload.company_record.legal_name


def test_payload_uses_company_record_key(starter_payload_dict):
    """Guards the api.py renderer bug.

    payload_assembler.py writes "company_record"; the renderer previously read
    "company" and so emitted "Not disclosed." for every field.
    """
    assert "company_record" in starter_payload_dict
    assert "company" not in starter_payload_dict


def test_structured_renderer_reads_real_company_fields(starter_payload_dict):
    from src.backend.api import generate_structured_dashboard_from_payload

    dashboard = generate_structured_dashboard_from_payload(starter_payload_dict)
    legal_name = starter_payload_dict["company_record"]["legal_name"]

    assert legal_name in dashboard, (
        "renderer did not surface the company name - it is probably reading the "
        "wrong payload key again"
    )


class TestLoadPayload:
    """load_payload must not substitute example data for a real company."""

    def test_missing_company_returns_none(self):
        from src.backend.structured_pipeline import load_payload

        assert load_payload("definitely-not-a-real-company-id") is None

    def test_data_dir_points_at_repo_root(self):
        from src.backend.structured_pipeline import DATA_DIR, REPO_ROOT

        # Previously parents[1] gave src/data/payloads, which never exists.
        assert DATA_DIR == REPO_ROOT / "data" / "payloads"
        assert DATA_DIR.parent.name == "data"
        assert (REPO_ROOT / "data" / "forbes_ai50_seed.json").exists()

    def test_starter_payload_available_explicitly(self):
        from src.backend.structured_pipeline import load_starter_payload

        assert load_starter_payload().company_record.legal_name
