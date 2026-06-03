"""
Rate limiter for NCBI API requests.

NCBI rate limits:
- Without API key: 3 requests/second
- With API key: 10 requests/second

This module provides:
- Token bucket rate limiting
- Exponential backoff retry logic
- Request timing and statistics
"""

import asyncio
import logging
import time
from typing import Optional, Callable, Any
from functools import wraps

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter for NCBI API.
    
    Ensures we don't exceed NCBI rate limits and handles 429 responses.
    """
    
    def __init__(self, requests_per_second: float = 3.0):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_second: Maximum requests per second (default 3 for no API key)
        """
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0.0
        self.lock = asyncio.Lock()
        
        logger.info(f"⏱️  Rate limiter initialized: {requests_per_second} req/s (min interval: {self.min_interval:.3f}s)")
    
    async def acquire(self) -> None:
        """
        Acquire permission to make a request.
        
        Blocks until enough time has passed since the last request.
        """
        async with self.lock:
            now = time.time()
            time_since_last = now - self.last_request_time
            
            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                logger.debug(f"⏳ Rate limit: sleeping {sleep_time:.3f}s")
                await asyncio.sleep(sleep_time)
            
            self.last_request_time = time.time()
    
    def acquire_sync(self) -> None:
        """
        Synchronous version of acquire() for blocking code.
        """
        now = time.time()
        time_since_last = now - self.last_request_time
        
        if time_since_last < self.min_interval:
            sleep_time = self.min_interval - time_since_last
            logger.debug(f"⏳ Rate limit: sleeping {sleep_time:.3f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()


class RetryConfig:
    """Configuration for retry logic with exponential backoff."""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        """
        Initialize retry configuration.
        
        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff (delay *= base^attempt)
            jitter: Add random jitter to prevent thundering herd
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given attempt number.
        
        Args:
            attempt: Retry attempt number (0-indexed)
        
        Returns:
            Delay in seconds
        """
        delay = self.initial_delay * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            import random
            delay *= (0.5 + random.random())  # Add 0-50% jitter
        
        return delay


async def retry_with_backoff(
    func: Callable,
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs
) -> Any:
    """
    Execute a function with exponential backoff retry.
    
    Args:
        func: Function to execute (can be sync or async)
        *args: Positional arguments for func
        config: Retry configuration (uses defaults if None)
        **kwargs: Keyword arguments for func
    
    Returns:
        Result of func
    
    Raises:
        Last exception if all retries fail
    """
    if config is None:
        config = RetryConfig()
    
    last_exception = None
    
    for attempt in range(config.max_retries + 1):
        try:
            # Execute function (handle both sync and async)
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            if attempt > 0:
                logger.info(f"✅ Retry succeeded on attempt {attempt + 1}")
            
            return result
        
        except Exception as e:
            last_exception = e
            
            # Check if we should retry
            if attempt >= config.max_retries:
                logger.error(f"❌ All {config.max_retries} retries failed: {e}")
                raise
            
            # Calculate delay
            delay = config.get_delay(attempt)
            
            # Log retry
            logger.warning(f"⚠️  Attempt {attempt + 1} failed: {e}. Retrying in {delay:.1f}s...")
            
            # Wait before retry
            await asyncio.sleep(delay)
    
    # Should never reach here, but just in case
    if last_exception:
        raise last_exception


def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator for automatic retry with exponential backoff.
    
    Usage:
        @with_retry(RetryConfig(max_retries=5))
        async def fetch_data():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_with_backoff(func, *args, config=config, **kwargs)
        return wrapper
    return decorator


# Global rate limiter instance (can be configured based on API key presence)
_global_limiter: Optional[RateLimiter] = None


def get_rate_limiter(has_api_key: bool = False) -> RateLimiter:
    """
    Get or create global rate limiter.
    
    Args:
        has_api_key: Whether NCBI API key is available
    
    Returns:
        RateLimiter instance
    """
    global _global_limiter
    
    if _global_limiter is None:
        # With API key: 10 req/s allowed, use 9.5 to be safe
        # Without API key: 3 req/s allowed, use 2.8 to be safe
        requests_per_second = 9.5 if has_api_key else 2.8
        _global_limiter = RateLimiter(requests_per_second)
    
    return _global_limiter


def reset_rate_limiter():
    """Reset global rate limiter (useful for tests)."""
    global _global_limiter
    _global_limiter = None
