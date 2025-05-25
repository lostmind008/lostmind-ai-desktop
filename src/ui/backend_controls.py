"""
Backend controls panel for switching between direct API and backend service modes.

Provides UI controls for backend connection, mode selection, and backend-specific features
like knowledge management and caching.
"""

import logging
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QCheckBox, QGroupBox, QLineEdit, QTextEdit,
    QProgressBar, QFrame, QMessageBox, QTabWidget, QListWidget,
    QListWidgetItem, QSplitter, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette

logger = logging.getLogger(__name__)

class BackendControlsPanel(QWidget):
    """
    Controls panel for backend service features and configuration.
    """
    
    # Signals
    mode_changed = pyqtSignal(str)  # "direct" or "backend"
    backend_url_changed = pyqtSignal(str)
    knowledge_search_requested = pyqtSignal(str)
    document_upload_requested = pyqtSignal(str)
    cache_action_requested = pyqtSignal(str)  # "clear", "stats"
    rag_mode_toggled = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_mode = "direct"
        self.backend_status = "disconnected"
        self.knowledge_stats = {}
        self.cache_stats = {}
        
        self._setup_ui()
        self._setup_connections()
        
        # Status update timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status_display)
        self.status_timer.start(5000)  # Update every 5 seconds
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Mode Selection
        mode_group = QGroupBox("Connection Mode")
        mode_layout = QVBoxLayout(mode_group)
        
        # Mode selection combo
        mode_layout.addWidget(QLabel("Select Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Direct API", "Backend Service"])
        self.mode_combo.setCurrentText("Direct API")
        mode_layout.addWidget(self.mode_combo)
        
        # Backend URL configuration
        self.backend_url_widget = QWidget()
        backend_url_layout = QHBoxLayout(self.backend_url_widget)
        backend_url_layout.addWidget(QLabel("Backend URL:"))
        self.backend_url_input = QLineEdit("http://localhost:8000")
        backend_url_layout.addWidget(self.backend_url_input)
        self.connect_btn = QPushButton("Connect")
        backend_url_layout.addWidget(self.connect_btn)
        mode_layout.addWidget(self.backend_url_widget)
        
        # Connection status
        self.status_label = QLabel("Status: Not connected")
        self.status_label.setStyleSheet("QLabel { color: #ff6b6b; font-weight: bold; }")
        mode_layout.addWidget(self.status_label)
        
        layout.addWidget(mode_group)
        
        # Backend Features (only visible when backend mode is selected)
        self.backend_features_widget = QWidget()
        self._setup_backend_features()
        layout.addWidget(self.backend_features_widget)
        
        # Hide backend features initially
        self.backend_features_widget.setVisible(False)
        self.backend_url_widget.setVisible(False)
    
    def _setup_backend_features(self):
        """Set up backend-specific features UI."""
        layout = QVBoxLayout(self.backend_features_widget)
        
        # Create tabbed interface for features
        features_tabs = QTabWidget()
        
        # Knowledge Management Tab
        knowledge_tab = self._create_knowledge_tab()
        features_tabs.addTab(knowledge_tab, "Knowledge Base")
        
        # Cache Management Tab
        cache_tab = self._create_cache_tab()
        features_tabs.addTab(cache_tab, "Cache")
        
        # RAG Settings Tab
        rag_tab = self._create_rag_tab()
        features_tabs.addTab(rag_tab, "RAG Settings")
        
        layout.addWidget(features_tabs)
    
    def _create_knowledge_tab(self):
        """Create knowledge management tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Knowledge base stats
        stats_group = QGroupBox("Knowledge Base Statistics")
        stats_layout = QVBoxLayout(stats_group)
        
        self.kb_stats_label = QLabel("Documents: 0\\nChunks: 0\\nTypes: None")
        stats_layout.addWidget(self.kb_stats_label)
        
        refresh_stats_btn = QPushButton("Refresh Stats")
        refresh_stats_btn.clicked.connect(lambda: self.cache_action_requested.emit("kb_stats"))
        stats_layout.addWidget(refresh_stats_btn)
        
        layout.addWidget(stats_group)
        
        # Document upload
        upload_group = QGroupBox("Document Management")
        upload_layout = QVBoxLayout(upload_group)
        
        upload_btn = QPushButton("Upload Document to Knowledge Base")
        upload_btn.clicked.connect(self._handle_document_upload)
        upload_layout.addWidget(upload_btn)
        
        layout.addWidget(upload_group)
        
        # Knowledge search
        search_group = QGroupBox("Knowledge Search")
        search_layout = QVBoxLayout(search_group)
        
        search_layout.addWidget(QLabel("Search knowledge base:"))
        
        search_input_layout = QHBoxLayout()
        self.knowledge_search_input = QLineEdit()
        self.knowledge_search_input.setPlaceholderText("Enter search query...")
        search_input_layout.addWidget(self.knowledge_search_input)
        
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self._handle_knowledge_search)
        search_input_layout.addWidget(search_btn)
        
        search_layout.addLayout(search_input_layout)
        
        # Search results
        self.search_results_list = QListWidget()
        self.search_results_list.setMaximumHeight(150)
        search_layout.addWidget(QLabel("Search Results:"))
        search_layout.addWidget(self.search_results_list)
        
        layout.addWidget(search_group)
        
        return tab
    
    def _create_cache_tab(self):
        """Create cache management tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Cache statistics
        stats_group = QGroupBox("Cache Statistics")
        stats_layout = QVBoxLayout(stats_group)
        
        self.cache_stats_label = QLabel("Status: Unknown")
        stats_layout.addWidget(self.cache_stats_label)
        
        refresh_cache_btn = QPushButton("Refresh Cache Stats")
        refresh_cache_btn.clicked.connect(lambda: self.cache_action_requested.emit("stats"))
        stats_layout.addWidget(refresh_cache_btn)
        
        layout.addWidget(stats_group)
        
        # Cache management
        management_group = QGroupBox("Cache Management")
        management_layout = QVBoxLayout(management_group)
        
        clear_cache_btn = QPushButton("Clear Cache")
        clear_cache_btn.clicked.connect(lambda: self.cache_action_requested.emit("clear"))
        clear_cache_btn.setStyleSheet("QPushButton { background-color: #ff6b6b; color: white; }")
        management_layout.addWidget(clear_cache_btn)
        
        layout.addWidget(management_group)
        
        return tab
    
    def _create_rag_tab(self):
        """Create RAG settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # RAG Configuration
        rag_group = QGroupBox("RAG (Retrieval-Augmented Generation)")
        rag_layout = QVBoxLayout(rag_group)
        
        self.rag_enabled_checkbox = QCheckBox("Enable RAG for messages")
        self.rag_enabled_checkbox.setToolTip("When enabled, messages will be enhanced with relevant context from the knowledge base")
        rag_layout.addWidget(self.rag_enabled_checkbox)
        
        # RAG parameters
        params_widget = QWidget()
        params_layout = QVBoxLayout(params_widget)
        
        # Number of context chunks
        params_layout.addWidget(QLabel("Number of context chunks:"))
        self.rag_limit_combo = QComboBox()
        self.rag_limit_combo.addItems(["1", "3", "5", "7", "10"])
        self.rag_limit_combo.setCurrentText("3")
        params_layout.addWidget(self.rag_limit_combo)
        
        # Similarity threshold
        params_layout.addWidget(QLabel("Similarity threshold:"))
        self.rag_threshold_combo = QComboBox()
        self.rag_threshold_combo.addItems(["0.5", "0.6", "0.7", "0.8", "0.9"])
        self.rag_threshold_combo.setCurrentText("0.7")
        params_layout.addWidget(self.rag_threshold_combo)
        
        rag_layout.addWidget(params_widget)
        layout.addWidget(rag_group)
        
        return tab
    
    def _setup_connections(self):
        """Set up signal connections."""
        self.mode_combo.currentTextChanged.connect(self._handle_mode_change)
        self.backend_url_input.textChanged.connect(self._handle_url_change)
        self.connect_btn.clicked.connect(self._handle_connect_request)
        self.rag_enabled_checkbox.toggled.connect(self.rag_mode_toggled.emit)
    
    def _handle_mode_change(self, mode_text: str):
        """Handle mode selection change."""
        if mode_text == "Backend Service":
            self.current_mode = "backend"
            self.backend_features_widget.setVisible(True)
            self.backend_url_widget.setVisible(True)
        else:
            self.current_mode = "direct"
            self.backend_features_widget.setVisible(False)
            self.backend_url_widget.setVisible(False)
        
        self.mode_changed.emit(self.current_mode)
    
    def _handle_url_change(self, url: str):
        """Handle backend URL change."""
        self.backend_url_changed.emit(url)
    
    def _handle_connect_request(self):
        """Handle connect button click."""
        self.cache_action_requested.emit("connect")
    
    def _handle_knowledge_search(self):
        """Handle knowledge search request."""
        query = self.knowledge_search_input.text().strip()
        if query:
            self.knowledge_search_requested.emit(query)
    
    def _handle_document_upload(self):
        """Handle document upload request."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Document to Upload",
            "",
            "All Files (*.*);;"
            "Text Files (*.txt *.md);;PDF Files (*.pdf);;"
            "Word Documents (*.docx *.doc);;"
            "Code Files (*.py *.js *.cpp *.java *.html *.css)"
        )
        
        if file_path:
            self.document_upload_requested.emit(file_path)
    
    def _update_status_display(self):
        """Update the status display."""
        # This will be called by the main window when status changes
        pass
    
    # Public methods for updating the UI
    
    def set_connection_status(self, connected: bool, message: str = ""):
        """Update connection status display."""
        if connected:
            self.backend_status = "connected"
            self.status_label.setText(f"Status: Connected {message}")
            self.status_label.setStyleSheet("QLabel { color: #51cf66; font-weight: bold; }")
            self.connect_btn.setText("Disconnect")
        else:
            self.backend_status = "disconnected"
            self.status_label.setText(f"Status: Disconnected {message}")
            self.status_label.setStyleSheet("QLabel { color: #ff6b6b; font-weight: bold; }")
            self.connect_btn.setText("Connect")
    
    def update_knowledge_stats(self, stats: Dict[str, Any]):
        """Update knowledge base statistics display."""
        self.knowledge_stats = stats
        
        if stats:
            text = f"Documents: {stats.get('unique_documents', 0)}\\n"
            text += f"Chunks: {stats.get('total_chunks', 0)}\\n"
            
            doc_types = stats.get('document_types', {})
            if doc_types:
                types_str = ", ".join([f"{k}: {v}" for k, v in doc_types.items()])
                text += f"Types: {types_str}"
            else:
                text += "Types: None"
        else:
            text = "Documents: 0\\nChunks: 0\\nTypes: None"
        
        self.kb_stats_label.setText(text)
    
    def update_cache_stats(self, stats: Dict[str, Any]):
        """Update cache statistics display."""
        self.cache_stats = stats
        
        if stats.get("status") == "connected":
            text = f"Redis Status: Connected\\n"
            text += f"Sessions: {stats.get('total_sessions', 0)}\\n"
            text += f"Messages: {stats.get('total_message_lists', 0)}\\n"
            text += f"Cached Responses: {stats.get('cached_responses', 0)}\\n"
            text += f"Memory: {stats.get('used_memory_human', 'Unknown')}"
        else:
            text = f"Cache Status: {stats.get('status', 'Unknown')}\\n"
            if stats.get('error'):
                text += f"Error: {stats['error']}"
        
        self.cache_stats_label.setText(text)
    
    def display_search_results(self, results: List[Dict[str, Any]]):
        """Display knowledge search results."""
        self.search_results_list.clear()
        
        for chunk in results:
            title = chunk.get("document_title", "Unknown Document")
            content_preview = chunk.get("content", "")[:100] + "..." if len(chunk.get("content", "")) > 100 else chunk.get("content", "")
            score = chunk.get("similarity_score", 0.0)
            
            item_text = f"{title} (Score: {score:.2f})\\n{content_preview}"
            item = QListWidgetItem(item_text)
            item.setToolTip(chunk.get("content", ""))
            self.search_results_list.addItem(item)
    
    def get_rag_settings(self) -> Dict[str, Any]:
        """Get current RAG settings."""
        return {
            "enabled": self.rag_enabled_checkbox.isChecked(),
            "limit": int(self.rag_limit_combo.currentText()),
            "threshold": float(self.rag_threshold_combo.currentText())
        }
    
    def get_current_mode(self) -> str:
        """Get current connection mode."""
        return self.current_mode
    
    def get_backend_url(self) -> str:
        """Get current backend URL."""
        return self.backend_url_input.text().strip()