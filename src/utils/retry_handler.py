"""
Retry handler for API requests with exponential backoff.

Provides retry logic for handling rate limits and transient failures
when communicating with the backend API.
"""

import asyncio
import logging
import random
import time
from typing import Any, Callable, Dict, Optional, Union
from datetime import datetime, timedelta

import aiohttp

logger = logging.getLogger(__name__)


class RateLimitInfo:
    """Track rate limit information for an endpoint."""
    
    def __init__(self):
        self.limit: int = 0
        self.remaining: int = 0
        self.reset: Optional[datetime] = None
    
    def update_from_headers(self, headers: Dict[str, str]) -> None:
        """Update rate limit info from response headers."""
        try:
            if 'X-RateLimit-Limit' in headers:
                self.limit = int(headers['X-RateLimit-Limit'])
            if 'X-RateLimit-Remaining' in headers:
                self.remaining = int(headers['X-RateLimit-Remaining'])
            if 'X-RateLimit-Reset' in headers:
                reset_timestamp = int(headers['X-RateLimit-Reset'])
                self.reset = datetime.fromtimestamp(reset_timestamp)
        except (ValueError, KeyError) as e:
            logger.warning(f"Failed to parse rate limit headers: {e}")
    
    def should_throttle(self) -> bool:
        """Check if we should throttle requests."""
        if self.limit == 0:
            return False
        # Throttle if we're at 20% or less of our limit
        return self.remaining <= self.limit * 0.2
    
    def get_throttle_delay(self) -> float:
        """Get delay in seconds until rate limit resets."""
        if not self.reset or self.remaining > 0:
            return 0.0
        
        now = datetime.now()
        if self.reset > now:
            return (self.reset - now).total_seconds() + 1.0  # Add 1s buffer
        return 0.0


class RateLimitTracker:
    """Track rate limits for multiple endpoints."""
    
    def __init__(self):
        self._limits: Dict[str, RateLimitInfo] = {}
    
    def update_from_response(self, endpoint: str, response: aiohttp.ClientResponse) -> None:
        """Update rate limit info from response."""
        if endpoint not in self._limits:
            self._limits[endpoint] = RateLimitInfo()
        
        self._limits[endpoint].update_from_headers(dict(response.headers))
    
    def should_throttle(self, endpoint: str) -> bool:
        """Check if endpoint should be throttled."""
        if endpoint not in self._limits:
            return False
        return self._limits[endpoint].should_throttle()
    
    def get_throttle_delay(self, endpoint: str) -> float:
        """Get throttle delay for endpoint."""
        if endpoint not in self._limits:
            return 0.0
        return self._limits[endpoint].get_throttle_delay()


# Global rate limit tracker
rate_limit_tracker = RateLimitTracker()


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


def calculate_backoff_delay(
    attempt: int,
    config: RetryConfig
) -> float:
    """Calculate exponential backoff delay with optional jitter."""
    # Exponential backoff: delay = initial * (base ^ attempt)
    delay = config.initial_delay * (config.exponential_base ** (attempt - 1))
    delay = min(delay, config.max_delay)
    
    if config.jitter:
        # Add random jitter (±25% of delay)
        jitter_range = delay * 0.25
        jitter = random.uniform(-jitter_range, jitter_range)
        delay = max(0, delay + jitter)
    
    return delay


def get_retry_after_delay(response: aiohttp.ClientResponse) -> Optional[float]:
    """Extract retry delay from Retry-After header."""
    retry_after = response.headers.get('Retry-After')
    if not retry_after:
        return None
    
    try:
        # Try parsing as seconds
        seconds = int(retry_after)
        return float(seconds)
    except ValueError:
        pass
    
    try:
        # Try parsing as HTTP date
        retry_date = datetime.strptime(retry_after, '%a, %d %b %Y %H:%M:%S GMT')
        delay = (retry_date - datetime.utcnow()).total_seconds()
        return max(0, delay)
    except ValueError:
        logger.warning(f"Unable to parse Retry-After header: {retry_after}")
        return None


