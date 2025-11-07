"""
LLM client with retry logic and error handling.
Supports: Anthropic, OpenAI, and Google Gemini (FREE).
"""
import logging
from typing import Optional, Dict, Any, Type, TypeVar
from pydantic import BaseModel

from anthropic import Anthropic
import instructor

from ..config.settings import settings
from ..core.exceptions import ExtractionError
from ..core.retry import retry_with_backoff
from ..core.telemetry import track_time

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """
    Unified LLM client supporting multiple providers.
    
    Providers:
    - anthropic: Claude (paid)
    - openai: GPT (paid)
    - gemini: Google Gemini (FREE - 1500 req/day)
    
    Uses instructor library for structured output extraction.
    """
    
    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize LLM client.
        
        Args:
            provider: LLM provider (anthropic, openai, gemini)
            model: Model identifier
            api_key: API key (defaults to settings)
        """
        self.provider = provider or settings.llm_provider
        self.model = model or settings.llm_model
        
        # ====================================================================
        # ANTHROPIC (Claude)
        # ====================================================================
        if self.provider == "anthropic":
            api_key = api_key or settings.anthropic_api_key
            if not api_key:
                raise ExtractionError(
                    "Anthropic API key not configured",
                    error_code="MISSING_API_KEY"
                )
            
            self.client = instructor.from_anthropic(
                Anthropic(api_key=api_key)
            )
            logger.info(f"Initialized Anthropic client: {self.model}")
        
        # ====================================================================
        # OPENAI (GPT)
        # ====================================================================
        elif self.provider == "openai":
            api_key = api_key or settings.openai_api_key
            if not api_key:
                raise ExtractionError(
                    "OpenAI API key not configured",
                    error_code="MISSING_API_KEY"
                )
            
            import openai
            self.client = instructor.from_openai(
                openai.OpenAI(api_key=api_key)
            )
            logger.info(f"Initialized OpenAI client: {self.model}")
        
        # ====================================================================
        # GEMINI (Google) - FREE TIER
        # ====================================================================
        elif self.provider == "gemini":
            api_key = api_key or getattr(settings, 'gemini_api_key', None)
            if not api_key:
                raise ExtractionError(
                    "Gemini API key not configured. Get free key: https://aistudio.google.com/app/apikey",
                    error_code="MISSING_API_KEY"
                )
            
            # Import Gemini client
            from .gemini_client import get_gemini_client
            self.client = get_gemini_client(api_key=api_key, model=self.model)
            logger.info(f"Initialized Gemini client: {self.model} (FREE tier)")
        
        # ====================================================================
        # INVALID PROVIDER
        # ====================================================================
        else:
            raise ExtractionError(
                f"Unsupported LLM provider: {self.provider}. "
                f"Supported: anthropic, openai, gemini",
                error_code="INVALID_PROVIDER"
            )
    
    @retry_with_backoff(max_attempts=3, exceptions=(Exception,))
    @track_time("llm_extraction")
    def extract(
        self,
        response_model: Type[T],
        messages: list[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> T:
        """
        Extract structured data using instructor or native client.
        
        Args:
            response_model: Pydantic model class to extract
            messages: Chat messages (system, user, assistant)
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens in response
            **kwargs: Additional provider-specific arguments
            
        Returns:
            Instance of response_model with extracted data
            
        Raises:
            ExtractionError: If extraction fails
        """
        try:
            logger.info(f"Extracting {response_model.__name__} using {self.provider}/{self.model}")
            
            # ================================================================
            # GEMINI uses its own extraction method
            # ================================================================
            if self.provider == "gemini":
                result = self.client.extract(
                    response_model=response_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
            
            # ================================================================
            # ANTHROPIC & OPENAI use instructor
            # ================================================================
            else:
                # Prepare request parameters
                request_params = {
                    "model": self.model,
                    "messages": messages,
                    "response_model": response_model,
                    "temperature": temperature or settings.llm_temperature,
                    "max_tokens": max_tokens or settings.llm_max_tokens,
                }
                
                # Add provider-specific parameters
                request_params.update(kwargs)
                
                # Call LLM with instructor
                result = self.client.chat.completions.create(**request_params)
            
            logger.info(f"Successfully extracted {response_model.__name__}")
            
            return result
        
        except Exception as e:
            logger.error(f"Extraction failed: {e}", exc_info=True)
            raise ExtractionError(
                f"Failed to extract {response_model.__name__}: {e}",
                error_code="EXTRACTION_FAILED",
                details={
                    "provider": self.provider,
                    "model": self.model,
                    "response_model": response_model.__name__,
                    "error": str(e)
                }
            )
    
    @retry_with_backoff(max_attempts=3)
    @track_time("llm_completion")
    def complete(
        self,
        messages: list[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Get text completion without structured extraction.
        
        Args:
            messages: Chat messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            **kwargs: Additional arguments
            
        Returns:
            Text response from LLM
        """
        try:
            logger.info(f"Getting completion from {self.provider}/{self.model}")
            
            # ================================================================
            # GEMINI
            # ================================================================
            if self.provider == "gemini":
                return self.client.complete(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
            
            # ================================================================
            # ANTHROPIC
            # ================================================================
            elif self.provider == "anthropic":
                from anthropic import Anthropic
                client = Anthropic(api_key=settings.anthropic_api_key)
                
                response = client.messages.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature or settings.llm_temperature,
                    max_tokens=max_tokens or settings.llm_max_tokens,
                    **kwargs
                )
                
                return response.content[0].text
            
            # ================================================================
            # OPENAI
            # ================================================================
            elif self.provider == "openai":
                import openai
                client = openai.OpenAI(api_key=settings.openai_api_key)
                
                response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature or settings.llm_temperature,
                    max_tokens=max_tokens or settings.llm_max_tokens,
                    **kwargs
                )
                
                return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"Completion failed: {e}", exc_info=True)
            raise ExtractionError(
                f"LLM completion failed: {e}",
                error_code="COMPLETION_FAILED",
                details={
                    "provider": self.provider,
                    "model": self.model,
                    "error": str(e)
                }
            )
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        
        Rough approximation: 1 token ≈ 4 characters.
        """
        return len(text) // 4


# Global LLM client instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create global LLM client instance."""
    global _llm_client
    
    if _llm_client is None:
        _llm_client = LLMClient()
    
    return _llm_client