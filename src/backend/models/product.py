"""
Product data model for tracking company offerings.
"""
from pydantic import BaseModel, Field, HttpUrl, field_validator
from typing import Optional, List
from datetime import date, datetime
from uuid import uuid4

from .enums import PricingModel
from .provenance import Provenance


class Product(BaseModel):
    """
    Represents a product or service offered by the company.
    """
    
    # Identity
    product_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique product identifier"
    )
    
    company_id: str = Field(
        ...,
        description="Associated company ID"
    )
    
    # Product details
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Product name"
    )
    
    tagline: Optional[str] = Field(
        None,
        max_length=300,
        description="Product tagline or one-liner"
    )
    
    description: Optional[str] = Field(
        None,
        max_length=2000,
        description="Detailed product description"
    )
    
    product_url: Optional[HttpUrl] = Field(
        None,
        description="Product-specific URL or landing page"
    )
    
    # Pricing
    pricing_model: Optional[PricingModel] = Field(
        None,
        description="Pricing model"
    )
    
    pricing_tiers_public: List[str] = Field(
        default_factory=list,
        description="Publicly available pricing tiers (e.g., 'Free', 'Pro', 'Enterprise')"
    )
    
    starting_price_usd: Optional[float] = Field(
        None,
        ge=0,
        description="Starting price (USD per month/year)"
    )
    
    pricing_unit: Optional[str] = Field(
        None,
        description="Pricing unit (per user, per API call, per month, etc.)"
    )
    
    free_tier_available: bool = Field(
        default=False,
        description="Whether a free tier is available"
    )
    
    enterprise_pricing: bool = Field(
        default=False,
        description="Whether enterprise pricing is available (contact sales)"
    )
    
    # Launch and lifecycle
    ga_date: Optional[date] = Field(
        None,
        description="General availability date"
    )
    
    beta_date: Optional[date] = Field(
        None,
        description="Beta launch date"
    )
    
    is_beta: bool = Field(
        default=False,
        description="Whether product is in beta"
    )
    
    is_deprecated: bool = Field(
        default=False,
        description="Whether product is deprecated"
    )
    
    sunset_date: Optional[date] = Field(
        None,
        description="Date product will be discontinued"
    )
    
    # Technical details
    api_available: bool = Field(
        default=False,
        description="Whether product has public API"
    )
    
    api_docs_url: Optional[HttpUrl] = Field(
        None,
        description="API documentation URL"
    )
    
    github_repo: Optional[str] = Field(
        None,
        description="GitHub repository (if open source)"
    )
    
    license_type: Optional[str] = Field(
        None,
        description="Software license (MIT, Apache, proprietary, etc.)"
    )
    
    supported_platforms: List[str] = Field(
        default_factory=list,
        description="Supported platforms (web, iOS, Android, API, etc.)"
    )
    
    programming_languages: List[str] = Field(
        default_factory=list,
        description="Programming languages supported (for dev tools)"
    )
    
    # Integrations
    integration_partners: List[str] = Field(
        default_factory=list,
        description="Companies/platforms this product integrates with"
    )
    
    marketplace_listings: List[str] = Field(
        default_factory=list,
        description="Marketplaces where product is listed (AWS, Azure, etc.)"
    )
    
    # Customers
    reference_customers: List[str] = Field(
        default_factory=list,
        description="Publicly announced customer logos"
    )
    
    customer_count: Optional[int] = Field(
        None,
        ge=0,
        description="Number of customers (if publicly disclosed)"
    )
    
    user_count: Optional[int] = Field(
        None,
        ge=0,
        description="Number of users (if publicly disclosed)"
    )
    
    # Features
    key_features: List[str] = Field(
        default_factory=list,
        description="Key product features"
    )
    
    use_cases: List[str] = Field(
        default_factory=list,
        description="Primary use cases"
    )
    
    target_audience: List[str] = Field(
        default_factory=list,
        description="Target customer segments (developers, enterprises, etc.)"
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
    
    @field_validator("starting_price_usd")
    @classmethod
    def round_price(cls, v):
        """Round price to 2 decimal places."""
        if v is not None:
            return round(v, 2)
        return v
    
    @property
    def is_open_source(self) -> bool:
        """Check if product is open source."""
        if self.license_type:
            open_source_licenses = ["mit", "apache", "gpl", "bsd", "mpl"]
            return any(lic in self.license_type.lower() for lic in open_source_licenses)
        return False
    
    @property
    def has_public_pricing(self) -> bool:
        """Check if product has publicly available pricing."""
        return len(self.pricing_tiers_public) > 0 or self.starting_price_usd is not None
    
    @property
    def age_days(self) -> Optional[int]:
        """Calculate product age in days since GA."""
        if self.ga_date:
            return (date.today() - self.ga_date).days
        return None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z",
            date: lambda v: v.isoformat()
        }