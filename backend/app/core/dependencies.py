"""
Dependency injection for FastAPI application.
Manages service instances and their lifecycle.
"""

from functools import lru_cache
from typing import Annotated, Dict, Any

from fastapi import Depends, HTTPException, Header

from app.core.config import Settings
from app.services.gemini_service import GeminiService


@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached singleton)."""
    return Settings()


# Global service instances
_gemini_service = None


def get_gemini_service(
    settings: Annotated[Settings, Depends(get_settings)]
) -> GeminiService:
    """Get GeminiService instance (singleton)."""
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiService(settings)
    return _gemini_service


# For manual service initialization during app startup
async def initialize_services(settings: Settings):
    """Initialize all services during application startup."""
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiService(settings)
        # Add basic initialization if needed
        

async def cleanup_services():
    """Cleanup services during application shutdown."""
    global _gemini_service
    if _gemini_service:
        # Add cleanup logic if needed
        _gemini_service = None


async def get_current_user(
    authorization: Annotated[str, Header()] = None
) -> Dict[str, Any]:
    """
    Get current authenticated user from request.
    
    For testing/development purposes, this returns a mock user.
    In production, this should validate JWT tokens or other auth mechanisms.
    
    Args:
        authorization: Authorization header from request
        
    Returns:
        User information dictionary
        
    Raises:
        HTTPException: If authentication fails
    """
    # For testing/development, return a mock user
    # In production, implement proper JWT validation here
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        # TODO: Implement proper JWT validation
        
        # Mock user for testing
        return {
            "user_id": "test_user_123",
            "email": "test@lostmindai.com",
            "name": "Test User",
            "is_active": True,
            "roles": ["user"]
        }
    
    # For development/testing, allow requests without auth
    settings = get_settings()
    if settings.DEBUG:
        return {
            "user_id": "dev_user",
            "email": "dev@lostmindai.com", 
            "name": "Development User",
            "is_active": True,
            "roles": ["admin", "user"]
        }
    
    # In production, require authentication
    raise HTTPException(
        status_code=401,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"}
    )