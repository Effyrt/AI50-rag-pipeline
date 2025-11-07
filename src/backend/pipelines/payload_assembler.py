"""
Payload assembly logic for Lab 6.
"""
import logging
import json
from typing import Optional, List
from pathlib import Path
from datetime import datetime

from ..models.payload import InvestorDashboardPayload
from ..models.company import Company
from ..models.event import Event
from ..models.snapshot import Snapshot
from ..models.product import Product
from ..models.leadership import Leadership
from ..models.visibility import VisibilityMetrics
from ..config.settings import settings
from ..core.exceptions import PipelineError

logger = logging.getLogger(__name__)


class PayloadAssembler:
    """
    Assembles complete InvestorDashboardPayload from structured data files.
    
    This is Lab 6 - payload assembly.
    """
    
    def assemble_from_structured_dir(
        self,
        company_id: str,
        structured_dir: Optional[Path] = None
    ) -> InvestorDashboardPayload:
        """
        Assemble payload from structured data directory.
        
        Args:
            company_id: Company identifier
            structured_dir: Directory with structured JSON files
            
        Returns:
            Complete payload
        """
        structured_dir = structured_dir or settings.structured_data_dir
        
        # Load main structured file
        structured_file = structured_dir / f"{company_id}.json"
        
        if not structured_file.exists():
            raise PipelineError(
                f"Structured data file not found: {structured_file}",
                error_code="STRUCTURED_FILE_NOT_FOUND"
            )
        
        logger.info(f"Loading structured data from {structured_file}")
        
        with open(structured_file) as f:
            data = json.load(f)
        
        # Parse into payload
        try:
            payload = InvestorDashboardPayload.model_validate(data)
            logger.info(f"Successfully assembled payload for {payload.company_record.display_name}")
            return payload
        
        except Exception as e:
            logger.error(f"Failed to parse structured data: {e}", exc_info=True)
            raise PipelineError(
                f"Failed to assemble payload: {e}",
                error_code="PAYLOAD_ASSEMBLY_FAILED",
                details={"company_id": company_id, "error": str(e)}
            )
    
    def assemble_from_components(
        self,
        company_record: Company,
        events: Optional[List[Event]] = None,
        snapshots: Optional[List[Snapshot]] = None,
        products: Optional[List[Product]] = None,
        leadership: Optional[List[Leadership]] = None,
        visibility: Optional[List[VisibilityMetrics]] = None,
        notes: Optional[str] = None
    ) -> InvestorDashboardPayload:
        """
        Assemble payload from individual components.
        
        Args:
            company_record: Company profile
            events: List of events
            snapshots: List of snapshots
            products: List of products
            leadership: List of leaders
            visibility: List of visibility metrics
            notes: Additional notes
            
        Returns:
            Complete payload
        """
        payload = InvestorDashboardPayload(
            company_record=company_record,
            events=events or [],
            snapshots=snapshots or [],
            products=products or [],
            leadership=leadership or [],
            visibility=visibility or [],
            notes=notes or ""
        )
        
        logger.info(f"Assembled payload for {company_record.display_name}")
        logger.info(f"  - Events: {len(payload.events)}")
        logger.info(f"  - Snapshots: {len(payload.snapshots)}")
        logger.info(f"  - Products: {len(payload.products)}")
        logger.info(f"  - Leadership: {len(payload.leadership)}")
        logger.info(f"  - Visibility: {len(payload.visibility)}")
        logger.info(f"  - Data quality: {payload.quality_grade}")
        
        return payload
    
    def validate_payload(self, payload: InvestorDashboardPayload) -> dict:
        """
        Validate payload completeness and quality.
        
        Args:
            payload: Payload to validate
            
        Returns:
            Validation results dictionary
        """
        results = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "completeness": payload.data_completeness_score,
            "quality_grade": payload.quality_grade
        }
        
        # Check required fields
        if not payload.company_record.legal_name:
            results["errors"].append("Company legal_name is required")
            results["valid"] = False
        
        if not payload.company_record.website:
            results["warnings"].append("Company website is missing")
        
        # Check funding data
        if not payload.company_record.total_raised_usd and not payload.funding_events:
            results["warnings"].append("No funding data available")
        
        # Check team data
        if not payload.leadership:
            results["warnings"].append("No leadership data available")
        
        if not payload.founders:
            results["warnings"].append("No founder information available")
        
        # Check product data
        if not payload.products:
            results["warnings"].append("No product data available")
        
        # Check metrics
        if not payload.snapshots:
            results["warnings"].append("No snapshot data available")
        
        if not payload.visibility:
            results["warnings"].append("No visibility data available")
        
        logger.info(f"Payload validation: {results['quality_grade']} grade")
        
        if results["warnings"]:
            logger.warning(f"Validation warnings: {len(results['warnings'])}")
            for warning in results["warnings"]:
                logger.warning(f"  - {warning}")
        
        if results["errors"]:
            logger.error(f"Validation errors: {len(results['errors'])}")
            for error in results["errors"]:
                logger.error(f"  - {error}")
        
        return results
    
    def save_payload(
        self,
        payload: InvestorDashboardPayload,
        output_dir: Optional[Path] = None
    ) -> Path:
        """
        Save payload to disk.
        
        Args:
            payload: Payload to save
            output_dir: Output directory
            
        Returns:
            Path to saved file
        """
        output_dir = output_dir or settings.payload_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        
        company_id = payload.company_record.company_id
        output_file = output_dir / f"{company_id}.json"
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(payload.model_dump_json(indent=2))
        
        logger.info(f"Saved payload to {output_file}")
        
        return output_file