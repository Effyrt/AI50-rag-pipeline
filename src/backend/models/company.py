"""
Company profile data model with comprehensive validation.
"""
from pydantic import BaseModel, HttpUrl, Field, field_validator
from typing import Optional, List
from datetime import date, datetime
from uuid import UUID, uuid4

from .enums import IndustryCategory, FundingRoundType
from .provenance import Provenance


class Company(BaseModel):
    """
    Core company profile with funding, location, and business details.
    """
    
    # Identity
    company_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier (UUID)"
    )
    
    legal_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Official legal entity name"
    )
    
    brand_name: Optional[str] = Field(
        None,
        max_length=200,
        description="Public-facing brand name (if different)"
    )
    
    # Online presence
    website: Optional[HttpUrl] = Field(
        None,
        description="Primary company website"
    )
    
    linkedin_url: Optional[HttpUrl] = Field(
        None,
        description="LinkedIn company page"
    )
    
    twitter_handle: Optional[str] = Field(
        None,
        max_length=50,
        pattern=r"^@?[A-Za-z0-9_]{1,15}$",
        description="Twitter/X handle"
    )
    
    github_org: Optional[str] = Field(
        None,
        max_length=100,
        description="GitHub organization name"
    )
    
    # Location
    hq_city: Optional[str] = Field(
        None,
        max_length=100,
        description="Headquarters city"
    )
    
    hq_state: Optional[str] = Field(
        None,
        max_length=100,
        description="Headquarters state/province"
    )
    
    hq_country: Optional[str] = Field(
        None,
        max_length=100,
        description="Headquarters country"
    )
    
    office_locations: List[str] = Field(
        default_factory=list,
        description="Other office locations"
    )
    
    # Business details
    founded_year: Optional[int] = Field(
        None,
        ge=1900,
        le=2030,
        description="Year company was founded"
    )
    
    categories: List[IndustryCategory] = Field(
        default_factory=list,
        description="Industry categories"
    )
    
    primary_category: Optional[IndustryCategory] = Field(
        None,
        description="Primary industry focus"
    )
    
    description: Optional[str] = Field(
        None,
        max_length=2000,
        description="Company description"
    )
    
    elevator_pitch: Optional[str] = Field(
        None,
        max_length=500,
        description="One-sentence value proposition"
    )
    
    # Competitive landscape
    related_companies: List[str] = Field(
        default_factory=list,
        max_length=20,
        description="Competitors or similar companies"
    )
    
    differentiation: Optional[str] = Field(
        None,
        max_length=1000,
        description="Key differentiators vs competitors"
    )
    
    # Funding summary
    total_raised_usd: Optional[float] = Field(
        None,
        ge=0,
        description="Total funding raised (USD)"
    )
    
    last_round_name: Optional[FundingRoundType] = Field(
        None,
        description="Most recent funding round"
    )
    
    last_round_date: Optional[date] = Field(
        None,
        description="Date of most recent funding"
    )
    
    last_round_amount_usd: Optional[float] = Field(
        None,
        ge=0,
        description="Amount raised in most recent round (USD)"
    )
    
    last_disclosed_valuation_usd: Optional[float] = Field(
        None,
        ge=0,
        description="Most recent disclosed valuation (USD)"
    )
    
    valuation_date: Optional[date] = Field(
        None,
        description="Date of most recent valuation"
    )
    
    top_investors: List[str] = Field(
        default_factory=list,
        max_length=15,
        description="Notable investors"
    )
    
    # Business metrics (if publicly disclosed)
    annual_revenue_usd: Optional[float] = Field(
        None,
        ge=0,
        description="Annual revenue (USD) - only if publicly disclosed"
    )
    
    arr_usd: Optional[float] = Field(
        None,
        ge=0,
        description="Annual Recurring Revenue (USD) - only if publicly disclosed"
    )
    
    revenue_growth_yoy: Optional[float] = Field(
        None,
        description="Year-over-year revenue growth (percentage)"
    )
    
    profitability_status: Optional[str] = Field(
        None,
        description="Profitability status (profitable, break-even, loss-making)"
    )
    
    # Customer base (if publicly disclosed)
    customer_count: Optional[int] = Field(
        None,
        ge=0,
        description="Number of customers - only if publicly disclosed"
    )
    
    enterprise_customer_count: Optional[int] = Field(
        None,
        ge=0,
        description="Number of enterprise customers - only if publicly disclosed"
    )
    
    notable_customers: List[str] = Field(
        default_factory=list,
        max_length=20,
        description="Publicly announced customer logos"
    )
    
    # Metadata
    schema_version: str = Field(
        default="2.1.0",
        description="Data schema version"
    )
    
    as_of: Optional[date] = Field(
        default_factory=date.today,
        description="Date this record represents"
    )
    
    last_updated: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        description="When this record was last updated"
    )
    
    forbes_ai50_rank: Optional[int] = Field(
        None,
        ge=1,
        le=50,
        description="Rank on Forbes AI 50 list (if applicable)"
    )
    
    forbes_ai50_year: Optional[int] = Field(
        None,
        ge=2019,
        le=2030,
        description="Year of Forbes AI 50 appearance"
    )
    
    # Provenance
    provenance: List[Provenance] = Field(
        default_factory=list,
        description="Data source tracking"
    )
    
    @field_validator("twitter_handle")
    @classmethod
    def clean_twitter_handle(cls, v):
        """Remove @ prefix from Twitter handle if present."""
        if v and v.startswith("@"):
            return v[1:]
        return v
    
    @field_validator("total_raised_usd", "last_round_amount_usd", "last_disclosed_valuation_usd")
    @classmethod
    def round_currency(cls, v):
        """Round currency values to 2 decimal places."""
        if v is not None:
            return round(v, 2)
        return v
    
    @field_validator("company_id", mode="before")
    @classmethod  
    def ensure_company_id(cls, v):
        """Auto-generate company_id if None."""
        if v is None or v == "None" or not v:
            from uuid import uuid4
            return str(uuid4())
        return v
    
    @property
    def display_name(self) -> str:
        """Get display name (brand name if available, else legal name)."""
        return self.brand_name or self.legal_name
    
    @property
    def location_string(self) -> str:
        """Get formatted location string."""
        parts = [self.hq_city, self.hq_state, self.hq_country]
        return ", ".join(p for p in parts if p)
    
    @property
    def age_years(self) -> Optional[int]:
        """Calculate company age in years."""
        if self.founded_year:
            return datetime.now().year - self.founded_year
        return None
    
    @property
    def has_valuation(self) -> bool:
        """Check if company has disclosed valuation."""
        return self.last_disclosed_valuation_usd is not None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z",
            date: lambda v: v.isoformat()
        }
        
        json_schema_extra = {
            "examples": [
                {
                    "company_id": "550e8400-e29b-41d4-a716-446655440000",
                    "legal_name": "Anthropic PBC",
                    "brand_name": "Anthropic",
                    "website": "https://anthropic.com",
                    "hq_city": "San Francisco",
                    "hq_state": "California",
                    "hq_country": "United States",
                    "founded_year": 2021,
                    "categories": ["enterprise_software", "infrastructure"],
                    "description": "AI safety and research company building reliable, interpretable, and steerable AI systems.",
                    "total_raised_usd": 7300000000.0,
                    "last_round_name": "series_c",
                    "top_investors": ["Google", "Spark Capital", "Salesforce Ventures"]
                }
            ]
        }