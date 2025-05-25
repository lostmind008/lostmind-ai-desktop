"""
Dependency injection for FastAPI application.
Manages service instances and their lifecycle.
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

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