"""
Custom exception hierarchy for precise error handling.
"""
from typing import Optional, Dict, Any


class OrbitException(Exception):
    """Base exception for all Project ORBIT errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}


class ScrapingError(OrbitException):
    """Raised when web scraping fails."""
    pass


class RateLimitError(ScrapingError):
    """Raised when rate limit is exceeded."""
    pass


class ParsingError(OrbitException):
    """Raised when HTML/text parsing fails."""
    pass


class ExtractionError(OrbitException):
    """Raised when LLM extraction fails."""
    pass


class ValidationError(OrbitException):
    """Raised when data validation fails."""
    pass


class StorageError(OrbitException):
    """Raised when data storage operations fail."""
    pass


class VectorStoreError(OrbitException):
    """Raised when vector store operations fail."""
    pass


class PipelineError(OrbitException):
    """Raised when pipeline execution fails."""
    pass


class ConfigurationError(OrbitException):
    """Raised when configuration is invalid."""
    pass