"""
High-level company data extractor orchestrating all extraction tasks.
"""
import logging
import json
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import date

from .instructor_extractor import InstructorExtractor
from ..models.payload import InvestorDashboardPayload
from ..config.settings import settings
from ..core.exceptions import ExtractionError
from ..core.telemetry import track_time

logger = logging.getLogger(__name__)


class CompanyDataExtractor:
    """
    Orchestrates extraction of all company data from scraped pages.
    
    This is the main entry point for Lab 5 - structured extraction.
    """
    
    def __init__(self):
        self.extractor = InstructorExtractor()
    
    @track_time("extract_full_company_data")
    def extract_from_scraped_data(
        self,
        company_id: str,
        company_name: str,
        scraped_data: Dict[str, Any]
    ) -> InvestorDashboardPayload:
        """
        Extract complete company data from scraped pages.
        
        Args:
            company_id: Company identifier
            company_name: Company name
            scraped_data: Dictionary with scraped page data
            
        Returns:
            Complete InvestorDashboardPayload
        """
        logger.info(f"Extracting full data for {company_name}")
        
        # Extract company profile from homepage
        company_record = None
        if "homepage" in scraped_data.get("pages", {}):
            homepage = scraped_data["pages"]["homepage"]
            if "text" in homepage and not homepage.get("error"):
                company_record = self.extractor.extract_company_profile(
                    content=homepage["text"],
                    source_url=homepage["url"],
                    company_name=company_name
                )
                company_record.company_id = company_id
        
        if not company_record:
            raise ExtractionError(
                f"Failed to extract company profile for {company_name}",
                error_code="NO_COMPANY_PROFILE"
            )
        
        # Extract from other pages
        events = []
        leadership = []
        products = []
        snapshots = []
        visibility = []
        
        pages = scraped_data.get("pages", {})
        
        # Extract from About page
        if "about" in pages and pages["about"] and not pages["about"].get("error"):
            about_page = pages["about"]
            content = about_page.get("text", "")
            url = about_page.get("url", "")
            
            # Extract leadership from about page
            leaders = self.extractor.extract_leadership(
                content=content,
                source_url=url,
                company_id=company_id
            )
            leadership.extend(leaders)
            
            # Extract additional company info
            # (Could enhance company_record here)
        
        # Extract from Product page
        if "product" in pages and pages["product"] and not pages["product"].get("error"):
            product_page = pages["product"]
            content = product_page.get("text", "")
            url = product_page.get("url", "")
            
            prods = self.extractor.extract_products(
                content=content,
                source_url=url,
                company_id=company_id
            )
            products.extend(prods)
        
        # Extract from Careers page
        if "careers" in pages and pages["careers"] and not pages["careers"].get("error"):
            careers_page = pages["careers"]
            content = careers_page.get("text", "")
            url = careers_page.get("url", "")
            
            snapshot = self.extractor.extract_snapshot(
                content=content,
                source_url=url,
                company_id=company_id,
                as_of_date=date.today()
            )
            snapshots.append(snapshot)
        
        # Extract from Blog/News page
        if "blog" in pages and pages["blog"] and not pages["blog"].get("error"):
            blog_page = pages["blog"]
            content = blog_page.get("text", "")
            url = blog_page.get("url", "")
            
            # Extract events from blog
            blog_events = self.extractor.extract_funding_events(
                content=content,
                source_url=url,
                company_id=company_id
            )
            events.extend(blog_events)
            
            # Extract visibility metrics
            vis = self.extractor.extract_visibility(
                content=content,
                source_url=url,
                company_id=company_id,
                as_of_date=date.today()
            )
            visibility.append(vis)
        
        # Assemble payload
        payload = InvestorDashboardPayload(
            company_record=company_record,
            events=events,
            snapshots=snapshots,
            products=products,
            leadership=leadership,
            visibility=visibility,
            notes=f"Extracted from {len(pages)} scraped pages"
        )
        
        logger.info(
            f"Extraction complete: {len(events)} events, "
            f"{len(leadership)} leaders, {len(products)} products"
        )
        
        return payload
    
    def extract_from_raw_directory(
        self,
        company_id: str,
        company_name: str,
        raw_dir: Optional[Path] = None
    ) -> InvestorDashboardPayload:
        """
        Extract data from raw scraped directory structure.
        
        Args:
            company_id: Company identifier
            company_name: Company name
            raw_dir: Path to raw data directory (defaults to settings)
            
        Returns:
            Complete payload
        """
        raw_dir = raw_dir or settings.raw_data_dir
        company_dir = raw_dir / company_id
        
        if not company_dir.exists():
            raise ExtractionError(
                f"Raw data directory not found: {company_dir}",
                error_code="DIRECTORY_NOT_FOUND"
            )
        
        # Find most recent scrape
        run_dirs = sorted(
            [d for d in company_dir.iterdir() if d.is_dir()],
            reverse=True
        )
        
        if not run_dirs:
            raise ExtractionError(
                f"No scrape runs found in {company_dir}",
                error_code="NO_SCRAPE_DATA"
            )
        
        latest_run = run_dirs[0]
        logger.info(f"Using latest scrape: {latest_run.name}")
        
        # Load metadata
        metadata_file = latest_run / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file) as f:
                metadata = json.load(f)
        else:
            metadata = {}
        
        # Load scraped pages
        scraped_data = {
            "company_id": company_id,
            "company_name": company_name,
            "pages": {}
        }
        
        for page_type in ["homepage", "about", "product", "careers", "blog"]:
            page_dir = latest_run / page_type
            
            if not page_dir.exists():
                continue
            
            # Load clean text
            text_file = page_dir / "clean.txt"
            if text_file.exists():
                with open(text_file, encoding="utf-8") as f:
                    text = f.read()
            else:
                text = ""
            
            # Load page metadata
            page_meta_file = page_dir / "metadata.json"
            if page_meta_file.exists():
                with open(page_meta_file) as f:
                    page_meta = json.load(f)
            else:
                page_meta = {}
            
            scraped_data["pages"][page_type] = {
                "text": text,
                "url": page_meta.get("url", ""),
                "page_type": page_type
            }
        
        # Extract from loaded data
        return self.extract_from_scraped_data(
            company_id=company_id,
            company_name=company_name,
            scraped_data=scraped_data
        )
    
    def save_structured_data(
        self,
        payload: InvestorDashboardPayload,
        output_dir: Optional[Path] = None
    ):
        """
        Save structured payload to disk.
        
        Args:
            payload: Payload to save
            output_dir: Output directory (defaults to settings)
        """
        output_dir = output_dir or settings.structured_data_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        
        company_id = payload.company_record.company_id
        output_file = output_dir / f"{company_id}.json"
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(payload.model_dump_json(indent=2))
        
        logger.info(f"Saved structured data to {output_file}")
    
    def save_payload(
        self,
        payload: InvestorDashboardPayload,
        output_dir: Optional[Path] = None
    ):
        """
        Save final payload to payloads directory.
        
        Args:
            payload: Payload to save
            output_dir: Output directory (defaults to settings)
        """
        output_dir = output_dir or settings.payload_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        
        company_id = payload.company_record.company_id
        output_file = output_dir / f"{company_id}.json"
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(payload.model_dump_json(indent=2))
        
        logger.info(f"Saved payload to {output_file}")