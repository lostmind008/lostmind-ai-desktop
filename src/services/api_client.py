"""
API Client for LostMindAI Backend Service.

Provides HTTP and WebSocket connectivity to the FastAPI backend,
replacing direct Gemini API calls with backend service communication.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, AsyncGenerator, Callable
from pathlib import Path

import aiohttp
import websockets
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from PyQt6.QtWidgets import QApplication

from src.utils.retry_handler import RetryableSession, RetryConfig, rate_limit_tracker

logger = logging.getLogger(__name__)

class ApiClientError(Exception):
    """Custom exception for API client errors."""
    pass

class WebSocketManager(QObject):
    """Manages WebSocket connection for real-time chat communication."""
    
    # Qt signals for UI updates
    message_received = pyqtSignal(dict)
    connection_status_changed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url.replace("http", "ws")
        self.websocket = None
        self.session_id = None
        self.is_connected = False
        self._connection_task = None
        
    async def connect(self, session_id: str):
        """Connect to WebSocket for a specific session."""
        self.session_id = session_id
        
        try:
            ws_url = f"{self.base_url}/ws/{session_id}"
            self.websocket = await websockets.connect(ws_url)
            self.is_connected = True
            self.connection_status_changed.emit(True)
            
            # Start listening for messages
            self._connection_task = asyncio.create_task(self._listen_for_messages())
            logger.info(f"WebSocket connected for session: {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to connect WebSocket: {e}")
            self.error_occurred.emit(f"WebSocket connection failed: {str(e)}")
            self.is_connected = False
            self.connection_status_changed.emit(False)
    
    async def disconnect(self):
        """Disconnect WebSocket."""
        self.is_connected = False
        
        if self._connection_task:
            self._connection_task.cancel()
            
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            
        self.connection_status_changed.emit(False)
        logger.info("WebSocket disconnected")
    
    async def send_message(self, message: str, files: List[str] = None):
        """Send a chat message through WebSocket."""
        if not self.is_connected or not self.websocket:
            raise ApiClientError("WebSocket not connected")
        
        message_data = {
            "type": "chat_message",
            "message": message,
            "files": files or [],
            "timestamp": datetime.now().isoformat()
        }
        
        await self.websocket.send(json.dumps(message_data))
    
    async def _listen_for_messages(self):
        """Listen for incoming WebSocket messages."""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    self.message_received.emit(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode WebSocket message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
            self.is_connected = False
            self.connection_status_changed.emit(False)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            self.error_occurred.emit(f"WebSocket error: {str(e)}")
            self.is_connected = False
            self.connection_status_changed.emit(False)

class ApiClient:
    """
    HTTP API client for LostMindAI backend service.
    
    Provides methods for chat sessions, knowledge management,
    and backend service interaction.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.api_base = f"{self.base_url}/api/v1"
        self.session = None
        self.retryable_session = None
        self.websocket_manager = WebSocketManager(base_url)
        self.retry_config = RetryConfig(
            max_attempts=3,
            initial_delay=1.0,
            max_delay=30.0,
            exponential_base=2.0,
            jitter=True
        )
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        self.retryable_session = RetryableSession(self.session, self.retry_config)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
        await self.websocket_manager.disconnect()
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Dict = None,
        files: Dict = None,
        params: Dict = None
    ) -> Dict[str, Any]:
        """Make HTTP request to backend API with retry logic."""
        if not self.session:
            self.session = aiohttp.ClientSession()
            self.retryable_session = RetryableSession(self.session, self.retry_config)
        
        url = f"{self.api_base}{endpoint}"
        
        try:
            kwargs = {"params": params} if params else {}
            
            if files:
                # Handle file uploads
                data = aiohttp.FormData()
                for key, file_path in files.items():
                    if isinstance(file_path, (str, Path)):
                        data.add_field(key, open(file_path, 'rb'), filename=Path(file_path).name)
                    else:
                        data.add_field(key, file_path)
                if json_data:
                    for key, value in json_data.items():
                        data.add_field(key, str(value))
                kwargs["data"] = data
            elif json_data:
                kwargs["json"] = json_data
            
            # Use retryable session for automatic retry logic
            response = await self.retryable_session.request(method, url, **kwargs)
            
            if response.content_type == 'application/json':
                result = await response.json()
            else:
                result = {"content": await response.text()}
            
            if response.status >= 400:
                error_msg = result.get("detail", f"HTTP {response.status}")
                # Log rate limit info if available
                if response.status == 429:
                    logger.warning(f"Rate limit hit for {endpoint}. Headers: {dict(response.headers)}")
                raise ApiClientError(f"API request failed: {error_msg}")
            
            return result
                
        except aiohttp.ClientError as e:
            logger.error(f"HTTP request failed: {e}")
            raise ApiClientError(f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in API request: {e}")
            raise ApiClientError(f"Request failed: {str(e)}")
    
    # Health and Status Methods
    
    async def check_health(self) -> Dict[str, Any]:
        """Check backend service health."""
        return await self._make_request("GET", "/health")
    
    async def get_backend_status(self) -> Dict[str, Any]:
        """Get detailed backend status including services."""
        return await self._make_request("GET", "/health/status")
    
    # Chat Session Management
    
    async def create_session(
        self,
        title: str = "New Chat",
        system_prompt: Optional[str] = None,
        model_id: str = "gemini-2.5-pro-preview"
    ) -> Dict[str, Any]:
        """Create a new chat session."""
        data = {
            "title": title,
            "system_prompt": system_prompt,
            "model_id": model_id
        }
        return await self._make_request("POST", "/chat/sessions", json_data=data)
    
    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get session details."""
        return await self._make_request("GET", f"/chat/sessions/{session_id}")
    
    async def list_sessions(self) -> List[Dict[str, Any]]:
        """List all chat sessions."""
        result = await self._make_request("GET", "/chat/sessions")
        return result.get("sessions", [])
    
    async def delete_session(self, session_id: str) -> Dict[str, Any]:
        """Delete a chat session."""
        return await self._make_request("DELETE", f"/chat/sessions/{session_id}")
    
    async def update_session(
        self,
        session_id: str,
        title: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update session metadata."""
        data = {}
        if title is not None:
            data["title"] = title
        if system_prompt is not None:
            data["system_prompt"] = system_prompt
        
        return await self._make_request("PUT", f"/chat/sessions/{session_id}", json_data=data)
    
    # Message Handling
    
    async def send_message(
        self,
        session_id: str,
        content: str,
        files: List[str] = None,
        use_thinking: bool = True,
        enable_search: bool = False
    ) -> Dict[str, Any]:
        """Send a message to a session."""
        data = {
            "content": content,
            "files": files or [],
            "use_thinking": use_thinking,
            "enable_search": enable_search
        }
        return await self._make_request("POST", f"/chat/sessions/{session_id}/messages", json_data=data)
    
    async def send_rag_message(
        self,
        session_id: str,
        content: str,
        use_rag: bool = True,
        rag_limit: int = 3,
        rag_threshold: float = 0.7,
        knowledge_filters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Send a message with RAG enhancement."""
        data = {
            "message": content,
            "use_rag": use_rag,
            "rag_limit": rag_limit,
            "rag_threshold": rag_threshold,
            "knowledge_filters": knowledge_filters or {}
        }
        return await self._make_request("POST", f"/chat/sessions/{session_id}/rag", json_data=data)
    
    async def send_cached_message(
        self,
        session_id: str,
        content: str,
        files: List[str] = None,
        use_thinking: bool = True,
        enable_search: bool = False
    ) -> Dict[str, Any]:
        """Send a message with caching optimization."""
        data = {
            "content": content,
            "files": files or [],
            "use_thinking": use_thinking,
            "enable_search": enable_search
        }
        return await self._make_request("POST", f"/chat/sessions/{session_id}/messages/cached", json_data=data)
    
    async def get_session_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all messages in a session."""
        result = await self._make_request("GET", f"/chat/sessions/{session_id}/messages")
        return result.get("messages", [])
    
    async def regenerate_response(self, session_id: str) -> Dict[str, Any]:
        """Regenerate the last AI response."""
        return await self._make_request("POST", f"/chat/sessions/{session_id}/regenerate")
    
    # Knowledge Management
    
    async def create_document(
        self,
        title: str,
        content: str,
        document_type: str = "text",
        source: Optional[str] = None,
        author: Optional[str] = None,
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """Create a new document in the knowledge base."""
        data = {
            "title": title,
            "content": content,
            "document_type": document_type,
            "source": source,
            "author": author,
            "tags": tags or []
        }
        return await self._make_request("POST", "/knowledge/documents", json_data=data)
    
    async def upload_document(
        self,
        file_path: str,
        title: Optional[str] = None,
        document_type: str = "text",
        author: Optional[str] = None,
        tags: str = None
    ) -> Dict[str, Any]:
        """Upload a file to the knowledge base."""
        files = {"file": file_path}
        data = {
            "title": title,
            "document_type": document_type,
            "author": author,
            "tags": tags
        }
        return await self._make_request("POST", "/knowledge/upload", files=files, json_data=data)
    
    async def search_knowledge(
        self,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.7,
        document_types: List[str] = None,
        tags: List[str] = None,
        author: Optional[str] = None
    ) -> Dict[str, Any]:
        """Search the knowledge base."""
        data = {
            "query": query,
            "limit": limit,
            "score_threshold": score_threshold,
            "document_types": document_types,
            "tags": tags,
            "author": author
        }
        return await self._make_request("POST", "/knowledge/search", json_data=data)
    
    async def get_knowledge_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        return await self._make_request("GET", "/knowledge/stats")
    
    async def delete_document(self, document_id: str) -> Dict[str, Any]:
        """Delete a document from the knowledge base."""
        return await self._make_request("DELETE", f"/knowledge/documents/{document_id}")
    
    # File Operations
    
    async def upload_file(self, file_path: str, session_id: str) -> Dict[str, Any]:
        """Upload a file for use in chat."""
        files = {"file": file_path}
        data = {"session_id": session_id}
        return await self._make_request("POST", "/files/upload", files=files, json_data=data)
    
    # Model Management
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """Get available AI models."""
        result = await self._make_request("GET", "/chat/models")
        return result if isinstance(result, list) else result.get("models", [])
    
    # Cache Management
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return await self._make_request("GET", "/knowledge/cache/stats")
    
    async def clear_cache(self) -> Dict[str, Any]:
        """Clear cache entries."""
        return await self._make_request("POST", "/knowledge/cache/clear")
    
    async def get_session_cache(self, session_id: str) -> Dict[str, Any]:
        """Get cached data for a session."""
        return await self._make_request("GET", f"/chat/sessions/{session_id}/cache")
    
    async def clear_session_cache(self, session_id: str) -> Dict[str, Any]:
        """Clear cache for a specific session."""
        return await self._make_request("DELETE", f"/chat/sessions/{session_id}/cache")
    
    # WebSocket Methods
    
    async def connect_websocket(self, session_id: str):
        """Connect WebSocket for real-time chat."""
        await self.websocket_manager.connect(session_id)
    
    async def send_websocket_message(self, message: str, files: List[str] = None):
        """Send message through WebSocket."""
        await self.websocket_manager.send_message(message, files)
    
    def get_websocket_manager(self) -> WebSocketManager:
        """Get WebSocket manager for signal connections."""
        return self.websocket_manager

# Convenience factory function
def create_api_client(backend_url: str = "http://localhost:8000") -> ApiClient:
    """Create and return configured API client."""
    return ApiClient(backend_url)