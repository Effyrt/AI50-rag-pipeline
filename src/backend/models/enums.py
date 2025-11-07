"""
Enumerations for type-safe categorical data.
"""
from enum import Enum


class IndustryCategory(str, Enum):
    """Industry categories for AI companies."""
    
    ENTERPRISE_SOFTWARE = "enterprise_software"
    DEVELOPER_TOOLS = "developer_tools"
    HEALTHCARE = "healthcare"
    FINTECH = "fintech"
    CYBERSECURITY = "cybersecurity"
    AUTONOMOUS_VEHICLES = "autonomous_vehicles"
    ROBOTICS = "robotics"
    INFRASTRUCTURE = "infrastructure"
    CONSUMER = "consumer"
    EDUCATION = "education"
    MANUFACTURING = "manufacturing"
    RETAIL = "retail"
    MARKETING = "marketing"
    HR_RECRUITING = "hr_recruiting"
    LEGAL = "legal"
    SUPPLY_CHAIN = "supply_chain"
    DRUG_DISCOVERY = "drug_discovery"
    CLIMATE_TECH = "climate_tech"
    OTHER = "other"


class FundingRoundType(str, Enum):
    """Funding round types."""
    
    SEED = "seed"
    SERIES_A = "series_a"
    SERIES_B = "series_b"
    SERIES_C = "series_c"
    SERIES_D = "series_d"
    SERIES_E = "series_e"
    SERIES_F_PLUS = "series_f_plus"
    BRIDGE = "bridge"
    CONVERTIBLE_NOTE = "convertible_note"
    DEBT_FINANCING = "debt_financing"
    GRANT = "grant"
    CORPORATE_ROUND = "corporate_round"
    ACQUISITION = "acquisition"
    IPO = "ipo"
    SECONDARY = "secondary"
    UNKNOWN = "unknown"


class EventType(str, Enum):
    """Types of company events."""
    
    FUNDING = "funding"
    MERGER_ACQUISITION = "mna"
    PRODUCT_RELEASE = "product_release"
    INTEGRATION = "integration"
    PARTNERSHIP = "partnership"
    CUSTOMER_WIN = "customer_win"
    LEADERSHIP_CHANGE = "leadership_change"
    REGULATORY = "regulatory"
    SECURITY_INCIDENT = "security_incident"
    PRICING_CHANGE = "pricing_change"
    LAYOFF = "layoff"
    HIRING_SPIKE = "hiring_spike"
    OFFICE_OPEN = "office_open"
    OFFICE_CLOSE = "office_close"
    BENCHMARK = "benchmark"
    OPEN_SOURCE_RELEASE = "open_source_release"
    CONTRACT_AWARD = "contract_award"
    CONFERENCE_PRESENTATION = "conference_presentation"
    MEDIA_COVERAGE = "media_coverage"
    OTHER = "other"


class PricingModel(str, Enum):
    """Product pricing models."""
    
    FREEMIUM = "freemium"
    SUBSCRIPTION = "subscription"
    USAGE_BASED = "usage_based"
    SEAT_BASED = "seat_based"
    TIERED = "tiered"
    ENTERPRISE_ONLY = "enterprise_only"
    ONE_TIME = "one_time"
    REVENUE_SHARE = "revenue_share"
    HYBRID = "hybrid"
    OPEN_SOURCE = "open_source"
    CONTACT_SALES = "contact_sales"
    UNKNOWN = "unknown"


class ConfidenceLevel(str, Enum):
    """Confidence levels for extracted data."""
    
    HIGH = "high"          # 0.8 - 1.0
    MEDIUM = "medium"      # 0.5 - 0.8
    LOW = "low"            # 0.3 - 0.5
    VERY_LOW = "very_low"  # 0.0 - 0.3


class DataSourceType(str, Enum):
    """Types of data sources."""
    
    OFFICIAL_WEBSITE = "official_website"
    CRUNCHBASE = "crunchbase"
    LINKEDIN = "linkedin"
    GITHUB = "github"
    NEWS_ARTICLE = "news_article"
    BLOG_POST = "blog_post"
    PRESS_RELEASE = "press_release"
    SEC_FILING = "sec_filing"
    COMPANY_API = "company_api"
    MANUAL_ENTRY = "manual_entry"
    LLM_INFERENCE = "llm_inference"


class ScrapingMethod(str, Enum):
    """Methods used for web scraping."""
    
    HTTP_CLIENT = "http_client"
    SELENIUM = "selenium"
    PLAYWRIGHT = "playwright"
    INSTRUCTOR_LLM = "instructor_llm"
    API = "api"
    MANUAL = "manual"