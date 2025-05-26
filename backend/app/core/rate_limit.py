"""
Rate limiting configuration and middleware for LostMindAI API.

Provides configurable rate limiting per endpoint to prevent abuse
and ensure fair usage of resources.
"""

import time
from typing import Callable, Optional
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import Settings

# Initialize settings
settings = Settings()

# Custom key function that considers both IP and user session
def get_rate_limit_key(request: Request) -> str:
    """
    Generate rate limit key based on IP address and session.
    
    For authenticated requests, use user ID.
    For anonymous requests, use IP address.
    """
    # Try to get user from request state (set by auth middleware)
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    
    # Fall back to IP address
    return get_remote_address(request)

# Create limiter instance
limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=["200 per hour", "50 per minute"],
    headers_enabled=True,  # Include rate limit headers in responses
    storage_uri=settings.REDIS_URL if hasattr(settings, 'REDIS_URL') else None,
)

# Custom rate limit exceeded handler with more informative response
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Custom handler for rate limit exceeded errors.
    
    Returns detailed information about the rate limit and when to retry.
    """
    response = JSONResponse(
        content={
            "detail": "Rate limit exceeded",
            "message": str(exc),
            "retry_after": exc.retry_after if hasattr(exc, 'retry_after') else 60,
            "limit": request.state.view_rate_limit if hasattr(request.state, 'view_rate_limit') else None,
        },
        status_code=429,
    )
    
    # Add rate limit headers
    response.headers["Retry-After"] = str(exc.retry_after if hasattr(exc, 'retry_after') else 60)
    response.headers["X-RateLimit-Limit"] = str(request.state.view_rate_limit) if hasattr(request.state, 'view_rate_limit') else "N/A"
    response.headers["X-RateLimit-Remaining"] = "0"
    response.headers["X-RateLimit-Reset"] = str(int(time.time()) + (exc.retry_after if hasattr(exc, 'retry_after') else 60))
    
    return response

# Endpoint-specific rate limits
class RateLimits:
    """Define rate limits for different endpoint categories."""
    
    # Critical AI endpoints - more restrictive
    CHAT = "10 per minute"
    CHAT_STREAM = "5 per minute"
    RAG_QUERY = "20 per minute"
    
    # File operations - moderate limits
    FILE_UPLOAD = "30 per hour"
    FILE_DOWNLOAD = "100 per hour"
    
    # Knowledge base operations
    KNOWLEDGE_CREATE = "50 per hour"
    KNOWLEDGE_UPDATE = "100 per hour"
    KNOWLEDGE_SEARCH = "60 per minute"
    
    # General API endpoints
    DEFAULT = "100 per minute"
    HEALTH = "1000 per hour"
    
    # WebSocket connections
    WEBSOCKET_CONNECT = "10 per minute"
    WEBSOCKET_MESSAGE = "30 per minute"

# Middleware to add rate limit information to all responses
async def add_rate_limit_headers(request: Request, call_next: Callable) -> Response:
    """
    Middleware to add rate limit headers to all responses.
    """
    response = await call_next(request)
    
    # Add custom headers if rate limit info is available
    if hasattr(request.state, "view_rate_limit"):
        response.headers["X-RateLimit-Policy"] = request.state.view_rate_limit
    
    return response

# Utility function to apply dynamic rate limits
def dynamic_rate_limit(
    default_limit: str = RateLimits.DEFAULT,
    key_func: Optional[Callable] = None,
    per_method: bool = True,
    methods: Optional[list] = None,
) -> Callable:
    """
    Apply dynamic rate limits based on configuration.
    
    Args:
        default_limit: Default rate limit string
        key_func: Custom key function for rate limiting
        per_method: Apply different limits per HTTP method
        methods: Specific methods to apply limits to
    
    Returns:
        Rate limit decorator
    """
    def decorator(func: Callable) -> Callable:
        # Get rate limit from environment or use default
        env_limit = getattr(settings, f"RATE_LIMIT_{func.__name__.upper()}", None)
        limit = env_limit or default_limit
        
        # Apply the limit
        return limiter.limit(limit, key_func=key_func, per_method=per_method, methods=methods)(func)
    
    return decorator

# Rate limit configuration for production
PRODUCTION_RATE_LIMITS = {
    "enabled": True,
    "storage": "redis",  # Use Redis for distributed rate limiting
    "key_prefix": "lostmindai:ratelimit:",
    "global_limits": ["1000 per hour", "100 per minute"],
    "burst_allowance": 1.2,  # Allow 20% burst over limit
    "cleanup_interval": 3600,  # Clean up old entries every hour
}

# Development rate limits (more permissive)
DEVELOPMENT_RATE_LIMITS = {
    "enabled": False,  # Disabled in development
    "storage": "memory",
    "key_prefix": "dev:ratelimit:",
    "global_limits": ["10000 per hour", "1000 per minute"],
    "burst_allowance": 2.0,  # Allow 100% burst in dev
    "cleanup_interval": 300,
}