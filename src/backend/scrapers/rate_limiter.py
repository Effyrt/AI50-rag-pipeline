"""
Token bucket rate limiter for respecting website rate limits.
"""
import time
import threading
from typing import Optional


class TokenBucket:
    """
    Token bucket algorithm for rate limiting.
    
    Allows bursts up to capacity, then enforces steady rate.
    Thread-safe implementation.
    """
    
    def __init__(self, rate: float, capacity: Optional[int] = None):
        """
        Initialize token bucket.
        
        Args:
            rate: Tokens per second
            capacity: Maximum burst size (defaults to rate)
        """
        self.rate = rate
        self.capacity = capacity or int(rate)
        self.tokens = float(self.capacity)
        self.last_update = time.time()
        self.lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        with self.lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def wait_for_token(self, tokens: int = 1) -> None:
        """
        Block until tokens are available.
        
        Args:
            tokens: Number of tokens needed
        """
        while not self.consume(tokens):
            time.sleep(0.01)  # Sleep 10ms
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_update
        
        # Add tokens based on rate
        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.rate
        )
        self.last_update = now
    
    @property
    def available_tokens(self) -> int:
        """Get current number of available tokens."""
        with self.lock:
            self._refill()
            return int(self.tokens)


class RateLimiter:
    """
    Multi-domain rate limiter with per-domain token buckets.
    """
    
    def __init__(self, default_rate: float = 5.0):
        """
        Initialize rate limiter.
        
        Args:
            default_rate: Default requests per second per domain
        """
        self.default_rate = default_rate
        self.buckets: dict[str, TokenBucket] = {}
        self.lock = threading.Lock()
    
    def acquire(self, domain: str, tokens: int = 1) -> None:
        """
        Acquire rate limit token for domain (blocking).
        
        Args:
            domain: Domain name (e.g., 'example.com')
            tokens: Number of tokens to acquire
        """
        bucket = self._get_bucket(domain)
        bucket.wait_for_token(tokens)
    
    def try_acquire(self, domain: str, tokens: int = 1) -> bool:
        """
        Try to acquire token without blocking.
        
        Args:
            domain: Domain name
            tokens: Number of tokens to acquire
            
        Returns:
            True if acquired, False otherwise
        """
        bucket = self._get_bucket(domain)
        return bucket.consume(tokens)
    
    def _get_bucket(self, domain: str) -> TokenBucket:
        """Get or create token bucket for domain."""
        with self.lock:
            if domain not in self.buckets:
                self.buckets[domain] = TokenBucket(self.default_rate)
            return self.buckets[domain]
    
    def set_rate(self, domain: str, rate: float) -> None:
        """
        Set custom rate limit for specific domain.
        
        Args:
            domain: Domain name
            rate: Requests per second
        """
        with self.lock:
            self.buckets[domain] = TokenBucket(rate)