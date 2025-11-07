"""
Point-in-time snapshot of company metrics.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict
from datetime import date, datetime
from uuid import uuid4

from .provenance import Provenance


class Snapshot(BaseModel):
    """
    Point-in-time snapshot of company headcount, hiring, and operational metrics.
    
    Used to track growth momentum over time.
    """
    
    # Identity
    snapshot_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique snapshot identifier"
    )
    
    company_id: str = Field(
        ...,
        description="Associated company ID"
    )
    
    as_of: date = Field(
        ...,
        description="Date this snapshot represents"
    )
    
    # Headcount metrics
    headcount_total: Optional[int] = Field(
        None,
        ge=0,
        description="Total employee count"
    )
    
    headcount_engineering: Optional[int] = Field(
        None,
        ge=0,
        description="Engineering headcount"
    )
    
    headcount_sales: Optional[int] = Field(
        None,
        ge=0,
        description="Sales/GTM headcount"
    )
    
    headcount_growth_pct: Optional[float] = Field(
        None,
        description="Headcount growth % since last snapshot"
    )
    
    headcount_growth_period: Optional[str] = Field(
        None,
        description="Period for growth calculation (e.g., '3m', '6m', '1y')"
    )
    
    # Job openings
    job_openings_count: Optional[int] = Field(
        None,
        ge=0,
        description="Total number of open job positions"
    )
    
    engineering_openings: Optional[int] = Field(
        None,
        ge=0,
        description="Open engineering positions"
    )
    
    sales_openings: Optional[int] = Field(
        None,
        ge=0,
        description="Open sales/GTM positions"
    )
    
    product_openings: Optional[int] = Field(
        None,
        ge=0,
        description="Open product management positions"
    )
    
    operations_openings: Optional[int] = Field(
        None,
        ge=0,
        description="Open operations positions"
    )
    
    hiring_focus: List[str] = Field(
        default_factory=list,
        description="Areas of hiring focus (e.g., 'ml', 'sales', 'security')"
    )
    
    # Product metrics
    active_products: List[str] = Field(
        default_factory=list,
        description="Names of active products in market"
    )
    
    pricing_tiers: List[str] = Field(
        default_factory=list,
        description="Available pricing tiers"
    )
    
    # Geographic presence
    geo_presence: List[str] = Field(
        default_factory=list,
        description="Countries or regions with presence"
    )
    
    office_count: Optional[int] = Field(
        None,
        ge=0,
        description="Number of physical offices"
    )
    
    # Technology metrics (if public)
    github_stars: Optional[int] = Field(
        None,
        ge=0,
        description="GitHub stars (if open source)"
    )
    
    github_contributors: Optional[int] = Field(
        None,
        ge=0,
        description="GitHub contributors"
    )
    
    github_activity_score: Optional[float] = Field(
        None,
        ge=0.0,
        description="GitHub activity score (custom metric)"
    )
    
    # Operational indicators
    remote_work_policy: Optional[str] = Field(
        None,
        description="Remote work policy (remote, hybrid, office)"
    )
    
    is_hiring: bool = Field(
        default=True,
        description="Whether company is actively hiring"
    )
    
    hiring_freeze: bool = Field(
        default=False,
        description="Whether company has hiring freeze"
    )
    
    recent_layoffs: bool = Field(
        default=False,
        description="Whether company had recent layoffs"
    )
    
    # Quality indicators
    confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Overall confidence in this snapshot's data"
    )
    
    data_completeness: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Percentage of fields populated"
    )
    
    # Metadata
    schema_version: str = Field(
        default="2.1.0",
        description="Data schema version"
    )
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this snapshot was created"
    )
    
    # Provenance
    provenance: List[Provenance] = Field(
        default_factory=list,
        description="Data source tracking"
    )
    
    @field_validator("hiring_focus")
    @classmethod
    def clean_hiring_focus(cls, v):
        """Convert to lowercase and remove duplicates."""
        if v:
            return list(set(focus.lower().strip() for focus in v))
        return v
    
    @property
    def engineering_to_sales_ratio(self) -> Optional[float]:
        """Calculate ratio of engineering to sales openings."""
        if self.engineering_openings and self.sales_openings:
            return self.engineering_openings / self.sales_openings
        return None
    
    @property
    def is_high_growth(self) -> bool:
        """Check if company is in high growth mode (>20% headcount growth)."""
        if self.headcount_growth_pct is None:
            return False
        return self.headcount_growth_pct > 20.0
    
    @property
    def hiring_velocity(self) -> Optional[float]:
        """Calculate hiring velocity (openings as % of headcount)."""
        if self.job_openings_count and self.headcount_total:
            return (self.job_openings_count / self.headcount_total) * 100
        return None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z",
            date: lambda v: v.isoformat()
        }