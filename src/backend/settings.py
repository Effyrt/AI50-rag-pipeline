"""
Application settings with environment variable support.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # ========================================================================
    # LLM Configuration
    # ========================================================================
    
    # API Keys
    anthropic_api_key: Optional[str] = Field(None, alias="ANTHROPIC_API_KEY")
    openai_api_key: Optional[str] = Field(None, alias="OPENAI_API_KEY")
    gemini_api_key: Optional[str] = Field(None, alias="GEMINI_API_KEY")
    
    # LLM Settings
    llm_provider: str = Field("gemini", description="LLM provider: anthropic, openai, gemini")
    llm_model: str = Field("gemini-1.5-flash-latest", description="Model identifier")
    llm_temperature: float = Field(0.0, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(4096, ge=1, le=200000)
    llm_timeout: int = Field(120, description="Timeout in seconds")
    
    # ========================================================================
    # Embedding Configuration
    # ========================================================================
    
    embedding_model: str = Field("all-MiniLM-L6-v2", description="Sentence transformer model")
    chunk_size: int = Field(1000, ge=100, le=5000)
    chunk_overlap: int = Field(200, ge=0, le=1000)
    
    # ========================================================================
    # Scraping Configuration
    # ========================================================================
    
    scraper_user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
    scraper_timeout: int = Field(30, description="HTTP timeout in seconds")
    scraper_max_retries: int = Field(3, ge=1, le=10)
    scraper_backoff_factor: float = Field(2.0, ge=1.0)
    scraper_rate_limit: int = Field(5, description="Requests per second")
    scraper_concurrent_limit: int = Field(10, description="Max concurrent requests")
    
    # ========================================================================
    # Storage Configuration
    # ========================================================================
    
    data_dir: Path = Field(Path("data"), description="Root data directory")
    
    # ========================================================================
    # Vector Store Configuration
    # ========================================================================
    
    vector_store_type: str = Field("faiss", description="faiss, chroma, or qdrant")
    
    # ========================================================================
    # API Configuration
    # ========================================================================
    
    api_host: str = Field("0.0.0.0")
    api_port: int = Field(8000, ge=1024, le=65535)
    api_workers: int = Field(4, ge=1)
    api_reload: bool = Field(False, description="Auto-reload on code changes")
    
    # ========================================================================
    # Logging Configuration
    # ========================================================================
    
    log_level: str = Field("INFO", description="DEBUG, INFO, WARNING, ERROR, CRITICAL")
    log_format: str = Field("text", description="json or text")
    
    # ========================================================================
    # Feature Flags
    # ========================================================================
    
    enable_selenium: bool = Field(False, description="Use Selenium for JS-heavy sites")
    enable_caching: bool = Field(True, description="Cache HTTP responses")
    enable_telemetry: bool = Field(True, description="OpenTelemetry tracing")
    
    # ========================================================================
    # Directory Properties
    # ========================================================================
    
    @property
    def raw_data_dir(self) -> Path:
        """Directory for raw scraped HTML/text."""
        path = self.data_dir / "raw"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def structured_data_dir(self) -> Path:
        """Directory for structured Pydantic models."""
        path = self.data_dir / "structured"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def payload_dir(self) -> Path:
        """Directory for assembled payloads."""
        path = self.data_dir / "payloads"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def vector_store_dir(self) -> Path:
        """Directory for vector store indices."""
        path = self.data_dir / "vector_store"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def reports_dir(self) -> Path:
        """Directory for generated reports."""
        path = self.data_dir / "reports"
        path.mkdir(parents=True, exist_ok=True)
        return path


# Global settings instance
settings = Settings()