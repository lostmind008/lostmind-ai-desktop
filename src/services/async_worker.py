"""
Async worker threads for handling API calls in PyQt6 environment.

Provides Qt-compatible async task execution with proper signal handling
for non-blocking API communication with the backend service.
"""

import asyncio
import logging
import traceback
from typing import Any, Callable, Dict, Optional
from concurrent.futures import ThreadPoolExecutor

from PyQt6.QtCore import QObject, QThread, pyqtSignal, QTimer

logger = logging.getLogger(__name__)

class AsyncWorker(QObject):
    """Worker class for executing async operations in a separate thread."""
    
    # Qt signals for result communication
    finished = pyqtSignal(object)  # Success result
    error = pyqtSignal(str)        # Error message
    progress = pyqtSignal(dict)    # Progress updates (for streaming)
    
    def __init__(self, coro_func: Callable, *args, **kwargs):
        super().__init__()
        self.coro_func = coro_func
        self.args = args
        self.kwargs = kwargs
        self.loop = None
        
    def run(self):
        """Execute the async function in a new event loop."""
        try:
            # Create new event loop for this thread
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # Run the coroutine
            result = self.loop.run_until_complete(
                self.coro_func(*self.args, **self.kwargs)
            )
            
            self.finished.emit(result)
            
        except Exception as e:
            logger.error(f"Async worker error: {e}")
            logger.error(traceback.format_exc())
            self.error.emit(str(e))
            
        finally:
            if self.loop:
                self.loop.close()

class StreamingWorker(QObject):
    """Worker for handling streaming responses from the API."""
    
    chunk_received = pyqtSignal(dict)  # Individual streaming chunks
    stream_finished = pyqtSignal()     # Stream completion
    stream_error = pyqtSignal(str)     # Stream error
    
    def __init__(self, stream_coro: Callable, *args, **kwargs):
        super().__init__()
        self.stream_coro = stream_coro
        self.args = args
        self.kwargs = kwargs
        self.loop = None
        self.is_cancelled = False
        
    def run(self):
        """Execute the streaming coroutine."""
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # Run the streaming coroutine
            self.loop.run_until_complete(self._handle_stream())
            
        except Exception as e:
            if not self.is_cancelled:
                logger.error(f"Streaming worker error: {e}")
                self.stream_error.emit(str(e))
                
        finally:
            if self.loop:
                self.loop.close()
    
    async def _handle_stream(self):
        """Handle the async streaming response."""
        try:
            async for chunk in self.stream_coro(*self.args, **self.kwargs):
                if self.is_cancelled:
                    break
                self.chunk_received.emit(chunk)
            
            if not self.is_cancelled:
                self.stream_finished.emit()
                
        except Exception as e:
            if not self.is_cancelled:
                raise e
    
    def cancel(self):
        """Cancel the streaming operation."""
        self.is_cancelled = True