def should_retry(
    response: Optional[aiohttp.ClientResponse],
    error: Optional[Exception]
) -> bool:
    """Determine if request should be retried."""
    if error and not response:
        # Network errors - retry
        return isinstance(error, (
            aiohttp.ClientError,
            asyncio.TimeoutError,
            ConnectionError
        ))
    
    if response:
        # Retry on rate limit or server errors
        return response.status == 429 or (500 <= response.status < 600)
    
    return False


async def retry_with_backoff(
    func: Callable[..., Any],
    *args,
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
    **kwargs
) -> Any:
    """
    Execute function with retry logic and exponential backoff.
    
    Args:
        func: Async function to retry
        *args: Positional arguments for func
        config: Retry configuration
        on_retry: Callback for retry events
        **kwargs: Keyword arguments for func
    
    Returns:
        Result from successful function call
    
    Raises:
        Last exception if all retries fail
    """
    if config is None:
        config = RetryConfig()
    
    last_error: Optional[Exception] = None
    
    for attempt in range(1, config.max_attempts + 1):
        try:
            result = await func(*args, **kwargs)
            
            # If result is an aiohttp response, check if we should retry
            if isinstance(result, aiohttp.ClientResponse):
                if should_retry(result, None):
                    # This is a retryable response
                    if attempt == config.max_attempts:
                        # Last attempt, return the error response
                        return result
                    
                    # Calculate delay
                    delay = get_retry_after_delay(result)
                    if delay is None:
                        delay = calculate_backoff_delay(attempt, config)
                    
                    # Log retry
                    logger.info(
                        f"Retrying after {result.status} response "
                        f"(attempt {attempt}/{config.max_attempts}) "
                        f"in {delay:.1f}s"
                    )
                    
                    if on_retry:
                        on_retry(attempt, Exception(f"HTTP {result.status}"))
                    
                    await asyncio.sleep(delay)
                    continue
            
            return result
            
        except Exception as e:
            last_error = e
            
            # Check if we should retry this error
            if not should_retry(None, e):
                raise
            
            if attempt == config.max_attempts:
                # Last attempt, re-raise
                raise
            
            # Calculate delay
            delay = calculate_backoff_delay(attempt, config)
            
            # Log retry
            logger.info(
                f"Retrying after {type(e).__name__} "
                f"(attempt {attempt}/{config.max_attempts}) "
                f"in {delay:.1f}s: {str(e)}"
            )
            
            if on_retry:
                on_retry(attempt, e)
            
            await asyncio.sleep(delay)
    
    # Should never reach here, but just in case
    if last_error:
        raise last_error
    raise RuntimeError("Retry logic error")


class RetryableSession:
    """Wrapper for aiohttp session with automatic retry logic."""
    
    def __init__(
        self,
        session: aiohttp.ClientSession,
        config: Optional[RetryConfig] = None
    ):
        self.session = session
        self.config = config or RetryConfig()
    
    async def request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """Make HTTP request with retry logic."""
        endpoint = url.split('?')[0]  # Remove query params for tracking
        
        # Check if we should throttle
        throttle_delay = rate_limit_tracker.get_throttle_delay(endpoint)
        if throttle_delay > 0:
            logger.info(f"Throttling request to {endpoint} for {throttle_delay:.1f}s")
            await asyncio.sleep(throttle_delay)
        
        async def _make_request():
            async with self.session.request(method, url, **kwargs) as response:
                # Update rate limit tracking
                rate_limit_tracker.update_from_response(endpoint, response)
                
                # Read response body to prevent connection issues
                await response.read()
                return response
        
        return await retry_with_backoff(
            _make_request,
            config=self.config,
            on_retry=lambda attempt, error: logger.warning(
                f"Retry attempt {attempt} for {method} {url}: {error}"
            )
        )
    
    # Convenience methods
    async def get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        return await self.request('GET', url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        return await self.request('POST', url, **kwargs)
    
    async def put(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        return await self.request('PUT', url, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        return await self.request('DELETE', url, **kwargs)
    
    async def patch(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        return await self.request('PATCH', url, **kwargs)