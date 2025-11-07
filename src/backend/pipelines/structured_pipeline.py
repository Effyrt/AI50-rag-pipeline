"""
Structured pipeline for dashboard generation using Pydantic payloads.
"""
import logging
import json
from typing import Optional
from pathlib import Path

from ..models.payload import InvestorDashboardPayload
from ..llm.client import get_llm_client
from ..llm.prompts import DashboardPrompts, create_messages
from ..config.settings import settings
from ..core.exceptions import PipelineError
from ..core.telemetry import track_time

logger = logging.getLogger(__name__)


class StructuredPipeline:
    """
    Structured pipeline for Lab 8 - Structured Dashboard Generation.
    
    Flow:
    1. Load structured payload (Pydantic models)
    2. Convert to LLM-friendly context
    3. Generate dashboard using LLM + structured data
    """
    
    def __init__(self):
        self.llm_client = get_llm_client()
    
    def load_payload(
        self,
        company_id: str,
        payload_dir: Optional[Path] = None
    ) -> Optional[InvestorDashboardPayload]:
        """
        Load payload from disk.
        
        Args:
            company_id: Company identifier
            payload_dir: Directory with payload files
            
        Returns:
            Payload instance or None if not found
        """
        payload_dir = payload_dir or settings.payload_dir
        payload_file = payload_dir / f"{company_id}.json"
        
        if not payload_file.exists():
            logger.warning(f"Payload not found: {payload_file}")
            return None
        
        logger.info(f"Loading payload from {payload_file}")
        
        try:
            with open(payload_file) as f:
                data = json.load(f)
            
            payload = InvestorDashboardPayload.model_validate(data)
            logger.info(f"Loaded payload for {payload.company_record.display_name}")
            
            return payload
        
        except Exception as e:
            logger.error(f"Failed to load payload: {e}", exc_info=True)
            raise PipelineError(
                f"Failed to load payload: {e}",
                error_code="PAYLOAD_LOAD_FAILED",
                details={"company_id": company_id, "error": str(e)}
            )
    
    @track_time("generate_dashboard_structured")
    def generate_dashboard(
        self,
        payload: InvestorDashboardPayload
    ) -> str:
        """
        Generate investor dashboard from structured payload.
        
        Args:
            payload: Complete structured payload
            
        Returns:
            Generated dashboard in Markdown
        """
        company_name = payload.company_record.display_name
        logger.info(f"Generating structured dashboard for {company_name}")
        
        # Convert payload to LLM context
        context = payload.to_llm_context()
        context_json = json.dumps(context, indent=2)
        
        # Generate dashboard
        user_prompt = DashboardPrompts.STRUCTURED_DASHBOARD.format(
            company_name=company_name,
            payload=context_json
        )
        
        messages = create_messages(
            system_prompt=DashboardPrompts.SYSTEM_PROMPT,
            user_prompt=user_prompt
        )
        
        dashboard = self.llm_client.complete(
            messages=messages,
            temperature=0.0,
            max_tokens=4096
        )
        
        logger.info(f"Generated {len(dashboard)} character dashboard")
        
        return dashboard
    
    def generate_dashboard_by_id(
        self,
        company_id: str
    ) -> str:
        """
        Generate dashboard by company ID.
        
        Args:
            company_id: Company identifier
            
        Returns:
            Generated dashboard
        """
        payload = self.load_payload(company_id)
        
        if not payload:
            raise PipelineError(
                f"No payload found for company_id: {company_id}",
                error_code="PAYLOAD_NOT_FOUND"
            )
        
        return self.generate_dashboard(payload)