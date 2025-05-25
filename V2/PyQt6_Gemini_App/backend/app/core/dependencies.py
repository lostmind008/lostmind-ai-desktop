"""
Dependency injection for FastAPI application.
Manages service instances and their lifecycle.
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.core.config import Settings
from app.services.gemini_service import GeminiService
from app.services.cache_service import CacheService
from app.services.vector_service import VectorService


@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached singleton)."""
    return Settings()


# Global service instances
_gemini_service = None
_cache_service = None
_vector_service = None


def get_gemini_service(
    settings: Annotated[Settings, Depends(get_settings)]
) -> GeminiService:
    """Get GeminiService instance (singleton)."""
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiService(settings)
    return _gemini_service


def get_cache_service(
    settings: Annotated[Settings, Depends(get_settings)]
) -> CacheService:
    """Get CacheService instance (singleton)."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService(settings)
    return _cache_service


def get_vector_service(
    settings: Annotated[Settings, Depends(get_settings)]
) -> VectorService:
    """Get VectorService instance (singleton)."""
    global _vector_service
    if _vector_service is None:
        _vector_service = VectorService(settings)
    return _vector_service


# For manual service initialization during app startup
async def initialize_services(settings: Settings):
    """Initialize all services during application startup."""
    global _gemini_service, _cache_service, _vector_service
    
    # Initialize Gemini service
    if _gemini_service is None:
        _gemini_service = GeminiService(settings)
        await _gemini_service.initialize()
    
    # Initialize cache service
    if _cache_service is None:
        _cache_service = CacheService(settings)
        await _cache_service.connect()
    
    # Initialize vector service
    if _vector_service is None:
        _vector_service = VectorService(settings)
        await _vector_service.initialize()


async def cleanup_services():
    """Cleanup services during application shutdown."""
    global _gemini_service, _cache_service, _vector_service
    
    if _gemini_service:
        await _gemini_service.cleanup()
        _gemini_service = None
    
    if _cache_service:
        await _cache_service.disconnect()
        _cache_service = None
    
    if _vector_service:
        # Vector service doesn't need explicit cleanup
        _vector_service = None