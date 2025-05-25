"""
Assistant Adapter for seamless switching between direct API and backend modes.

Provides a unified interface that can switch between the original GeminiAssistant
(direct API calls) and the new BackendAssistant (backend service communication)
based on user preference or backend availability.
"""

import logging
from typing import Dict, List, Optional, Any, Callable, Union

from PyQt6.QtCore import QObject, pyqtSignal

from config_manager import ConfigManager
from gemini_assistant import GeminiAssistant
from backend_assistant import BackendAssistant

logger = logging.getLogger(__name__)

class AssistantAdapter(QObject):
    """
    Adapter that provides a unified interface for both direct API and backend service modes.
    
    This allows the UI to remain unchanged while switching between different
    backend implementations seamlessly.
    """
    
    # Unified signals that both assistants support
    response_ready = pyqtSignal(str, str)      # session_id, response
    error_occurred = pyqtSignal(str)           # error message
    thinking_update = pyqtSignal(str)          # thinking content
    status_changed = pyqtSignal(str)           # status message
    file_uploaded = pyqtSignal(str, str)       # file_path, file_id
    
    # Backend-specific signals
    backend_connection_status = pyqtSignal(bool)  # backend connection status
    knowledge_stats_updated = pyqtSignal(dict)    # knowledge base statistics
    cache_stats_updated = pyqtSignal(dict)        # cache statistics
    search_results_ready = pyqtSignal(list)       # search results
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        
        self.config_manager = config_manager
        self.config = config_manager.get_config()
        
        # Initialize both assistants
        self.direct_assistant = None
        self.backend_assistant = None
        
        # Current mode and active assistant
        self.current_mode = "direct"  # "direct" or "backend"
        self.active_assistant = None
        
        # Initialize with direct mode by default
        self._initialize_direct_assistant()
        
        # Backend configuration
        self.backend_url = "http://localhost:8000"
        self.rag_enabled = False
        self.rag_settings = {
            "limit": 3,
            "threshold": 0.7
        }
    
    def _initialize_direct_assistant(self):
        """Initialize the direct API assistant."""
        try:
            if not self.direct_assistant:
                self.direct_assistant = GeminiAssistant(self.config_manager)
                self._connect_direct_signals()
            
            self.active_assistant = self.direct_assistant
            self.current_mode = "direct"
            logger.info("Direct assistant initialized and activated")
            
        except Exception as e:
            logger.error(f"Failed to initialize direct assistant: {e}")
            self.error_occurred.emit(f"Failed to initialize direct assistant: {str(e)}")
    
    def _initialize_backend_assistant(self):
        """Initialize the backend service assistant."""
        try:
            if not self.backend_assistant:
                # Update config with backend URL
                if "backend" not in self.config:
                    self.config["backend"] = {}
                self.config["backend"]["url"] = self.backend_url
                
                self.backend_assistant = BackendAssistant(self.config_manager)
                self._connect_backend_signals()
            
            self.active_assistant = self.backend_assistant
            self.current_mode = "backend"
            logger.info("Backend assistant initialized and activated")
            
        except Exception as e:
            logger.error(f"Failed to initialize backend assistant: {e}")
            self.error_occurred.emit(f"Failed to initialize backend assistant: {str(e)}")
    
    def _connect_direct_signals(self):
        """Connect signals from the direct assistant."""
        if self.direct_assistant:
            self.direct_assistant.response_ready.connect(self.response_ready.emit)
            self.direct_assistant.error_occurred.connect(self.error_occurred.emit)
            self.direct_assistant.thinking_update.connect(self.thinking_update.emit)
            self.direct_assistant.status_changed.connect(self.status_changed.emit)
            self.direct_assistant.file_uploaded.connect(self.file_uploaded.emit)
    
    def _connect_backend_signals(self):
        """Connect signals from the backend assistant."""
        if self.backend_assistant:
            self.backend_assistant.response_ready.connect(self.response_ready.emit)
            self.backend_assistant.error_occurred.connect(self.error_occurred.emit)
            self.backend_assistant.thinking_update.connect(self.thinking_update.emit)
            self.backend_assistant.status_changed.connect(self.status_changed.emit)
            self.backend_assistant.file_uploaded.connect(self.file_uploaded.emit)
            self.backend_assistant.connection_status.connect(self.backend_connection_status.emit)
    
    # Mode switching methods
    
    def switch_to_direct_mode(self):
        """Switch to direct API mode."""
        if self.current_mode == "direct":
            return
        
        try:
            self._initialize_direct_assistant()
            self.status_changed.emit("Switched to direct API mode")
            
        except Exception as e:
            logger.error(f"Failed to switch to direct mode: {e}")
            self.error_occurred.emit(f"Failed to switch to direct mode: {str(e)}")
    
    def switch_to_backend_mode(self, backend_url: str = None):
        """Switch to backend service mode."""
        if backend_url:
            self.backend_url = backend_url
        
        if self.current_mode == "backend":
            return
        
        try:
            self._initialize_backend_assistant()
            self.status_changed.emit("Switched to backend service mode")
            
        except Exception as e:
            logger.error(f"Failed to switch to backend mode: {e}")
            self.error_occurred.emit(f"Failed to switch to backend mode: {str(e)}")
            # Fallback to direct mode
            self._initialize_direct_assistant()
    
    def get_current_mode(self) -> str:
        """Get current assistant mode."""
        return self.current_mode
    
    def is_backend_available(self) -> bool:
        """Check if backend service is available."""
        if self.backend_assistant:
            return self.backend_assistant.is_connected()
        return False
    
    # Unified assistant interface methods
    
    def create_session(
        self, 
        title: str = "New Chat", 
        system_prompt: Optional[str] = None,
        model_id: Optional[str] = None,
        callback: Optional[Callable] = None
    ):
        """Create a new chat session."""
        if not self.active_assistant:
            self.error_occurred.emit("No active assistant available")
            return
        
        self.active_assistant.create_session(
            title=title,
            system_prompt=system_prompt,
            model_id=model_id,
            callback=callback
        )
    
    def load_session(self, session_id: str, callback: Optional[Callable] = None):
        """Load an existing session."""
        if not self.active_assistant:
            self.error_occurred.emit("No active assistant available")
            return
        
        self.active_assistant.load_session(session_id, callback)
    
    def list_sessions(self, callback: Optional[Callable] = None):
        """List all available sessions."""
        if not self.active_assistant:
            self.error_occurred.emit("No active assistant available")
            return
        
        self.active_assistant.list_sessions(callback)
    
    def delete_session(self, session_id: str, callback: Optional[Callable] = None):
        """Delete a session."""
        if not self.active_assistant:
            self.error_occurred.emit("No active assistant available")
            return
        
        self.active_assistant.delete_session(session_id, callback)
    
    def send_message(
        self,
        message: str,
        files: List[str] = None,
        use_thinking: bool = True,
        enable_search: bool = False,
        session_id: Optional[str] = None
    ):
        """Send a message to the current or specified session."""
        if not self.active_assistant:
            self.error_occurred.emit("No active assistant available")
            return
        
        # Use RAG if enabled and in backend mode
        use_rag = self.rag_enabled and self.current_mode == "backend"
        
        if hasattr(self.active_assistant, 'send_message'):
            if self.current_mode == "backend":
                self.active_assistant.send_message(
                    message=message,
                    files=files,
                    use_thinking=use_thinking,
                    enable_search=enable_search,
                    use_rag=use_rag,
                    session_id=session_id
                )
            else:
                # Direct assistant has different signature
                self.active_assistant.send_message(
                    message=message,
                    files=files or [],
                    use_thinking=use_thinking,
                    enable_search=enable_search
                )
        else:
            self.error_occurred.emit("Send message not supported by current assistant")
    
    def regenerate_last_response(self, session_id: Optional[str] = None):
        """Regenerate the last AI response."""
        if not self.active_assistant:
            self.error_occurred.emit("No active assistant available")
            return
        
        if hasattr(self.active_assistant, 'regenerate_last_response'):
            self.active_assistant.regenerate_last_response(session_id)
        else:
            self.error_occurred.emit("Regenerate response not supported by current assistant")
    
    def upload_file(self, file_path: str, callback: Optional[Callable] = None):
        """Upload a file for use in chat."""
        if not self.active_assistant:
            self.error_occurred.emit("No active assistant available")
            return
        
        if hasattr(self.active_assistant, 'upload_file'):
            self.active_assistant.upload_file(file_path, callback)
        else:
            self.error_occurred.emit("File upload not supported by current assistant")
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models."""
        if not self.active_assistant:
            return []
        
        if hasattr(self.active_assistant, 'get_available_models'):
            return self.active_assistant.get_available_models()
        return []
    
    def refresh_models(self):
        """Refresh the list of available models."""
        if self.active_assistant and hasattr(self.active_assistant, 'refresh_models'):
            self.active_assistant.refresh_models()
    
    # Backend-specific methods
    
    def set_rag_enabled(self, enabled: bool):
        """Enable or disable RAG functionality."""
        self.rag_enabled = enabled
        if enabled and self.current_mode != "backend":
            self.status_changed.emit("RAG requires backend mode. Please switch to backend service.")
    
    def set_rag_settings(self, settings: Dict[str, Any]):
        """Update RAG settings."""
        self.rag_settings.update(settings)
    
    def upload_document_to_knowledge_base(
        self, 
        file_path: str, 
        title: Optional[str] = None,
        callback: Optional[Callable] = None
    ):
        """Upload a document to the knowledge base (backend only)."""
        if self.current_mode != "backend":
            self.error_occurred.emit("Knowledge base features require backend mode")
            return
        
        if self.backend_assistant:
            self.backend_assistant.upload_document_to_knowledge_base(
                file_path=file_path,
                title=title,
                callback=callback
            )
    
    def search_knowledge_base(
        self, 
        query: str, 
        limit: int = 5,
        callback: Optional[Callable] = None
    ):
        """Search the knowledge base (backend only)."""
        if self.current_mode != "backend":
            self.error_occurred.emit("Knowledge base features require backend mode")
            return
        
        if self.backend_assistant:
            def search_callback(results):
                self.search_results_ready.emit(results)
                if callback:
                    callback(results)
            
            self.backend_assistant.search_knowledge_base(
                query=query,
                limit=limit,
                callback=search_callback
            )
    
    def get_knowledge_stats(self, callback: Optional[Callable] = None):
        """Get knowledge base statistics (backend only)."""
        if self.current_mode != "backend":
            return
        
        if self.backend_assistant:
            def stats_callback(stats):
                self.knowledge_stats_updated.emit(stats)
                if callback:
                    callback(stats)
            
            self.backend_assistant.get_knowledge_stats(stats_callback)
    
    def get_cache_stats(self, callback: Optional[Callable] = None):
        """Get cache statistics (backend only)."""
        if self.current_mode != "backend":
            return
        
        if self.backend_assistant:
            def cache_callback(stats):
                self.cache_stats_updated.emit(stats)
                if callback:
                    callback(stats)
            
            self.backend_assistant.get_cache_stats(cache_callback)
    
    def clear_cache(self, callback: Optional[Callable] = None):
        """Clear cache (backend only)."""
        if self.current_mode != "backend":
            self.error_occurred.emit("Cache features require backend mode")
            return
        
        if self.backend_assistant:
            self.backend_assistant.clear_cache(callback)
    
    def get_backend_status(self, callback: Optional[Callable] = None):
        """Get backend service status."""
        if self.current_mode != "backend":
            return
        
        if self.backend_assistant:
            self.backend_assistant.get_backend_status(callback)
    
    # Cleanup methods
    
    def cleanup(self):
        """Clean up resources for both assistants."""
        try:
            if self.direct_assistant and hasattr(self.direct_assistant, 'cleanup'):
                self.direct_assistant.cleanup()
            
            if self.backend_assistant and hasattr(self.backend_assistant, 'cleanup'):
                self.backend_assistant.cleanup()
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            self.cleanup()
        except Exception:
            pass  # Ignore errors during destruction