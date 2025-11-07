"""
Instructor-based structured extraction from raw text.
"""
import logging
from typing import Optional, List, Type, TypeVar
from datetime import date, datetime
from pathlib import Path

from ..models.company import Company
from ..models.event import Event
from ..models.snapshot import Snapshot
from ..models.product import Product
from ..models.leadership import Leadership
from ..models.visibility import VisibilityMetrics
from ..models.provenance import Provenance, DataSourceType, ScrapingMethod
from ..llm.client import get_llm_client
from ..llm.prompts import ExtractionPrompts, format_extraction_prompt, create_messages
from ..config.settings import settings
from ..core.exceptions import ExtractionError
from ..core.telemetry import track_time

logger = logging.getLogger(__name__)

T = TypeVar("T")


class InstructorExtractor:
    """
    Extract structured Pydantic models from raw text using LLM + instructor.
    
    This is the core of Lab 5 - structured extraction pipeline.
    """
    
    def __init__(self):
        self.llm_client = get_llm_client()
    
    @track_time("extract_company_profile")
    def extract_company_profile(
        self,
        content: str,
        source_url: str,
        company_name: Optional[str] = None
    ) -> Company:
        """
        Extract company profile from website content.
        
        Args:
            content: Raw text from company website
            source_url: Source URL
            company_name: Known company name (optional)
            
        Returns:
            Company model instance
        """
        logger.info(f"Extracting company profile from {source_url}")
        
        try:
            # Prepare prompt
            user_prompt = format_extraction_prompt(
                ExtractionPrompts.COMPANY_PROFILE,
                content=content[:8000]  # Limit content length
            )
            
            messages = create_messages(
                system_prompt="You are an expert at extracting company information from websites.",
                user_prompt=user_prompt
            )
            
            # Extract using instructor
            company = self.llm_client.extract(
                response_model=Company,
                messages=messages
            )
            
            # Add provenance
            provenance = Provenance(
                source_url=source_url,
                scraped_at=datetime.utcnow(),
                scraping_method=ScrapingMethod.INSTRUCTOR_LLM,
                source_type=DataSourceType.OFFICIAL_WEBSITE,
                confidence_score=0.9,
                extractor_model=settings.llm_model,
                snippet=content[:200]
            )
            
            company.provenance.append(provenance)
            
            # Override company name if provided
            if company_name:
                company.legal_name = company_name
                if not company.brand_name:
                    company.brand_name = company_name
            
            logger.info(f"Successfully extracted company profile: {company.display_name}")
            
            return company
        
        except Exception as e:
            logger.error(f"Company extraction failed: {e}", exc_info=True)
            raise ExtractionError(
                f"Failed to extract company profile: {e}",
                error_code="COMPANY_EXTRACTION_FAILED",
                details={"source_url": source_url, "error": str(e)}
            )
    
    @track_time("extract_funding_events")
    def extract_funding_events(
        self,
        content: str,
        source_url: str,
        company_id: str
    ) -> List[Event]:
        """
        Extract funding events from content.
        
        Args:
            content: Raw text mentioning funding
            source_url: Source URL
            company_id: Associated company ID
            
        Returns:
            List of Event instances
        """
        logger.info(f"Extracting funding events from {source_url}")
        
        try:
            user_prompt = format_extraction_prompt(
                ExtractionPrompts.FUNDING_EVENTS,
                content=content[:8000]
            )
            
            messages = create_messages(
                system_prompt="You are an expert at extracting funding information from text.",
                user_prompt=user_prompt
            )
            
            # Extract list of events
            events = self.llm_client.extract(
                response_model=List[Event],
                messages=messages
            )
            
            # Add metadata
            provenance = Provenance(
                source_url=source_url,
                scraped_at=datetime.utcnow(),
                scraping_method=ScrapingMethod.INSTRUCTOR_LLM,
                source_type=DataSourceType.OFFICIAL_WEBSITE,
                confidence_score=0.85,
                extractor_model=settings.llm_model
            )
            
            for event in events:
                event.company_id = company_id
                event.provenance.append(provenance)
            
            logger.info(f"Extracted {len(events)} funding events")
            
            return events
        
        except Exception as e:
            logger.warning(f"Funding extraction failed: {e}")
            return []
    
    @track_time("extract_leadership")
    def extract_leadership(
        self,
        content: str,
        source_url: str,
        company_id: str
    ) -> List[Leadership]:
        """
        Extract leadership team from content.
        
        Args:
            content: Raw text about team/leadership
            source_url: Source URL
            company_id: Associated company ID
            
        Returns:
            List of Leadership instances
        """
        logger.info(f"Extracting leadership from {source_url}")
        
        try:
            user_prompt = format_extraction_prompt(
                ExtractionPrompts.TEAM_EXTRACTION,
                content=content[:8000]
            )
            
            messages = create_messages(
                system_prompt="You are an expert at extracting leadership team information.",
                user_prompt=user_prompt
            )
            
            leaders = self.llm_client.extract(
                response_model=List[Leadership],
                messages=messages
            )
            
            provenance = Provenance(
                source_url=source_url,
                scraped_at=datetime.utcnow(),
                scraping_method=ScrapingMethod.INSTRUCTOR_LLM,
                source_type=DataSourceType.OFFICIAL_WEBSITE,
                confidence_score=0.9,
                extractor_model=settings.llm_model
            )
            
            for leader in leaders:
                leader.company_id = company_id
                leader.provenance.append(provenance)
            
            logger.info(f"Extracted {len(leaders)} leaders")
            
            return leaders
        
        except Exception as e:
            logger.warning(f"Leadership extraction failed: {e}")
            return []
    
    @track_time("extract_products")
    def extract_products(
        self,
        content: str,
        source_url: str,
        company_id: str
    ) -> List[Product]:
        """
        Extract products from content.
        
        Args:
            content: Raw text about products/services
            source_url: Source URL
            company_id: Associated company ID
            
        Returns:
            List of Product instances
        """
        logger.info(f"Extracting products from {source_url}")
        
        try:
            user_prompt = format_extraction_prompt(
                ExtractionPrompts.PRODUCT_EXTRACTION,
                content=content[:8000]
            )
            
            messages = create_messages(
                system_prompt="You are an expert at extracting product information.",
                user_prompt=user_prompt
            )
            
            products = self.llm_client.extract(
                response_model=List[Product],
                messages=messages
            )
            
            provenance = Provenance(
                source_url=source_url,
                scraped_at=datetime.utcnow(),
                scraping_method=ScrapingMethod.INSTRUCTOR_LLM,
                source_type=DataSourceType.OFFICIAL_WEBSITE,
                confidence_score=0.85,
                extractor_model=settings.llm_model
            )
            
            for product in products:
                product.company_id = company_id
                product.provenance.append(provenance)
            
            logger.info(f"Extracted {len(products)} products")
            
            return products
        
        except Exception as e:
            logger.warning(f"Product extraction failed: {e}")
            return []
    
    @track_time("extract_snapshot")
    def extract_snapshot(
        self,
        content: str,
        source_url: str,
        company_id: str,
        as_of_date: Optional[date] = None
    ) -> Snapshot:
        """
        Extract current metrics snapshot from content.
        
        Args:
            content: Raw text about company metrics
            source_url: Source URL
            company_id: Associated company ID
            as_of_date: Date for snapshot (defaults to today)
            
        Returns:
            Snapshot instance
        """
        logger.info(f"Extracting snapshot from {source_url}")
        
        as_of_date = as_of_date or date.today()
        
        try:
            user_prompt = format_extraction_prompt(
                ExtractionPrompts.SNAPSHOT_EXTRACTION,
                content=content[:8000],
                as_of_date=as_of_date.isoformat()
            )
            
            messages = create_messages(
                system_prompt="You are an expert at extracting company metrics.",
                user_prompt=user_prompt
            )
            
            snapshot = self.llm_client.extract(
                response_model=Snapshot,
                messages=messages
            )
            
            snapshot.company_id = company_id
            snapshot.as_of = as_of_date
            
            provenance = Provenance(
                source_url=source_url,
                scraped_at=datetime.utcnow(),
                scraping_method=ScrapingMethod.INSTRUCTOR_LLM,
                source_type=DataSourceType.OFFICIAL_WEBSITE,
                confidence_score=0.8,
                extractor_model=settings.llm_model
            )
            
            snapshot.provenance.append(provenance)
            
            logger.info("Successfully extracted snapshot")
            
            return snapshot
        
        except Exception as e:
            logger.warning(f"Snapshot extraction failed: {e}")
            # Return empty snapshot
            return Snapshot(
                company_id=company_id,
                as_of=as_of_date
            )
    
    @track_time("extract_visibility")
    def extract_visibility(
        self,
        content: str,
        source_url: str,
        company_id: str,
        as_of_date: Optional[date] = None
    ) -> VisibilityMetrics:
        """
        Extract visibility metrics from content.
        
        Args:
            content: Raw text about company visibility
            source_url: Source URL
            company_id: Associated company ID
            as_of_date: Date for metrics (defaults to today)
            
        Returns:
            VisibilityMetrics instance
        """
        logger.info(f"Extracting visibility metrics from {source_url}")
        
        as_of_date = as_of_date or date.today()
        
        try:
            user_prompt = format_extraction_prompt(
                ExtractionPrompts.VISIBILITY_EXTRACTION,
                content=content[:8000]
            )
            
            messages = create_messages(
                system_prompt="You are an expert at analyzing company visibility and sentiment.",
                user_prompt=user_prompt
            )
            
            visibility = self.llm_client.extract(
                response_model=VisibilityMetrics,
                messages=messages
            )
            
            visibility.company_id = company_id
            visibility.as_of = as_of_date
            
            provenance = Provenance(
                source_url=source_url,
                scraped_at=datetime.utcnow(),
                scraping_method=ScrapingMethod.INSTRUCTOR_LLM,
                source_type=DataSourceType.OFFICIAL_WEBSITE,
                confidence_score=0.75,
                extractor_model=settings.llm_model
            )
            
            visibility.provenance.append(provenance)
            
            logger.info("Successfully extracted visibility metrics")
            
            return visibility
        
        except Exception as e:
            logger.warning(f"Visibility extraction failed: {e}")
            return VisibilityMetrics(
                company_id=company_id,
                as_of=as_of_date
            )