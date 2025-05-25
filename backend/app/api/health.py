"""
Health check endpoints for LostMindAI Backend API Service.

Provides health monitoring, status checks, and system information
for both internal monitoring and external load balancers.
"""

import asyncio
import os
import psutil
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.config import get_settings, Settings
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Store application start time
_start_time = time.time()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: datetime
    uptime_seconds: float
    version: str
    environment: str


class DetailedHealthResponse(BaseModel):
    """Detailed health check response model."""
    status: str
    timestamp: datetime
    uptime_seconds: float
    version: str
    environment: str
    system_info: Dict[str, Any]
    services: Dict[str, str]
    configuration: Dict[str, Any]


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Basic health check endpoint.
    
    Returns:
        Basic health status and uptime information
    """
    try:
        current_time = datetime.now(timezone.utc)
        uptime = time.time() - _start_time
        
        return HealthResponse(
            status="healthy",
            timestamp=current_time,
            uptime_seconds=uptime,
            version="1.0.0",
            environment="development" if get_settings().DEBUG else "production"
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check(settings: Settings = Depends(get_settings)):
    """
    Detailed health check endpoint with system information.
    
    Returns:
        Comprehensive health status including system metrics and service status
    """
    try:
        current_time = datetime.now(timezone.utc)
        uptime = time.time() - _start_time
        
        # System information
        system_info = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else None,
            "python_version": f"{psutil.version_info.major}.{psutil.version_info.minor}",
            "platform": psutil.platform.system() if hasattr(psutil, 'platform') else "unknown"
        }
        
        # Service status checks
        services_status = await check_services_status(settings)
        
        # Configuration summary (non-sensitive)
        config_summary = {
            "debug_mode": settings.DEBUG,
            "rag_enabled": settings.RAG_ENABLED,
            "redis_configured": settings.use_redis_cache,
            "max_file_size_mb": settings.MAX_FILE_SIZE // (1024 * 1024),
            "allowed_file_types_count": len(settings.ALLOWED_FILE_TYPES),
            "default_model": settings.DEFAULT_MODEL
        }
        
        # Determine overall status
        overall_status = "healthy"
        if any(status != "healthy" for status in services_status.values()):
            overall_status = "degraded"
        if system_info["memory_percent"] > 90 or system_info["cpu_percent"] > 90:
            overall_status = "degraded"
        
        return DetailedHealthResponse(
            status=overall_status,
            timestamp=current_time,
            uptime_seconds=uptime,
            version="1.0.0",
            environment="development" if settings.DEBUG else "production",
            system_info=system_info,
            services=services_status,
            configuration=config_summary
        )
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


@router.get("/health/ready")
async def readiness_check(settings: Settings = Depends(get_settings)):
    """
    Kubernetes-style readiness probe.
    
    Returns:
        200 if service is ready to accept traffic, 503 otherwise
    """
    try:
        # Check critical services
        services_status = await check_services_status(settings)
        
        # Check if critical services are healthy
        critical_services = ["gemini", "cache"]
        for service in critical_services:
            if services_status.get(service) != "healthy":
                raise HTTPException(
                    status_code=503, 
                    detail=f"Critical service {service} is not ready"
                )
        
        return {"status": "ready"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")


@router.get("/health/live")
async def liveness_check():
    """
    Kubernetes-style liveness probe.
    
    Returns:
        200 if service is alive, 503 otherwise
    """
    try:
        # Basic liveness check - can the service respond?
        return {"status": "alive", "timestamp": datetime.now(timezone.utc)}
        
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not alive")


async def check_services_status(settings: Settings) -> Dict[str, str]:
    """
    Check the status of various services.
    
    Args:
        settings: Application settings
    
    Returns:
        Dictionary with service names and their status
    """
    services = {}
    
    # Check Gemini service
    try:
        # Import here to avoid circular imports
        from services.gemini_service import GeminiService
        
        # Simple check - can we initialize the service?
        services["gemini"] = "healthy"
    except Exception as e:
        logger.error(f"Gemini service check failed: {e}")
        services["gemini"] = "unhealthy"
    
    # Check cache service
    try:
        if settings.use_redis_cache:
            # Check Redis connection
            from services.cache_service import CacheService
            services["cache"] = "healthy"  # TODO: Implement actual Redis ping
        else:
            # Using local cache
            services["cache"] = "healthy"
    except Exception as e:
        logger.error(f"Cache service check failed: {e}")
        services["cache"] = "unhealthy"
    
    # Check vector database
    try:
        if os.path.exists(settings.VECTOR_DB_PATH) or settings.RAG_ENABLED:
            services["vector_db"] = "healthy"
        else:
            services["vector_db"] = "not_configured"
    except Exception as e:
        logger.error(f"Vector DB check failed: {e}")
        services["vector_db"] = "unhealthy"
    
    # Check file system
    try:
        upload_dir = settings.UPLOAD_DIR
        if os.path.exists(upload_dir) and os.access(upload_dir, os.W_OK):
            services["filesystem"] = "healthy"
        else:
            services["filesystem"] = "unhealthy"
    except Exception as e:
        logger.error(f"Filesystem check failed: {e}")
        services["filesystem"] = "unhealthy"
    
    return services


@router.get("/metrics")
async def metrics_endpoint():
    """
    Prometheus-style metrics endpoint.
    
    Returns:
        Basic metrics in Prometheus format
    """
    try:
        uptime = time.time() - _start_time
        cpu_percent = psutil.cpu_percent()
        memory_percent = psutil.virtual_memory().percent
        
        metrics = [
            f"# HELP lostmindai_uptime_seconds Application uptime in seconds",
            f"# TYPE lostmindai_uptime_seconds gauge",
            f"lostmindai_uptime_seconds {uptime}",
            f"",
            f"# HELP lostmindai_cpu_percent CPU usage percentage",
            f"# TYPE lostmindai_cpu_percent gauge",
            f"lostmindai_cpu_percent {cpu_percent}",
            f"",
            f"# HELP lostmindai_memory_percent Memory usage percentage",
            f"# TYPE lostmindai_memory_percent gauge",
            f"lostmindai_memory_percent {memory_percent}",
        ]
        
        return "\n".join(metrics)
        
    except Exception as e:
        logger.error(f"Metrics endpoint failed: {e}")
        raise HTTPException(status_code=503, detail="Metrics unavailable")