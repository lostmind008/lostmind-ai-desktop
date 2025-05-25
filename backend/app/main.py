"""
LostMindAI Backend API Service

FastAPI-based backend service providing AI chat capabilities, RAG pipeline,
and knowledge management for both desktop and web clients.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.core.config import Settings
from app.api import health, chat, knowledge
from app.api.endpoints import rag, chat_rag
from app.core.dependencies import initialize_services, cleanup_services, get_gemini_service
from app.services.gemini_service import GeminiService

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    # Startup
    logger.info("Starting LostMindAI Backend API Service...")
    
    settings = Settings()
    
    # Initialize services
    try:
        await initialize_services(settings)
        logger.info("All services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down LostMindAI Backend API Service...")
    await cleanup_services()

# Create FastAPI application
app = FastAPI(
    title="LostMindAI Backend API",
    description="API-first AI assistant service supporting desktop and web clients",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware for web client
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(knowledge.router, prefix="/api/v1")
app.include_router(rag.router, prefix="/api/v1/rag", tags=["RAG"])
app.include_router(chat_rag.router, prefix="/api/v1/chat", tags=["Chat with RAG"])

# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections for real-time chat."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept WebSocket connection."""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected: {session_id}")
    
    def disconnect(self, session_id: str):
        """Remove WebSocket connection."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected: {session_id}")
    
    async def send_message(self, session_id: str, message: Dict[str, Any]):
        """Send message to specific connection."""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send WebSocket message: {e}")
                self.disconnect(session_id)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connections."""
        disconnected = []
        for session_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to broadcast to {session_id}: {e}")
                disconnected.append(session_id)
        
        # Clean up disconnected websockets
        for session_id in disconnected:
            self.disconnect(session_id)

manager = ConnectionManager()

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time chat communication."""
    await manager.connect(websocket, session_id)
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            # Process chat message through Gemini service
            if data.get("type") == "chat_message":
                try:
                    gemini_service = get_gemini_service(Settings())
                    response = await gemini_service.process_message(
                        session_id=session_id,
                        message=data.get("message", ""),
                        attachments=data.get("files", [])
                    )
                    
                    # Send response back to client
                    await manager.send_message(session_id, {
                        "type": "chat_response",
                        "response": response.dict()
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing chat message: {e}")
                    await manager.send_message(session_id, {
                        "type": "error",
                        "message": f"Error processing message: {str(e)}"
                    })
            
            # Handle other message types (file uploads, commands, etc.)
            elif data.get("type") == "ping":
                await manager.send_message(session_id, {"type": "pong"})
                
    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket error for {session_id}: {e}")
        manager.disconnect(session_id)

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "LostMindAI Backend API Service",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }

def main():
    """Main entry point for running the server."""
    settings = Settings()
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )

if __name__ == "__main__":
    main()