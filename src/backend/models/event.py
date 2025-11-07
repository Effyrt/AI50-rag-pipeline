"""
Event data model for tracking company milestones and news.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date, datetime
from uuid import UUID, uuid4

from .enums import EventType, FundingRoundType
from .provenance import Provenance


class Event(BaseModel):
    """
    Represents a significant company event or milestone.
    
    Events include funding rounds, product launches, partnerships,
    leadership changes, and other newsworthy occurrences.
    """
    
    # Identity
    event_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique event identifier"
    )
    
    company_id: str = Field(
        ...,
        description="Associated company ID"
    )
    
    # Event details
    occurred_on: date = Field(
        ...,
        description="Date the event occurred"
    )
    
    event_type: EventType = Field(
        ...,
        description="Type of event"
    )
    
    title: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description="Event title or headline"
    )
    
    description: Optional[str] = Field(
        None,
        max_length=2000,
        description="Detailed description of the event"
    )
    
    # Funding-specific fields
    round_name: Optional[FundingRoundType] = Field(
        None,
        description="Funding round type (if event_type is 'funding')"
    )
    
    investors: List[str] = Field(
        default_factory=list,
        description="Investors involved (for funding events)"
    )
    
    lead_investors: List[str] = Field(
        default_factory=list,
        description="Lead investors (for funding events)"
    )
    
    amount_usd: Optional[float] = Field(
        None,
        ge=0,
        description="Dollar amount (for funding, contract awards, etc.)"
    )
    
    valuation_usd: Optional[float] = Field(
        None,
        ge=0,
        description="Company valuation at time of event (if disclosed)"
    )
    
    valuation_type: Optional[str] = Field(
        None,
        description="Type of valuation (pre-money, post-money, etc.)"
    )
    
    # Partnership/integration fields
    partner_name: Optional[str] = Field(
        None,
        max_length=200,
        description="Partner company name (for partnerships, integrations)"
    )
    
    integration_platform: Optional[str] = Field(
        None,
        max_length=200,
        description="Platform integrated with"
    )
    
    # Product fields
    product_name: Optional[str] = Field(
        None,
        max_length=200,
        description="Product name (for product launches)"
    )
    
    # Leadership fields
    executive_name: Optional[str] = Field(
        None,
        max_length=200,
        description="Executive name (for leadership changes)"
    )
    
    executive_role: Optional[str] = Field(
        None,
        max_length=100,
        description="Executive role (CEO, CTO, etc.)"
    )
    
    change_type: Optional[str] = Field(
        None,
        description="Type of change (hire, departure, promotion)"
    )
    
    # Generic fields
    actors: List[str] = Field(
        default_factory=list,
        description="People or organizations involved"
    )
    
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for categorization and search"
    )
    
    impact_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=10.0,
        description="Estimated impact/importance (0-10 scale)"
    )
    
    sentiment: Optional[float] = Field(
        None,
        ge=-1.0,
        le=1.0,
        description="Sentiment score (-1 negative, 0 neutral, +1 positive)"
    )
    
    # External references
    source_urls: List[str] = Field(
        default_factory=list,
        description="URLs to news articles or press releases"
    )
    
    press_release_url: Optional[str] = Field(
        None,
        description="Official press release URL"
    )
    
    # Metadata
    schema_version: str = Field(
        default="2.1.0",
        description="Data schema version"
    )
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this record was created"
    )
    
    # Provenance
    provenance: List[Provenance] = Field(
        default_factory=list,
        description="Data source tracking"
    )
    
    @field_validator("amount_usd", "valuation_usd")
    @classmethod
    def round_currency(cls, v):
        """Round currency values to 2 decimal places."""
        if v is not None:
            return round(v, 2)
        return v
    
    @field_validator("tags")
    @classmethod
    def clean_tags(cls, v):
        """Convert tags to lowercase and remove duplicates."""
        if v:
            return list(set(tag.lower().strip() for tag in v))
        return v
    
    @property
    def is_funding(self) -> bool:
        """Check if this is a funding event."""
        return self.event_type == EventType.FUNDING
    
    @property
    def is_positive(self) -> bool:
        """Check if event has positive sentiment."""
        if self.sentiment is None:
            return None
        return self.sentiment > 0.0
    
    @property
    def is_high_impact(self) -> bool:
        """Check if event is high impact (score >= 7)."""
        if self.impact_score is None:
            return None
        return self.impact_score >= 7.0
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z",
            date: lambda v: v.isoformat()
        }
        
        json_schema_extra = {
            "examples": [
                {
                    "event_id": "650e8400-e29b-41d4-a716-446655440000",
                    "company_id": "550e8400-e29b-41d4-a716-446655440000",
                    "occurred_on": "2024-03-15",
                    "event_type": "funding",
                    "title": "Anthropic raises $750M Series C led by Menlo Ventures",
                    "round_name": "series_c",
                    "investors": ["Menlo Ventures", "Google", "Spark Capital"],
                    "lead_investors": ["Menlo Ventures"],
                    "amount_usd": 750000000.0,
                    "valuation_usd": 15000000000.0,
                    "impact_score": 9.0,
                    "sentiment": 1.0
                }
            ]
        }