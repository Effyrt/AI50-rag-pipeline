"""
Leadership team data model.
"""
from pydantic import BaseModel, Field, HttpUrl, field_validator
from typing import Optional, List
from datetime import date, datetime
from uuid import uuid4

from .provenance import Provenance


class Leadership(BaseModel):
    """
    Represents a member of the company's leadership team.
    """
    
    # Identity
    person_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique person identifier"
    )
    
    company_id: str = Field(
        ...,
        description="Associated company ID"
    )
    
    # Personal details
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Full name"
    )
    
    role: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Current role/title (CEO, CTO, VP Engineering, etc.)"
    )
    
    is_founder: bool = Field(
        default=False,
        description="Whether this person is a company founder"
    )
    
    is_executive: bool = Field(
        default=True,
        description="Whether this is C-level/executive role"
    )
    
    # Tenure
    start_date: Optional[date] = Field(
        None,
        description="Date started in current role"
    )
    
    end_date: Optional[date] = Field(
        None,
        description="Date left role (if no longer with company)"
    )
    
    is_current: bool = Field(
        default=True,
        description="Whether currently in this role"
    )
    
    # Background
    previous_affiliation: Optional[str] = Field(
        None,
        max_length=300,
        description="Previous company or notable role"
    )
    
    previous_companies: List[str] = Field(
        default_factory=list,
        description="List of previous companies"
    )
    
    education: Optional[str] = Field(
        None,
        max_length=500,
        description="Educational background"
    )
    
    degrees: List[str] = Field(
        default_factory=list,
        description="Academic degrees (PhD, MBA, etc.)"
    )
    
    universities: List[str] = Field(
        default_factory=list,
        description="Universities attended"
    )
    
    # Expertise
    expertise_areas: List[str] = Field(
        default_factory=list,
        description="Areas of expertise (ML, sales, product, etc.)"
    )
    
    notable_achievements: List[str] = Field(
        default_factory=list,
        description="Notable achievements or recognition"
    )
    
    # Online presence
    linkedin_url: Optional[HttpUrl] = Field(
        None,
        description="LinkedIn profile URL"
    )
    
    twitter_handle: Optional[str] = Field(
        None,
        max_length=50,
        pattern=r"^@?[A-Za-z0-9_]{1,15}$",
        description="Twitter/X handle"
    )
    
    github_username: Optional[str] = Field(
        None,
        max_length=100,
        description="GitHub username"
    )
    
    personal_website: Optional[HttpUrl] = Field(
        None,
        description="Personal website or blog"
    )
    
    # Bio
    bio: Optional[str] = Field(
        None,
        max_length=2000,
        description="Professional biography"
    )
    
    quote: Optional[str] = Field(
        None,
        max_length=500,
        description="Notable quote or statement"
    )
    
    # Recognition
    awards: List[str] = Field(
        default_factory=list,
        description="Awards and recognition"
    )
    
    board_positions: List[str] = Field(
        default_factory=list,
        description="Board positions at other companies"
    )
    
    publications_count: Optional[int] = Field(
        None,
        ge=0,
        description="Number of academic publications"
    )
    
    patents_count: Optional[int] = Field(
        None,
        ge=0,
        description="Number of patents"
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
    
    @field_validator("twitter_handle")
    @classmethod
    def clean_twitter_handle(cls, v):
        """Remove @ prefix from Twitter handle."""
        if v and v.startswith("@"):
            return v[1:]
        return v
    
    @property
    def tenure_days(self) -> Optional[int]:
        """Calculate tenure in current role (days)."""
        if not self.start_date:
            return None
        
        end = self.end_date or date.today()
        return (end - self.start_date).days
    
    @property
    def tenure_years(self) -> Optional[float]:
        """Calculate tenure in current role (years)."""
        if days := self.tenure_days:
            return round(days / 365.25, 1)
        return None
    
    @property
    def is_technical_leader(self) -> bool:
        """Check if this is a technical leadership role."""
        technical_roles = ["cto", "vp engineering", "chief scientist", "head of ai"]
        return any(role in self.role.lower() for role in technical_roles)
    
    @property
    def is_founding_team(self) -> bool:
        """Check if person is on founding team."""
        return self.is_founder or (self.start_date and self.tenure_years and self.tenure_years > 3)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z",
            date: lambda v: v.isoformat()
        }
        
        json_schema_extra = {
            "examples": [
                {
                    "person_id": "750e8400-e29b-41d4-a716-446655440000",
                    "company_id": "550e8400-e29b-41d4-a716-446655440000",
                    "name": "Dario Amodei",
                    "role": "CEO",
                    "is_founder": True,
                    "start_date": "2021-01-01",
                    "previous_affiliation": "VP of Research at OpenAI",
                    "education": "PhD in Physics from Princeton University",
                    "expertise_areas": ["AI safety", "machine learning", "research"]
                }
            ]
        }