"""
Visibility and market sentiment metrics.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date, datetime
from uuid import uuid4

from .provenance import Provenance


class VisibilityMetrics(BaseModel):
    """
    Tracks company visibility, media presence, and sentiment.
    """
    
    # Identity
    metrics_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique metrics snapshot ID"
    )
    
    company_id: str = Field(
        ...,
        description="Associated company ID"
    )
    
    as_of: date = Field(
        ...,
        description="Date these metrics were captured"
    )
    
    # News and media
    news_mentions_30d: Optional[int] = Field(
        None,
        ge=0,
        description="News mentions in last 30 days"
    )
    
    news_mentions_90d: Optional[int] = Field(
        None,
        ge=0,
        description="News mentions in last 90 days"
    )
    
    press_releases_30d: Optional[int] = Field(
        None,
        ge=0,
        description="Press releases in last 30 days"
    )
    
    top_news_sources: List[str] = Field(
        default_factory=list,
        description="Top publications covering the company"
    )
    
    # Sentiment analysis
    avg_sentiment: Optional[float] = Field(
        None,
        ge=-1.0,
        le=1.0,
        description="Average sentiment score (-1 negative to +1 positive)"
    )
    
    sentiment_distribution: Optional[dict] = Field(
        None,
        description="Distribution of sentiment (positive, neutral, negative counts)"
    )
    
    controversy_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=10.0,
        description="Controversy/risk score (0 low, 10 high)"
    )
    
    # Social media
    twitter_followers: Optional[int] = Field(
        None,
        ge=0,
        description="Twitter/X follower count"
    )
    
    twitter_engagement_rate: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Twitter engagement rate (%)"
    )
    
    linkedin_followers: Optional[int] = Field(
        None,
        ge=0,
        description="LinkedIn follower count"
    )
    
    # Developer community (if applicable)
    github_stars: Optional[int] = Field(
        None,
        ge=0,
        description="Total GitHub stars across repos"
    )
    
    github_forks: Optional[int] = Field(
        None,
        ge=0,
        description="Total GitHub forks"
    )
    
    github_contributors: Optional[int] = Field(
        None,
        ge=0,
        description="Total GitHub contributors"
    )
    
    stackoverflow_mentions: Optional[int] = Field(
        None,
        ge=0,
        description="Stack Overflow mentions"
    )
    
    npm_downloads_monthly: Optional[int] = Field(
        None,
        ge=0,
        description="Monthly npm downloads (for dev tools)"
    )
    
    pypi_downloads_monthly: Optional[int] = Field(
        None,
        ge=0,
        description="Monthly PyPI downloads (for Python tools)"
    )
    
    # Search and traffic
    google_search_volume: Optional[int] = Field(
        None,
        ge=0,
        description="Monthly Google search volume for company name"
    )
    
    website_traffic_rank: Optional[int] = Field(
        None,
        ge=1,
        description="Alexa/Similarweb traffic rank"
    )
    
    organic_keywords: Optional[int] = Field(
        None,
        ge=0,
        description="Number of organic keywords ranking"
    )
    
    # Employee sentiment
    glassdoor_rating: Optional[float] = Field(
        None,
        ge=0.0,
        le=5.0,
        description="Glassdoor overall rating (0-5 scale)"
    )
    
    glassdoor_review_count: Optional[int] = Field(
        None,
        ge=0,
        description="Number of Glassdoor reviews"
    )
    
    glassdoor_recommend_pct: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="% of employees who would recommend"
    )
    
    glassdoor_ceo_approval: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="CEO approval rating (%)"
    )
    
    # Industry recognition
    awards_30d: Optional[int] = Field(
        None,
        ge=0,
        description="Awards received in last 30 days"
    )
    
    conference_mentions: Optional[int] = Field(
        None,
        ge=0,
        description="Mentions at major conferences"
    )
    
    analyst_reports: Optional[int] = Field(
        None,
        ge=0,
        description="Number of analyst reports mentioning company"
    )
    
    # Trends
    visibility_trend: Optional[str] = Field(
        None,
        description="Overall trend (increasing, stable, decreasing)"
    )
    
    momentum_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=10.0,
        description="Market momentum score (0-10)"
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
    
    @field_validator("glassdoor_rating")
    @classmethod
    def round_rating(cls, v):
        """Round rating to 1 decimal place."""
        if v is not None:
            return round(v, 1)
        return v
    
    @property
    def sentiment_label(self) -> str:
        """Get human-readable sentiment label."""
        if self.avg_sentiment is None:
            return "unknown"
        elif self.avg_sentiment > 0.3:
            return "positive"
        elif self.avg_sentiment < -0.3:
            return "negative"
        else:
            return "neutral"
    
    @property
    def has_strong_dev_community(self) -> bool:
        """Check if company has strong developer community."""
        return (
            (self.github_stars and self.github_stars > 1000) or
            (self.npm_downloads_monthly and self.npm_downloads_monthly > 10000) or
            (self.pypi_downloads_monthly and self.pypi_downloads_monthly > 10000)
        )
    
    @property
    def employee_satisfaction_high(self) -> bool:
        """Check if employee satisfaction is high."""
        return (
            self.glassdoor_rating is not None and
            self.glassdoor_rating >= 4.0
        )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z",
            date: lambda v: v.isoformat()
        }