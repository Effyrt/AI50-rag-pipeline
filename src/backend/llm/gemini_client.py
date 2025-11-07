"""
Google Gemini client - production-grade with native JSON mode.
"""
import logging
import json
from typing import Optional, Type, TypeVar, Dict, Any, List
from pydantic import BaseModel
import google.generativeai as genai

from ..core.exceptions import ExtractionError
from ..core.retry import retry_with_backoff
from ..core.telemetry import track_time

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class GeminiClient:
    """
    Production-grade Gemini client with structured output.
    
    Free tier: 60 requests/minute, 1500 requests/day
    """
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        """Initialize Gemini client."""
        genai.configure(api_key=api_key)
        
        # Configure for JSON output
        self.generation_config = {
            "temperature": 0.0,
            "response_mime_type": "application/json",
        }
        
        self.model = genai.GenerativeModel(
            model_name=model,
            generation_config=self.generation_config
        )
        
        logger.info(f"Initialized Gemini client: {model} (FREE tier)")
    
    @retry_with_backoff(max_attempts=3)
    @track_time("gemini_extraction")
    def extract(
        self,
        response_model: Type[T],
        messages: list[Dict[str, str]],
        temperature: Optional[float] = None,
        **kwargs
    ) -> T:
        """
        Extract structured data using Gemini with JSON mode.
        
        Args:
            response_model: Pydantic model class
            messages: Chat messages
            temperature: Override temperature
            
        Returns:
            Instance of response_model
        """
        try:
            # Build prompt from messages
            prompt = self._format_messages(messages)
            
            # Add schema instruction
            schema = response_model.model_json_schema()
            prompt += f"\n\nYou must respond with valid JSON matching this exact schema:\n```json\n{json.dumps(schema, indent=2)}\n```"
            
            # Generate with JSON mode
            response = self.model.generate_content(prompt)
            
            # Parse JSON response
            json_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if json_text.startswith("```"):
                json_text = json_text.split("```")[1]
                if json_text.startswith("json"):
                    json_text = json_text[4:]
            
            # Parse and validate
            data = json.loads(json_text)
            result = response_model.model_validate(data)
            
            logger.info(f"Successfully extracted {response_model.__name__}")
            return result
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            logger.error(f"Response text: {response.text[:500]}")
            # Return empty instance on parse error
            return response_model()
        
        except Exception as e:
            logger.error(f"Gemini extraction failed: {e}", exc_info=True)
            raise ExtractionError(
                f"Failed to extract {response_model.__name__}: {e}",
                error_code="GEMINI_EXTRACTION_FAILED"
            )
    
    @retry_with_backoff(max_attempts=3)
    @track_time("gemini_completion")
    def complete(
        self,
        messages: list[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Get text completion from Gemini.
        
        Args:
            messages: Chat messages
            temperature: Override temperature
            max_tokens: Maximum output tokens
            
        Returns:
            Generated text
        """
        try:
            prompt = self._format_messages(messages)
            
            # Override config if needed
            config = self.generation_config.copy()
            if temperature is not None:
                config["temperature"] = temperature
            if max_tokens:
                config["max_output_tokens"] = max_tokens
            
            # Generate
            response = self.model.generate_content(prompt)
            
            logger.info("Successfully generated completion")
            return response.text
        
        except Exception as e:
            logger.error(f"Gemini completion failed: {e}", exc_info=True)
            raise ExtractionError(
                f"Gemini completion failed: {e}",
                error_code="GEMINI_COMPLETION_FAILED"
            )
    
    def _format_messages(self, messages: list[Dict[str, str]]) -> str:
        """Format chat messages into single prompt."""
        formatted = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                formatted.append(f"Instructions: {content}")
            elif role == "user":
                formatted.append(f"User: {content}")
            elif role == "assistant":
                formatted.append(f"Assistant: {content}")
        
        return "\n\n".join(formatted)
    
    def estimate_tokens(self, text: str) -> int:
        """Rough token estimate (4 chars ≈ 1 token)."""
        return len(text) // 4


# Global Gemini client
_gemini_client: Optional[GeminiClient] = None


def get_gemini_client(api_key: str, model: str = "gemini-1.5-flash") -> GeminiClient:
    """Get or create Gemini client instance."""
    global _gemini_client
    
    if _gemini_client is None:
        _gemini_client = GeminiClient(api_key=api_key, model=model)
    
    return _gemini_client