"""
GenAI Service wrapper for LostMindAI Backend.
Provides compatibility layer for RAG services that expect GenAIService.
This is essentially an alias/wrapper for GeminiService.
"""

import logging
from typing import Optional

from app.services.gemini_service import GeminiService
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class GenAIService:
    """
    GenAI Service wrapper that provides compatibility for RAG services.
    This class acts as a wrapper around GeminiService to maintain API compatibility.
    """
    
    def __init__(self, settings: Optional[object] = None):
        """Initialize GenAI service as a wrapper around GeminiService."""
        if settings is None:
            settings = get_settings()
            
        self._gemini_service = GeminiService(settings)
        logger.info("GenAI service initialized as GeminiService wrapper")
    
    @property
    def client(self):
        """Get the underlying Gemini client for RAG operations."""
        return self._gemini_service.client
    
    def __getattr__(self, name):
        """Delegate all other attributes to the underlying GeminiService."""
        return getattr(self._gemini_service, name)