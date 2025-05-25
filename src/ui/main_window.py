#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main Window for LostMind AI Gemini Chat Assistant

This module implements the main application window and UI components
for the Gemini Chat Assistant using PyQt6.
"""

import os
import sys
import logging
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTabWidget, QLabel, QPushButton, QComboBox,
    QSlider, QLineEdit, QTextEdit, QScrollArea, QMessageBox,
    QFileDialog, QDialog, QCheckBox, QGroupBox, QRadioButton,
    QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSignal, QThread, QUrl
from PyQt6.QtGui import QIcon, QPixmap, QColor, QFont, QAction, QTextCursor, QTextCharFormat, QTextBlockFormat, QTextListFormat, QTextTableFormat, QTextOption, QDesktopServices

from ui.chat_display import ChatDisplay
from ui.controls_panel import ControlsPanel
from ui.settings_panel import SettingsPanel
from ui.file_panel import FilePanel
from ui.model_panel import ModelPanel
from ui.status_bar import StatusBarManager

from config_manager import ConfigManager
from model_registry import ModelRegistry
from gemini_assistant import GeminiAssistant

class MainWindow(QMainWindow):
    """
    Main application window for the Gemini Chat Assistant.
    """
    
    def __init__(self, config: ConfigManager):
        """
        Initialize the main window.
        
        Args:
            config (ConfigManager): Application configuration manager.
        """
        super().__init__()
        
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Initialize the model registry
        self.model_registry = ModelRegistry(config)
        if not self.model_registry.initialize_client():
            QMessageBox.critical(
                self,
                "Initialization Error",
                "Failed to initialize GenAI client. Please check your authentication and network connection."
            )
        
        # Try to discover available models
        self.model_registry.discover_models()
        
        # Initialize the Gemini assistant
        self.assistant = GeminiAssistant(config, self.model_registry)
        self.assistant.initialize()
        
        # Set up the UI
        self.init_ui()
        
        # Connect signals and slots
        self.connect_signals()
        
        # Set window properties
        self.setup_window()
        
        # Set up status bar
        self.status_manager = StatusBarManager(self.statusBar())
        
        # Show initial message
        self.status_manager.show_message("Welcome to LostMind AI Gemini Chat Assistant")
    
    def init_ui(self):
        """Set up the user interface components."""
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create splitter for adjustable panels
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter)
        
        # Chat area (takes 70% of space)
        self.chat_area = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_area)
        self.chat_layout.setContentsMargins(10, 10, 10, 10)
        
        # Chat display
        self.chat_display = ChatDisplay()
        self.chat_layout.addWidget(self.chat_display)
        
        # Controls panel at the bottom of chat area
        self.controls_panel = ControlsPanel(self.config, self.assistant)
        self.chat_layout.addWidget(self.controls_panel)
        
        # Right sidebar with panels (takes 30% of space)
        self.sidebar = QWidget()
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(0, 0, 0, 0)
        
        # Tabs for different panels
        self.tabs = QTabWidget()
        self.sidebar_layout.addWidget(self.tabs)
        
        # Settings panel
        self.settings_panel = SettingsPanel(self.config, self.model_registry, self.assistant)
        self.tabs.addTab(self.settings_panel, "Settings")
        
        # File panel
        self.file_panel = FilePanel(self.config, self.assistant)
        self.tabs.addTab(self.file_panel, "Files")
        
        # Model info panel
        self.model_panel = ModelPanel(self.config, self.model_registry, self.assistant)
        self.tabs.addTab(self.model_panel, "Model Info")
        
        # Add widgets to splitter
        self.splitter.addWidget(self.chat_area)
        self.splitter.addWidget(self.sidebar)
        
        # Set initial sizes (70/30 split)
        self.splitter.setSizes([700, 300])
    
    def connect_signals(self):
        """Connect signals and slots."""
        # Connect settings panel signals
        self.settings_panel.model_changed.connect(self.on_model_changed)
        self.settings_panel.chat_started.connect(self.on_chat_started)
        self.settings_panel.settings_updated.connect(self.on_settings_updated)
        
        # Connect controls panel signals
        self.controls_panel.message_sent.connect(self.on_message_sent)
        self.controls_panel.clear_requested.connect(self.on_clear_requested)
        self.controls_panel.export_requested.connect(self.on_export_requested)
        
        # Connect file panel signals
        self.file_panel.file_uploaded.connect(self.on_file_uploaded)
        self.file_panel.files_cleared.connect(self.on_files_cleared)
    
    def setup_window(self):
        """Set up window properties."""
        # Set window title
        self.setWindowTitle(self.config.get_value(['ui', 'window_title'], "LostMind AI - Gemini Chat Assistant"))
        
        # Set window size
        window_size = self.config.get_value(['ui', 'window_size'], [1024, 768])
        self.resize(window_size[0], window_size[1])
        
        # Set window minimum size
        self.setMinimumSize(800, 600)
        
        # Create and set up menu bar
        self.create_menus()
    
    def create_menus(self):
        """Create application menus."""
        # File menu
        file_menu = self.menuBar().addMenu("&File")
        
        # New chat action
        new_chat_action = QAction("New Chat", self)
        new_chat_action.setShortcut("Ctrl+N")
        new_chat_action.triggered.connect(self.on_new_chat)
        file_menu.addAction(new_chat_action)
        
        # Export chat action
        export_chat_action = QAction("Export Chat...", self)
        export_chat_action.setShortcut("Ctrl+E")
        export_chat_action.triggered.connect(self.on_export_requested)
        file_menu.addAction(export_chat_action)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = self.menuBar().addMenu("&Edit")
        
        # Clear chat action
        clear_chat_action = QAction("Clear Chat", self)
        clear_chat_action.triggered.connect(self.on_clear_requested)
        edit_menu.addAction(clear_chat_action)
        
        # Settings action
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.show_settings_tab)
        edit_menu.addAction(settings_action)
        
        # View menu
        view_menu = self.menuBar().addMenu("&View")
        
        # Toggle sidebar action
        toggle_sidebar_action = QAction("Toggle Sidebar", self)
        toggle_sidebar_action.setShortcut("Ctrl+B")
        toggle_sidebar_action.triggered.connect(self.toggle_sidebar)
        view_menu.addAction(toggle_sidebar_action)
        
        # Help menu
        help_menu = self.menuBar().addMenu("&Help")
        
        # About action
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
    
    def on_model_changed(self, model_id: str):
        """
        Handle model change.
        
        Args:
            model_id (str): New model ID.
        """
        self.assistant.selected_model = model_id
        self.model_panel.update_model_info(model_id)
        self.status_manager.show_message(f"Model changed to: {model_id}")
    
    def on_chat_started(self):
        """Handle chat session start."""
        # Clear chat display
        self.chat_display.clear()
        
        # Start chat session
        success, error_message = self.assistant.start_chat()
        
        if success:
            # Add welcome message
            model_display_name = self.model_registry.get_model_by_id(
                self.assistant.selected_model
            ).get('display_name', self.assistant.selected_model)
            
            welcome_message = "Ready to assist you. Type your message below to begin."
            self.chat_display.add_system_message(welcome_message)
            
            # Update UI
            self.controls_panel.enable_controls()
            self.status_manager.show_message("Chat session started")
            
            # If there was a warning, show it
            if error_message:
                self.status_manager.show_warning(error_message)
        else:
            # Show error
            self.chat_display.add_error_message(f"Failed to start chat: {error_message}")
            self.status_manager.show_error("Failed to start chat session")
    
    def on_settings_updated(self):
        """Handle settings updates."""
        # Update window title
        self.setWindowTitle(self.config.get_value(['ui', 'window_title'], "LostMind AI - Gemini Chat Assistant"))
        
        # Update other settings as needed
        self.status_manager.show_message("Settings updated")
    
    def on_message_sent(self, message: str):
        """
        Handle message sent.
        
        Args:
            message (str): Message text.
        """
        # Add user message to display
        self.chat_display.add_user_message(message)
        
        # Disable controls during processing
        self.controls_panel.set_controls_enabled(False)
        self.status_manager.show_busy("Processing message...")
        
        # Send message to assistant
        def streaming_callback(chunk: str):
            self.chat_display.append_to_last_message(chunk)
            QApplication.processEvents()  # Ensure UI updates
        
        # Use a single-shot timer to allow UI to update before processing
        QTimer.singleShot(100, lambda: self._process_message(message, streaming_callback))
    
    def _process_message(self, message: str, streaming_callback: Callable[[str], None]):
        """
        Process a message with the assistant.
        
        Args:
            message (str): Message text.
            streaming_callback (Callable[[str], None]): Callback for streaming chunks.
        """
        try:
            # Get currently selected files
            include_files = self.file_panel.get_include_files()
            
            # Create an empty AI message bubble for streaming mode
            if self.assistant.streaming:
                # Add empty AI message that will be filled by streaming
                empty_bubble = self.chat_display.add_ai_message("")
            
            # Normal processing for all messages
            success, error, response = self.assistant.send_message(
                message,
                include_files=include_files,
                streaming_callback=streaming_callback if self.assistant.streaming else None
            )
            
            if success:
                # For non-streaming mode, create the message bubble with the complete response
                if not self.assistant.streaming:
                    message_bubble = self.chat_display.add_ai_message(response.content)
                # else: for streaming mode, we already created the empty bubble before the API call
                
                # Update the search indicator if search was used
                if response and response.used_search:
                    self.chat_display.set_last_message_search_used(True)
                
                # Show response time in status bar
                self.status_manager.show_message(f"Response received in {response.response_time:.2f} seconds")
            else:
                # Show error
                self.chat_display.add_error_message(f"Error: {error}")
                self.status_manager.show_error(f"Error: {error}")
                
        except Exception as e:
            # Handle unexpected exceptions
            error_message = f"Unexpected error: {str(e)}"
            self.chat_display.add_error_message(error_message)
            self.status_manager.show_error(error_message)
            self.logger.exception("Error processing message")
            
        finally:
            # Re-enable controls
            self.controls_panel.set_controls_enabled(True)
    
    def on_clear_requested(self):
        """Handle clear chat request."""
        reply = QMessageBox.question(
            self,
            "Clear Chat",
            "Are you sure you want to clear the chat history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Clear chat display
            self.chat_display.clear()
            
            # Start new chat session
            success, error_message = self.assistant.start_chat()
            
            if success:
                # Add welcome message
                welcome_message = "Chat history cleared. You can continue chatting."
                self.chat_display.add_system_message(welcome_message)
                self.status_manager.show_message("Chat history cleared")
            else:
                # Show error
                self.chat_display.add_error_message(f"Failed to restart chat: {error_message}")
                self.status_manager.show_error("Failed to restart chat session")
    

    def on_export_requested(self):
        """Handle export chat request."""
        # Ask for export format and path
        options = QFileDialog.Option.DontUseNativeDialog
        
        filters = "HTML Files (*.html);;Text Files (*.txt)"
        default_filter = "HTML Files (*.html)"
        
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Chat",
            "",
            filters,
            default_filter,
            options
        )
        
        if not file_path:
            return
        
        # Determine export format
        is_html = selected_filter.startswith("HTML")
        
        # Add extension if not provided
        if not file_path.endswith(".html") and not file_path.endswith(".txt"):
            file_path += ".html" if is_html else ".txt"
        
        # Export chat
        if is_html:
            success, error = self.assistant.export_chat_to_html(file_path)
        else:
            success, error = self.assistant.export_chat_to_text(file_path)
        
        if success:
            self.status_manager.show_message(f"Chat exported to {file_path}")
            
            # Ask if user wants to open the file
            reply = QMessageBox.question(
                self,
                "Export Complete",
                f"Chat exported to {file_path}. Open file now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Open file with default application using QDesktopServices
                QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
                
        else:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export chat: {error}"
            )
            self.status_manager.show_error(f"Export failed: {error}")

    
    def on_file_uploaded(self, file_info: Dict[str, Any]):
        """
        Handle file upload.
        
        Args:
            file_info (Dict[str, Any]): Information about the uploaded file.
        """
        file_name = file_info.get("display_name", "Unknown file")
        self.status_manager.show_message(f"File uploaded: {file_name}")
    
    def on_files_cleared(self):
        """Handle files cleared."""
        self.status_manager.show_message("All files cleared")
    
    def on_new_chat(self):
        """Handle new chat request."""
        reply = QMessageBox.question(
            self,
            "New Chat",
            "Start a new chat? This will clear the current chat history.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Show settings tab to configure new chat
            self.show_settings_tab()
            self.settings_panel.focus_start_button()
    
    def show_settings_tab(self):
        """Show the settings tab."""
        self.tabs.setCurrentWidget(self.settings_panel)
    
    def toggle_sidebar(self):
        """Toggle the sidebar visibility."""
        if self.sidebar.isVisible():
            self.sidebar.hide()
        else:
            self.sidebar.show()
    
    def show_about_dialog(self):
        """Show the about dialog."""
        QMessageBox.about(
            self,
            "About LostMind AI",
            "<h3>LostMind AI - Gemini Chat Assistant</h3>"
            "<p>Version 1.0.0</p>"
            "<p>© 2025 Sumit Mondal</p>"
            "<p>A modern PyQt6-based application for interacting with "
            "Google's Gemini models via Vertex AI.</p>"
        )
    
    def closeEvent(self, event):
        """
        Handle window close event.
        
        Args:
            event: Close event.
        """
        reply = QMessageBox.question(
            self,
            "Exit",
            "Are you sure you want to exit?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Save settings
            self.config.save_config()
            event.accept()
        else:
            event.ignore()
