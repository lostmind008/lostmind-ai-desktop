"""
Configuration management for LostMindAI Backend API Service.

Handles environment-based configuration with sensible defaults
for both development and production deployment.
"""

import os
from functools import lru_cache
from typing import Optional, List
from pydantic import BaseSettings, validator


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Server Configuration
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # Google AI Configuration
    GOOGLE_CLOUD_PROJECT: Optional[str] = None
    GOOGLE_CLOUD_LOCATION: str = "us-central1"
    GEMINI_API_KEY: Optional[str] = None
    
    # Database Configuration
    DATABASE_URL: str = "sqlite:///./lostmindai.db"
    VECTOR_DB_PATH: str = "./data/vectors.db"
    
    # Caching Configuration
    REDIS_URL: Optional[str] = None
    CACHE_TTL_SHORT: int = 3600  # 1 hour
    CACHE_TTL_MEDIUM: int = 86400  # 24 hours
    CACHE_TTL_LONG: int = 604800  # 7 days
    
    # File Upload Configuration
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = [
        ".pdf", ".txt", ".md", ".py", ".js", ".html", ".css", ".json", ".csv",
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
        ".mp4", ".webm", ".avi"
    ]
    
    # RAG Configuration
    RAG_ENABLED: bool = True
    EMBEDDING_MODEL: str = "text-embedding-004"
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    MAX_CONTEXT_ITEMS: int = 5
    
    # AI Model Configuration
    DEFAULT_MODEL: str = "gemini-2.5-pro-preview"
    DEFAULT_TEMPERATURE: float = 0.7
    DEFAULT_MAX_TOKENS: int = 8192
    
    # Thinking Budget Configuration
    THINKING_BUDGET_AUTO: bool = True
    THINKING_BUDGET_LIGHT: int = 1024
    THINKING_BUDGET_MODERATE: int = 4096
    THINKING_BUDGET_DEEP: int = 8192
    THINKING_BUDGET_MAXIMUM: int = 24576
    
    # Performance Configuration
    MAX_CONCURRENT_REQUESTS: int = 10
    REQUEST_TIMEOUT: int = 300  # 5 minutes
    
    @validator("GOOGLE_CLOUD_PROJECT")
    def validate_google_project(cls, v):
        """Validate Google Cloud project configuration."""
        if not v and not os.getenv("GEMINI_API_KEY"):
            raise ValueError(
                "Either GOOGLE_CLOUD_PROJECT or GEMINI_API_KEY must be set"
            )
        return v
    
    @validator("SECRET_KEY")
    def validate_secret_key(cls, v):
        """Validate secret key for production."""
        if v == "your-secret-key-change-in-production":
            import secrets
            return secrets.token_urlsafe(32)
        return v
    
    @validator("UPLOAD_DIR")
    def validate_upload_dir(cls, v):
        """Ensure upload directory exists."""
        os.makedirs(v, exist_ok=True)
        return v
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.DEBUG
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return not self.DEBUG
    
    @property
    def use_redis_cache(self) -> bool:
        """Check if Redis caching is available."""
        return self.REDIS_URL is not None
    
    @property
    def gemini_config(self) -> dict:
        """Get Gemini configuration dictionary."""
        config = {
            "temperature": self.DEFAULT_TEMPERATURE,
            "max_output_tokens": self.DEFAULT_MAX_TOKENS,
        }
        
        if self.GOOGLE_CLOUD_PROJECT:
            config.update({
                "project_id": self.GOOGLE_CLOUD_PROJECT,
                "location": self.GOOGLE_CLOUD_LOCATION,
                "vertexai": True
            })
        elif self.GEMINI_API_KEY:
            config.update({
                "api_key": self.GEMINI_API_KEY,
                "vertexai": False
            })
        
        return config
    
    @property
    def rag_config(self) -> dict:
        """Get RAG configuration dictionary."""
        return {
            "enabled": self.RAG_ENABLED,
            "embedding_model": self.EMBEDDING_MODEL,
            "chunk_size": self.CHUNK_SIZE,
            "chunk_overlap": self.CHUNK_OVERLAP,
            "max_context_items": self.MAX_CONTEXT_ITEMS,
            "vector_db_path": self.VECTOR_DB_PATH
        }
    
    @property
    def thinking_budget_config(self) -> dict:
        """Get thinking budget configuration."""
        return {
            "auto_detect": self.THINKING_BUDGET_AUTO,
            "light": self.THINKING_BUDGET_LIGHT,
            "moderate": self.THINKING_BUDGET_MODERATE,
            "deep": self.THINKING_BUDGET_DEEP,
            "maximum": self.THINKING_BUDGET_MAXIMUM
        }
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


def get_database_url() -> str:
    """Get database URL for SQLAlchemy."""
    settings = get_settings()
    return settings.DATABASE_URL


def get_redis_url() -> Optional[str]:
    """Get Redis URL if available."""
    settings = get_settings()
    return settings.REDIS_URL