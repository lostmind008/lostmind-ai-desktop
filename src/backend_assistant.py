"""
Backend-Compatible Gemini Assistant for LostMind AI Desktop Client.

This module provides an API-compatible interface that connects to the FastAPI backend
instead of directly calling the Gemini API, enabling advanced features like RAG,
caching, and centralized knowledge management.
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from services.api_client import ApiClient, create_api_client
from services.async_worker import ApiManager, ConnectionMonitor
from config_manager import ConfigManager

logger = logging.getLogger(__name__)

class BackendAssistant(QObject):
    """
    Backend-compatible Gemini assistant for desktop client.
    
    Provides the same interface as the original GeminiAssistant but communicates
    with the FastAPI backend service for enhanced capabilities.
    """
    
    # Qt signals for UI updates
    response_ready = pyqtSignal(str, str)  # session_id, response
    error_occurred = pyqtSignal(str)       # error message
    thinking_update = pyqtSignal(str)      # thinking content
    status_changed = pyqtSignal(str)       # status message
    connection_status = pyqtSignal(bool)   # backend connection status
    message_streaming = pyqtSignal(str, str)  # session_id, partial_content
    file_uploaded = pyqtSignal(str, str)   # file_path, file_id
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        
        self.config_manager = config_manager
        self.config = config_manager.get_config()
        
        # Initialize API client
        backend_url = self.config.get("backend", {}).get("url", "http://localhost:8000")
        self.api_client = create_api_client(backend_url)
        self.api_manager = ApiManager(self.api_client)
        
        # Connection monitoring
        self.connection_monitor = ConnectionMonitor(self.api_manager)
        self.connection_monitor.connection_status_changed.connect(self.connection_status.emit)
        self.connection_monitor.connection_error.connect(self._handle_connection_error)
        
        # Current state
        self.current_session_id = None
        self.available_models = []
        self.is_backend_available = False
        
        # File upload tracking
        self.uploaded_files = {}  # file_path -> file_id mapping
        
        # Initialize
        self._initialize()
    
    def _initialize(self):
        """Initialize the backend assistant."""
        try:
            # Start connection monitoring
            self.connection_monitor.start_monitoring()
            
            # Load available models
            self._load_models()
            
            logger.info("Backend assistant initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize backend assistant: {e}")
            self.error_occurred.emit(f"Initialization failed: {str(e)}")
    
    def _load_models(self):
        """Load available models from backend."""
        def on_success(models):
            self.available_models = models
            logger.info(f"Loaded {len(models)} models from backend")
            
        def on_error(error):
            logger.warning(f"Failed to load models: {error}")
            # Use fallback models from config
            self.available_models = self.config.get("models", [])
        
        self.api_manager.execute_async(
            self.api_client.list_models,
            success_callback=on_success,
            error_callback=on_error
        )
    
    def _handle_connection_error(self, error: str):
        """Handle connection errors."""
        self.is_backend_available = False
        self.error_occurred.emit(f"Backend connection error: {error}")
    
    # Session Management
    
    def create_session(
        self, 
        title: str = "New Chat", 
        system_prompt: Optional[str] = None,
        model_id: Optional[str] = None,
        callback: Optional[Callable] = None
    ):
        """Create a new chat session."""
        if not model_id:
            model_id = self.config.get("default_model", "gemini-2.5-pro-preview")
        
        def on_success(session_data):
            self.current_session_id = session_data["id"]
            logger.info(f"Created session: {session_data['id']}")
            self.status_changed.emit(f"Created new session: {title}")
            if callback:
                callback(session_data)
                
        def on_error(error):
            logger.error(f"Failed to create session: {error}")
            self.error_occurred.emit(f"Failed to create session: {error}")
            if callback:
                callback(None)
        
        self.api_manager.execute_async(
            self.api_client.create_session,
            success_callback=on_success,
            error_callback=on_error,
            title=title,
            system_prompt=system_prompt,
            model_id=model_id
        )
    
    def load_session(self, session_id: str, callback: Optional[Callable] = None):
        """Load an existing session."""
        def on_success(session_data):
            self.current_session_id = session_id
            logger.info(f"Loaded session: {session_id}")
            self.status_changed.emit(f"Loaded session: {session_data.get('title', 'Untitled')}")
            if callback:
                callback(session_data)
                
        def on_error(error):
            logger.error(f"Failed to load session: {error}")
            self.error_occurred.emit(f"Failed to load session: {error}")
            if callback:
                callback(None)
        
        self.api_manager.get_session(
            session_id=session_id,
            success_callback=on_success,
            error_callback=on_error
        )
    
    def list_sessions(self, callback: Optional[Callable] = None):
        """List all available sessions."""
        def on_success(sessions):
            logger.info(f"Retrieved {len(sessions)} sessions")
            if callback:
                callback(sessions)
                
        def on_error(error):
            logger.error(f"Failed to list sessions: {error}")
            self.error_occurred.emit(f"Failed to list sessions: {error}")
            if callback:
                callback([])
        
        self.api_manager.list_sessions(
            success_callback=on_success,
            error_callback=on_error
        )
    
    def delete_session(self, session_id: str, callback: Optional[Callable] = None):
        """Delete a session."""
        def on_success(result):
            logger.info(f"Deleted session: {session_id}")
            self.status_changed.emit(f"Deleted session")
            if session_id == self.current_session_id:
                self.current_session_id = None
            if callback:
                callback(True)
                
        def on_error(error):
            logger.error(f"Failed to delete session: {error}")
            self.error_occurred.emit(f"Failed to delete session: {error}")
            if callback:
                callback(False)
        
        self.api_manager.execute_async(
            self.api_client.delete_session,
            success_callback=on_success,
            error_callback=on_error,
            session_id=session_id
        )
    
    # Message Processing
    
    def send_message(
        self,
        message: str,
        files: List[str] = None,
        use_thinking: bool = True,
        enable_search: bool = False,
        use_rag: bool = False,
        session_id: Optional[str] = None
    ):
        """Send a message to the current or specified session."""
        if not session_id:
            session_id = self.current_session_id
            
        if not session_id:
            self.error_occurred.emit("No active session. Please create or load a session first.")
            return
        
        self.status_changed.emit("Sending message...")
        
        # Choose API method based on features requested
        if use_rag:
            self._send_rag_message(session_id, message)
        else:
            self._send_regular_message(session_id, message, files, use_thinking, enable_search)
    
    def _send_regular_message(
        self, 
        session_id: str, 
        message: str, 
        files: List[str], 
        use_thinking: bool, 
        enable_search: bool
    ):
        """Send a regular message."""
        def on_success(response):
            self.status_changed.emit("Response received")
            
            # Extract response content
            content = response.get("content", "")
            thinking = response.get("thinking_content")
            
            if thinking:
                self.thinking_update.emit(thinking)
            
            self.response_ready.emit(session_id, content)
            
        def on_error(error):
            logger.error(f"Failed to send message: {error}")
            self.error_occurred.emit(f"Failed to send message: {error}")
            self.status_changed.emit("Ready")
        
        # Use cached messaging for better performance
        self.api_manager.execute_async(
            self.api_client.send_cached_message,
            success_callback=on_success,
            error_callback=on_error,
            session_id=session_id,
            content=message,
            files=files or [],
            use_thinking=use_thinking,
            enable_search=enable_search
        )
    
    def _send_rag_message(self, session_id: str, message: str):
        """Send a RAG-enhanced message."""
        def on_success(response):
            self.status_changed.emit("RAG response received")
            
            content = response.get("content", "")
            rag_context = response.get("rag_context")
            sources = response.get("sources_used", [])
            
            # Add source information to response if available
            if sources:
                content += f"\n\n**Sources:** {', '.join(sources)}"
            
            self.response_ready.emit(session_id, content)
            
        def on_error(error):
            logger.error(f"Failed to send RAG message: {error}")
            self.error_occurred.emit(f"Failed to send RAG message: {error}")
            self.status_changed.emit("Ready")
        
        self.api_manager.send_rag_message(
            session_id=session_id,
            content=message,
            success_callback=on_success,
            error_callback=on_error
        )
    
    def regenerate_last_response(self, session_id: Optional[str] = None):
        """Regenerate the last AI response."""
        if not session_id:
            session_id = self.current_session_id
            
        if not session_id:
            self.error_occurred.emit("No active session")
            return
        
        def on_success(response):
            content = response.get("content", "")
            self.response_ready.emit(session_id, content)
            self.status_changed.emit("Response regenerated")
            
        def on_error(error):
            self.error_occurred.emit(f"Failed to regenerate response: {error}")
        
        self.api_manager.execute_async(
            self.api_client.regenerate_response,
            success_callback=on_success,
            error_callback=on_error,
            session_id=session_id
        )
    
    # File Management
    
    def upload_file(self, file_path: str, callback: Optional[Callable] = None):
        """Upload a file for use in chat."""
        if not self.current_session_id:
            self.error_occurred.emit("No active session for file upload")
            return
        
        def on_success(result):
            file_id = result.get("file_id", file_path)
            self.uploaded_files[file_path] = file_id
            self.file_uploaded.emit(file_path, file_id)
            self.status_changed.emit(f"File uploaded: {Path(file_path).name}")
            if callback:
                callback(file_id)
                
        def on_error(error):
            logger.error(f"Failed to upload file: {error}")
            self.error_occurred.emit(f"Failed to upload file: {error}")
            if callback:
                callback(None)
        
        self.api_manager.execute_async(
            self.api_client.upload_file,
            success_callback=on_success,
            error_callback=on_error,
            file_path=file_path,
            session_id=self.current_session_id
        )
    
    def get_uploaded_files(self) -> Dict[str, str]:
        """Get mapping of uploaded files."""
        return self.uploaded_files.copy()
    
    def clear_uploaded_files(self):
        """Clear uploaded files tracking."""
        self.uploaded_files.clear()
    
    # Knowledge Management
    
    def upload_document_to_knowledge_base(
        self, 
        file_path: str, 
        title: Optional[str] = None,
        document_type: str = "text",
        author: Optional[str] = None,
        tags: List[str] = None,
        callback: Optional[Callable] = None
    ):
        """Upload a document to the knowledge base."""
        def on_success(result):
            doc_id = result.get("id")
            self.status_changed.emit(f"Document added to knowledge base: {title or Path(file_path).name}")
            if callback:
                callback(doc_id)
                
        def on_error(error):
            self.error_occurred.emit(f"Failed to add document to knowledge base: {error}")
            if callback:
                callback(None)
        
        self.api_manager.upload_document(
            file_path=file_path,
            title=title,
            success_callback=on_success,
            error_callback=on_error
        )
    
    def search_knowledge_base(
        self, 
        query: str, 
        limit: int = 5,
        callback: Optional[Callable] = None
    ):
        """Search the knowledge base."""
        def on_success(result):
            chunks = result.get("chunks", [])
            if callback:
                callback(chunks)
                
        def on_error(error):
            self.error_occurred.emit(f"Knowledge search failed: {error}")
            if callback:
                callback([])
        
        self.api_manager.search_knowledge(
            query=query,
            limit=limit,
            success_callback=on_success,
            error_callback=on_error
        )
    
    def get_knowledge_stats(self, callback: Optional[Callable] = None):
        """Get knowledge base statistics."""
        def on_success(stats):
            if callback:
                callback(stats)
                
        def on_error(error):
            logger.warning(f"Failed to get knowledge stats: {error}")
            if callback:
                callback({})
        
        self.api_manager.execute_async(
            self.api_client.get_knowledge_stats,
            success_callback=on_success,
            error_callback=on_error
        )
    
    # Model Management
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models."""
        return self.available_models
    
    def refresh_models(self):
        """Refresh the list of available models."""
        self._load_models()
    
    # Utility Methods
    
    def get_backend_status(self, callback: Optional[Callable] = None):
        """Get backend service status."""
        def on_success(status):
            self.is_backend_available = True
            if callback:
                callback(status)
                
        def on_error(error):
            self.is_backend_available = False
            if callback:
                callback({"status": "error", "error": error})
        
        self.api_manager.execute_async(
            self.api_client.get_backend_status,
            success_callback=on_success,
            error_callback=on_error
        )
    
    def get_cache_stats(self, callback: Optional[Callable] = None):
        """Get cache statistics."""
        self.api_manager.execute_async(
            self.api_client.get_cache_stats,
            success_callback=callback,
            error_callback=lambda e: callback({}) if callback else None
        )
    
    def clear_cache(self, callback: Optional[Callable] = None):
        """Clear cache."""
        def on_success(result):
            self.status_changed.emit("Cache cleared")
            if callback:
                callback(True)
                
        def on_error(error):
            self.error_occurred.emit(f"Failed to clear cache: {error}")
            if callback:
                callback(False)
        
        self.api_manager.execute_async(
            self.api_client.clear_cache,
            success_callback=on_success,
            error_callback=on_error
        )
    
    def is_connected(self) -> bool:
        """Check if connected to backend."""
        return self.is_backend_available
    
    def cleanup(self):
        """Clean up resources."""
        try:
            self.connection_monitor.stop_monitoring()
            self.api_manager.cleanup()
            
            # Close API client session
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.api_client.__aexit__(None, None, None))
            loop.close()
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            self.cleanup()
        except Exception:
            pass  # Ignore errors during destruction