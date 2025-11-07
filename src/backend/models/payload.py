"""
Complete payload model assembling all company data.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from .company import Company
from .event import Event
from .snapshot import Snapshot
from .product import Product
from .leadership import Leadership
from .visibility import VisibilityMetrics


class InvestorDashboardPayload(BaseModel):
    """
    Complete payload for investor dashboard generation.
    
    This is the unified data structure that gets passed to the LLM
    for dashboard generation.
    """
    
    # Core company record
    company_record: Company = Field(
        ...,
        description="Primary company profile"
    )
    
    # Time-series data
    events: List[Event] = Field(
        default_factory=list,
        description="Company events (funding, partnerships, etc.)"
    )
    
    snapshots: List[Snapshot] = Field(
        default_factory=list,
        description="Point-in-time snapshots of company metrics"
    )
    
    # Related entities
    products: List[Product] = Field(
        default_factory=list,
        description="Company products and services"
    )
    
    leadership: List[Leadership] = Field(
        default_factory=list,
        description="Leadership team members"
    )
    
    visibility: List[VisibilityMetrics] = Field(
        default_factory=list,
        description="Visibility and sentiment metrics"
    )
    
    # Additional context
    notes: Optional[str] = Field(
        None,
        description="Additional analyst notes or context"
    )
    
    provenance_policy: str = Field(
        default=(
            "Use only the sources you scraped. "
            "If a field is missing, write 'Not disclosed.' "
            "Do not infer valuation, ARR, or customer counts. "
            "If a claim sounds like marketing, attribute it: 'The company states...'"
        ),
        description="Rules for using provenance data"
    )
    
    # Metadata
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this payload was generated"
    )
    
    payload_version: str = Field(
        default="2.1.0",
        description="Payload schema version"
    )
    
    @property
    def latest_snapshot(self) -> Optional[Snapshot]:
        """Get most recent snapshot."""
        if not self.snapshots:
            return None
        return max(self.snapshots, key=lambda s: s.as_of)
    
    @property
    def latest_visibility(self) -> Optional[VisibilityMetrics]:
        """Get most recent visibility metrics."""
        if not self.visibility:
            return None
        return max(self.visibility, key=lambda v: v.as_of)
    
    @property
    def funding_events(self) -> List[Event]:
        """Get all funding events."""
        return [e for e in self.events if e.is_funding]
    
    @property
    def total_funding_from_events(self) -> float:
        """Calculate total funding from events."""
        return sum(
            e.amount_usd for e in self.funding_events
            if e.amount_usd is not None
        )
    
    @property
    def latest_funding_event(self) -> Optional[Event]:
        """Get most recent funding event."""
        funding = self.funding_events
        if not funding:
            return None
        return max(funding, key=lambda e: e.occurred_on)
    
    @property
    def current_leaders(self) -> List[Leadership]:
        """Get current leadership team."""
        return [l for l in self.leadership if l.is_current]
    
    @property
    def founders(self) -> List[Leadership]:
        """Get company founders."""
        return [l for l in self.leadership if l.is_founder]
    
    @property
    def active_products(self) -> List[Product]:
        """Get active (non-deprecated) products."""
        return [p for p in self.products if not p.is_deprecated]
    
    @property
    def data_completeness_score(self) -> float:
        """
        Calculate overall data completeness score (0-1).
        
        Checks how many key fields are populated.
        """
        checks = [
            # Company basics
            self.company_record.founded_year is not None,
            self.company_record.hq_city is not None,
            len(self.company_record.categories) > 0,
            self.company_record.description is not None,
            
            # Funding
            self.company_record.total_raised_usd is not None,
            len(self.funding_events) > 0,
            
            # Team
            len(self.leadership) > 0,
            len(self.founders) > 0,
            
            # Products
            len(self.products) > 0,
            
            # Metrics
            len(self.snapshots) > 0,
            len(self.visibility) > 0,
            
            # Snapshot details
            self.latest_snapshot is not None and self.latest_snapshot.headcount_total is not None,
            self.latest_snapshot is not None and self.latest_snapshot.job_openings_count is not None,
            
            # Visibility details
            self.latest_visibility is not None and self.latest_visibility.news_mentions_30d is not None,
            self.latest_visibility is not None and self.latest_visibility.glassdoor_rating is not None,
        ]
        
        return sum(checks) / len(checks)
    
    @property
    def quality_grade(self) -> str:
        """Get letter grade for data quality."""
        score = self.data_completeness_score
        if score >= 0.9:
            return "A"
        elif score >= 0.8:
            return "B"
        elif score >= 0.7:
            return "C"
        elif score >= 0.6:
            return "D"
        else:
            return "F"
    
    def to_llm_context(self) -> dict:
        """
        Convert payload to LLM-friendly context.
        
        Returns a simplified dict structure optimized for LLM consumption.
        """
        return {
            "company": {
                "name": self.company_record.display_name,
                "legal_name": self.company_record.legal_name,
                "website": str(self.company_record.website) if self.company_record.website else None,
                "location": self.company_record.location_string,
                "founded": self.company_record.founded_year,
                "description": self.company_record.description,
                "categories": [c.value for c in self.company_record.categories],
            },
            "funding": {
                "total_raised_usd": self.company_record.total_raised_usd,
                "last_round": self.company_record.last_round_name.value if self.company_record.last_round_name else None,
                "valuation_usd": self.company_record.last_disclosed_valuation_usd,
                "top_investors": self.company_record.top_investors,
                "recent_rounds": [
                    {
                        "date": e.occurred_on.isoformat(),
                        "round": e.round_name.value if e.round_name else None,
                        "amount_usd": e.amount_usd,
                        "investors": e.investors,
                    }
                    for e in sorted(self.funding_events, key=lambda x: x.occurred_on, reverse=True)[:3]
                ]
            },
            "team": {
                "size": self.latest_snapshot.headcount_total if self.latest_snapshot else None,
                "growth_pct": self.latest_snapshot.headcount_growth_pct if self.latest_snapshot else None,
                "openings": self.latest_snapshot.job_openings_count if self.latest_snapshot else None,
                "founders": [
                    {"name": f.name, "role": f.role}
                    for f in self.founders
                ],
                "executives": [
                    {"name": l.name, "role": l.role}
                    for l in self.current_leaders[:5]
                ]
            },
            "products": [
                {
                    "name": p.name,
                    "description": p.tagline or p.description,
                    "pricing_model": p.pricing_model.value if p.pricing_model else None,
                }
                for p in self.active_products
            ],
            "visibility": {
                "news_mentions_30d": self.latest_visibility.news_mentions_30d if self.latest_visibility else None,
                "sentiment": self.latest_visibility.avg_sentiment if self.latest_visibility else None,
                "glassdoor_rating": self.latest_visibility.glassdoor_rating if self.latest_visibility else None,
                "github_stars": self.latest_visibility.github_stars if self.latest_visibility else None,
            },
            "metadata": {
                "generated_at": self.generated_at.isoformat(),
                "data_quality": self.quality_grade,
                "completeness": f"{self.data_completeness_score:.1%}",
            }
        }
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z"
        }