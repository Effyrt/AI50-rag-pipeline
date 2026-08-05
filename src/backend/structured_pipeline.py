"""Structured pipeline payload loading.

Loads the assembled payload for a company (Lab 6 output) so the structured
dashboard prompt can be built from validated data.
"""
from pathlib import Path
from typing import Optional

from .models import Payload

# Repo root is three levels up from this file: src/backend/structured_pipeline.py
# -> src/backend -> src -> <repo root>. This previously used parents[1], which
# resolved to src/data/payloads - a directory that does not exist - so every
# lookup missed and silently fell through to the starter payload.
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "payloads"
STARTER_PAYLOAD = REPO_ROOT / "data" / "starter_payload.json"


def load_payload(company_id: str) -> Optional[Payload]:
    """Load the assembled payload for a company.

    Returns None when no payload exists for that company. It deliberately does
    NOT fall back to the starter payload: doing so returned example data labelled
    as the requested company, which is indistinguishable from a real result.
    Callers should treat None as "not found" and surface a 404.
    """
    fp = DATA_DIR / f"{company_id}.json"
    if not fp.exists():
        return None
    return Payload.model_validate_json(fp.read_text())


def load_starter_payload() -> Payload:
    """Load the starter payload explicitly, for tests and local demos.

    Kept as a separate, clearly named function so example data can never be
    served in place of a real company payload by accident.
    """
    return Payload.model_validate_json(STARTER_PAYLOAD.read_text())