class ApiManager(QObject):
    """
    Manager for handling API operations with Qt signals.
    
    Provides a Qt-friendly interface for async API calls
    with proper thread management and signal handling.
    """
    
    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.active_workers = []
        
    def execute_async(
        self, 
        coro_func: Callable, 
        success_callback: Optional[Callable] = None,
        error_callback: Optional[Callable] = None,
        progress_callback: Optional[Callable] = None,
        *args, 
        **kwargs
    ) -> AsyncWorker:
        """
        Execute an async API operation with callbacks.
        
        Returns the worker object for additional signal connections.
        """
        # Create worker and thread
        worker = AsyncWorker(coro_func, *args, **kwargs)
        thread = QThread()
        
        # Move worker to thread
        worker.moveToThread(thread)
        
        # Connect signals
        if success_callback:
            worker.finished.connect(success_callback)
        if error_callback:
            worker.error.connect(error_callback)
        if progress_callback:
            worker.progress.connect(progress_callback)
        
        # Connect thread signals
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.error.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        
        # Clean up when done
        def cleanup():
            if worker in self.active_workers:
                self.active_workers.remove(worker)
        
        worker.finished.connect(cleanup)
        worker.error.connect(cleanup)
        
        # Track and start
        self.active_workers.append(worker)
        thread.start()
        
        return worker
    
    def execute_streaming(
        self,
        stream_coro: Callable,
        chunk_callback: Optional[Callable] = None,
        finished_callback: Optional[Callable] = None,
        error_callback: Optional[Callable] = None,
        *args,
        **kwargs
    ) -> StreamingWorker:
        """Execute a streaming API operation."""
        # Create worker and thread
        worker = StreamingWorker(stream_coro, *args, **kwargs)
        thread = QThread()
        
        # Move worker to thread
        worker.moveToThread(thread)
        
        # Connect signals
        if chunk_callback:
            worker.chunk_received.connect(chunk_callback)
        if finished_callback:
            worker.stream_finished.connect(finished_callback)
        if error_callback:
            worker.stream_error.connect(error_callback)
        
        # Connect thread signals
        thread.started.connect(worker.run)
        worker.stream_finished.connect(thread.quit)
        worker.stream_error.connect(thread.quit)
        worker.stream_finished.connect(worker.deleteLater)
        worker.stream_error.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        
        # Clean up when done
        def cleanup():
            if worker in self.active_workers:
                self.active_workers.remove(worker)
        
        worker.stream_finished.connect(cleanup)
        worker.stream_error.connect(cleanup)
        
        # Track and start
        self.active_workers.append(worker)
        thread.start()
        
        return worker
    
    # Convenience methods for common API operations
    
    def create_session(self, title: str, success_callback=None, error_callback=None):
        """Create a new chat session."""
        return self.execute_async(
            self.api_client.create_session,
            success_callback=success_callback,
            error_callback=error_callback,
            title=title
        )
    
    def send_message(
        self, 
        session_id: str, 
        content: str, 
        files=None,
        success_callback=None, 
        error_callback=None,
        use_thinking: bool = True,
        enable_search: bool = False
    ):
        """Send a message to a session."""
        return self.execute_async(
            self.api_client.send_message,
            success_callback=success_callback,
            error_callback=error_callback,
            session_id=session_id,
            content=content,
            files=files or [],
            use_thinking=use_thinking,
            enable_search=enable_search
        )
    
    def send_rag_message(
        self,
        session_id: str,
        content: str,
        success_callback=None,
        error_callback=None,
        use_rag: bool = True,
        rag_limit: int = 3
    ):
        """Send a RAG-enhanced message."""
        return self.execute_async(
            self.api_client.send_rag_message,
            success_callback=success_callback,
            error_callback=error_callback,
            session_id=session_id,
            content=content,
            use_rag=use_rag,
            rag_limit=rag_limit
        )
    
    def list_sessions(self, success_callback=None, error_callback=None):
        """List all chat sessions."""
        return self.execute_async(
            self.api_client.list_sessions,
            success_callback=success_callback,
            error_callback=error_callback
        )
    
    def get_session(self, session_id: str, success_callback=None, error_callback=None):
        """Get session details."""
        return self.execute_async(
            self.api_client.get_session,
            success_callback=success_callback,
            error_callback=error_callback,
            session_id=session_id
        )
    
    def upload_document(
        self, 
        file_path: str, 
        title=None, 
        success_callback=None, 
        error_callback=None
    ):
        """Upload a document to the knowledge base."""
        return self.execute_async(
            self.api_client.upload_document,
            success_callback=success_callback,
            error_callback=error_callback,
            file_path=file_path,
            title=title
        )
    
    def search_knowledge(
        self, 
        query: str, 
        success_callback=None, 
        error_callback=None,
        limit: int = 5
    ):
        """Search the knowledge base."""
        return self.execute_async(
            self.api_client.search_knowledge,
            success_callback=success_callback,
            error_callback=error_callback,
            query=query,
            limit=limit
        )
    
    def check_health(self, success_callback=None, error_callback=None):
        """Check backend health."""
        return self.execute_async(
            self.api_client.check_health,
            success_callback=success_callback,
            error_callback=error_callback
        )
    
    def cleanup(self):
        """Clean up resources and cancel active operations."""
        for worker in self.active_workers[:]:  # Copy list to avoid modification during iteration
            if hasattr(worker, 'cancel'):
                worker.cancel()
        
        self.active_workers.clear()
        self.executor.shutdown(wait=False)

# Connection monitor for backend availability
class ConnectionMonitor(QObject):
    """Monitors connection to the backend service."""
    
    connection_status_changed = pyqtSignal(bool)  # True = connected, False = disconnected
    connection_error = pyqtSignal(str)
    
    def __init__(self, api_manager: ApiManager, check_interval: int = 30000):
        super().__init__()
        self.api_manager = api_manager
        self.timer = QTimer()
        self.timer.timeout.connect(self._check_connection)
        self.timer.setInterval(check_interval)  # Check every 30 seconds
        self.is_connected = False
        
    def start_monitoring(self):
        """Start monitoring the connection."""
        self._check_connection()  # Initial check
        self.timer.start()
        
    def stop_monitoring(self):
        """Stop monitoring the connection."""
        self.timer.stop()
        
    def _check_connection(self):
        """Check if backend is available."""
        def on_success(result):
            if not self.is_connected:
                self.is_connected = True
                self.connection_status_changed.emit(True)
                
        def on_error(error):
            if self.is_connected:
                self.is_connected = False
                self.connection_status_changed.emit(False)
                self.connection_error.emit(error)
        
        self.api_manager.check_health(
            success_callback=on_success,
            error_callback=on_error
        )