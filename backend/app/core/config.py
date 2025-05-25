"""
Configuration management for LostMindAI Backend API Service.

Handles environment-based configuration with sensible defaults
for both development and production deployment.
"""

import os
from functools import lru_cache
from typing import Optional, List
from pydantic import validator
from pydantic_settings import BaseSettings


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
    DATABASE_URL: str = "sqlite+aiosqlite:///./lostmindai.db"
    VECTOR_DB_PATH: str = "./data/vectors.db"
    
    # Caching Configuration
    REDIS_URL: Optional[str] = None
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
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
    DEFAULT_MODEL: str = "gemini-2.0-flash"  # Updated to latest stable model
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
    
    @validator("VECTOR_DB_PATH")
    def validate_vector_db_path(cls, v):
        """Ensure vector database directory exists."""
        if v:
            os.makedirs(os.path.dirname(v) if os.path.dirname(v) else "./data", exist_ok=True)
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
        return self.REDIS_URL is not None or (self.REDIS_HOST and self.REDIS_PORT)
    
    @property
    def redis_host(self) -> str:
        """Get Redis host from URL or direct config."""
        if self.REDIS_URL:
            # Parse Redis URL (redis://host:port/db)
            return self.REDIS_URL.split("//")[1].split(":")[0]
        return self.REDIS_HOST
    
    @property
    def redis_port(self) -> int:
        """Get Redis port from URL or direct config."""
        if self.REDIS_URL:
            # Parse Redis URL
            parts = self.REDIS_URL.split("//")[1].split(":")
            if len(parts) > 1:
                return int(parts[1].split("/")[0])
        return self.REDIS_PORT
    
    @property
    def redis_db(self) -> int:
        """Get Redis database from URL or direct config."""
        if self.REDIS_URL:
            # Parse Redis URL
            if "/" in self.REDIS_URL:
                return int(self.REDIS_URL.split("/")[-1])
        return self.REDIS_DB
    
    @property
    def redis_password(self) -> Optional[str]:
        """Get Redis password from URL or direct config."""
        if self.REDIS_URL and "@" in self.REDIS_URL:
            # Parse Redis URL with password (redis://:password@host:port/db)
            return self.REDIS_URL.split("//")[1].split("@")[0].split(":")[-1]
        return self.REDIS_PASSWORD
    
    @property
    def vector_db_path(self) -> str:
        """Get vector database path."""
        return self.VECTOR_DB_PATH
    
    @property
    def embedding_model(self) -> str:
        """Get embedding model name."""
        # Map Gemini embedding model to sentence-transformers model
        if self.EMBEDDING_MODEL == "text-embedding-004":
            return "all-MiniLM-L6-v2"  # Fast, good quality
        elif self.EMBEDDING_MODEL == "text-embedding-preview":
            return "all-mpnet-base-v2"  # Higher quality
        else:
            return "all-MiniLM-L6-v2"  # Default fallback
    
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