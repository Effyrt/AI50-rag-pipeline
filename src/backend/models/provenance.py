"""
Data provenance tracking for audit trails and quality scoring.
"""
from pydantic import BaseModel, HttpUrl, Field, field_validator
from datetime import datetime
from typing import Optional

from .enums import DataSourceType, ScrapingMethod, ConfidenceLevel


class Provenance(BaseModel):
    """
    Tracks the origin and quality of each piece of data.
    
    Every field in our data models should have provenance metadata.
    """
    
    source_url: str = Field(
        ...,
        description="URL where this data was sourced"
    )
    
    scraped_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when data was collected"
    )
    
    scraping_method: ScrapingMethod = Field(
        default=ScrapingMethod.HTTP_CLIENT,
        description="Method used to collect this data"
    )
    
    source_type: DataSourceType = Field(
        default=DataSourceType.OFFICIAL_WEBSITE,
        description="Type of data source"
    )
    
    confidence_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence in data accuracy (0.0 to 1.0)"
    )
    
    confidence_level: Optional[ConfidenceLevel] = Field(
        None,
        description="Human-readable confidence level"
    )
    
    last_verified: Optional[datetime] = Field(
        None,
        description="When this data was last verified"
    )
    
    snippet: Optional[str] = Field(
        None,
        max_length=50000,
        description="Text snippet showing where data came from"
    )
    
    @field_validator("snippet")
    @classmethod
    def truncate_snippet(cls, v):
        """Automatically truncate snippet to 500 chars."""
        if v and len(v) > 500:
            return v[:497] + "..."
        return v

    extractor_model: Optional[str] = Field(
        None,
        description="LLM model used for extraction (if applicable)"
    )
    
    extraction_prompt: Optional[str] = Field(
        None,
        description="Prompt used for LLM extraction (if applicable)"
    )
    
    validation_passed: bool = Field(
        default=True,
        description="Whether data passed validation checks"
    )
    
    validation_notes: Optional[str] = Field(
        None,
        description="Notes from validation process"
    )
    
    @field_validator("confidence_level", mode="before")
    @classmethod
    def set_confidence_level(cls, v, info):
        """Automatically set confidence level from score if not provided."""
        if v is not None:
            return v
        
        # Get confidence_score from validation context
        score = info.data.get("confidence_score", 1.0)
        
        if score >= 0.8:
            return ConfidenceLevel.HIGH
        elif score >= 0.5:
            return ConfidenceLevel.MEDIUM
        elif score >= 0.3:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z"
        }


class ProvenanceBundle(BaseModel):
    """
    Bundle of provenance records for a complex data structure.
    
    Useful when multiple sources contribute to a single entity.
    """
    
    primary_source: Provenance = Field(
        ...,
        description="Primary/most authoritative source"
    )
    
    secondary_sources: list[Provenance] = Field(
        default_factory=list,
        description="Additional corroborating sources"
    )
    
    conflicting_sources: list[Provenance] = Field(
        default_factory=list,
        description="Sources with conflicting information"
    )
    
    @property
    def aggregate_confidence(self) -> float:
        """Calculate aggregate confidence from all sources."""
        all_sources = [self.primary_source] + self.secondary_sources
        
        if not all_sources:
            return 0.0
        
        # Weighted average: primary source has 2x weight
        weights = [2.0] + [1.0] * len(self.secondary_sources)
        weighted_sum = sum(
            source.confidence_score * weight
            for source, weight in zip(all_sources, weights)
        )
        
        return weighted_sum / sum(weights)
    
    @property
    def source_count(self) -> int:
        """Total number of sources."""
        return 1 + len(self.secondary_sources) + len(self.conflicting_sources)