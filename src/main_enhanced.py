#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced Main Entry Point for LostMind AI Gemini Chat Assistant

This module provides the enhanced main entry point that supports both
direct API and backend service modes through the assistant adapter.
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import QApplication, QMessageBox, QSplashScreen
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtCore import Qt, QTimer

from config_manager import ConfigManager
from assistant_adapter import AssistantAdapter
from ui.main_window import MainWindow
from ui.backend_controls import BackendControlsPanel
from utils.error_logger import ErrorLogger

def setup_logging(log_dir="logs", level=logging.INFO):
    """
    Set up logging configuration.
    
    Args:
        log_dir (str, optional): Directory for log files. Defaults to "logs".
        level (int, optional): Logging level. Defaults to logging.INFO.
    
    Returns:
        logging.Logger: Root logger.
    """
    # Ensure log directory exists
    os.makedirs(log_dir, exist_ok=True)
    
    # Create log file path with date
    log_file = os.path.join(
        log_dir, 
        f"lostmind_ai_{datetime.now().strftime('%Y%m%d')}.log"
    )
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("="*50)
    logger.info("LostMind AI Gemini Chat Assistant (Enhanced) - Starting")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Python version: {sys.version}")
    logger.info("="*50)
    
    return logger

class EnhancedMainWindow(MainWindow):
    """
    Enhanced main window with backend service support.
    
    Extends the original MainWindow to include backend controls
    and assistant adapter integration.
    """
    
    def __init__(self, config: ConfigManager):
        """Initialize enhanced main window."""
        # Initialize assistant adapter instead of direct GeminiAssistant
        self.assistant_adapter = AssistantAdapter(config)
        
        # Initialize parent with config
        super().__init__(config)
        
        # Add backend controls
        self._setup_backend_integration()
        
    def _setup_backend_integration(self):
        """Set up backend service integration."""
        try:
            # Create backend controls panel
            self.backend_controls = BackendControlsPanel()
            
            # Add backend controls to the UI (you might want to add this as a tab or side panel)
            # For now, we'll add it as a new tab in the main interface
            if hasattr(self, 'tab_widget'):
                self.tab_widget.addTab(self.backend_controls, "Backend")
            
            # Connect backend control signals
            self.backend_controls.mode_changed.connect(self._handle_mode_change)
            self.backend_controls.backend_url_changed.connect(self._handle_backend_url_change)
            self.backend_controls.knowledge_search_requested.connect(self._handle_knowledge_search)
            self.backend_controls.document_upload_requested.connect(self._handle_document_upload)
            self.backend_controls.cache_action_requested.connect(self._handle_cache_action)
            self.backend_controls.rag_mode_toggled.connect(self._handle_rag_toggle)
            
            # Connect assistant adapter signals
            self.assistant_adapter.response_ready.connect(self._handle_response_ready)
            self.assistant_adapter.error_occurred.connect(self._handle_error)
            self.assistant_adapter.thinking_update.connect(self._handle_thinking_update)
            self.assistant_adapter.status_changed.connect(self._handle_status_change)
            self.assistant_adapter.file_uploaded.connect(self._handle_file_uploaded)
            self.assistant_adapter.backend_connection_status.connect(self._handle_backend_connection)
            self.assistant_adapter.knowledge_stats_updated.connect(self._handle_knowledge_stats)
            self.assistant_adapter.cache_stats_updated.connect(self._handle_cache_stats)
            self.assistant_adapter.search_results_ready.connect(self._handle_search_results)
            
            logging.info("Backend integration setup completed")
            
        except Exception as e:
            logging.error(f"Failed to setup backend integration: {e}")
    
    def _handle_mode_change(self, mode: str):
        """Handle assistant mode change."""
        try:
            if mode == "backend":
                backend_url = self.backend_controls.get_backend_url()
                self.assistant_adapter.switch_to_backend_mode(backend_url)
            else:
                self.assistant_adapter.switch_to_direct_mode()
            
            logging.info(f"Switched to {mode} mode")
            
        except Exception as e:
            logging.error(f"Failed to change mode to {mode}: {e}")
            self._show_error_message(f"Failed to switch to {mode} mode: {str(e)}")
    
    def _handle_backend_url_change(self, url: str):
        """Handle backend URL change."""
        # Update assistant adapter with new URL if in backend mode
        if self.assistant_adapter.get_current_mode() == "backend":
            self.assistant_adapter.switch_to_backend_mode(url)
    
    def _handle_knowledge_search(self, query: str):
        """Handle knowledge base search request."""
        self.assistant_adapter.search_knowledge_base(query)
    
    def _handle_document_upload(self, file_path: str):
        """Handle document upload to knowledge base."""
        def upload_callback(doc_id):
            if doc_id:
                self._show_info_message(f"Document uploaded successfully: {doc_id}")
                # Refresh knowledge stats
                self.assistant_adapter.get_knowledge_stats()
            else:
                self._show_error_message("Failed to upload document")
        
        self.assistant_adapter.upload_document_to_knowledge_base(
            file_path=file_path,
            callback=upload_callback
        )
    
    def _handle_cache_action(self, action: str):
        """Handle cache management actions."""
        if action == "stats":
            self.assistant_adapter.get_cache_stats()
        elif action == "clear":
            def clear_callback(success):
                if success:
                    self._show_info_message("Cache cleared successfully")
                    self.assistant_adapter.get_cache_stats()  # Refresh stats
                else:
                    self._show_error_message("Failed to clear cache")
            
            self.assistant_adapter.clear_cache(clear_callback)
        elif action == "kb_stats":
            self.assistant_adapter.get_knowledge_stats()
        elif action == "connect":
            # Handle backend connection test
            def status_callback(status):
                if status.get("status") == "healthy":
                    self.backend_controls.set_connection_status(True, "- Service healthy")
                else:
                    self.backend_controls.set_connection_status(False, f"- {status.get('error', 'Unknown error')}")
            
            self.assistant_adapter.get_backend_status(status_callback)
    
    def _handle_rag_toggle(self, enabled: bool):
        """Handle RAG mode toggle."""
        self.assistant_adapter.set_rag_enabled(enabled)
        
        # Update RAG settings from controls
        rag_settings = self.backend_controls.get_rag_settings()
        self.assistant_adapter.set_rag_settings(rag_settings)
    
    def _handle_backend_connection(self, connected: bool):
        """Handle backend connection status change."""
        status_msg = "Connected" if connected else "Disconnected"
        self.backend_controls.set_connection_status(connected, f"- {status_msg}")
    
    def _handle_knowledge_stats(self, stats: dict):
        """Handle knowledge base statistics update."""
        self.backend_controls.update_knowledge_stats(stats)
    
    def _handle_cache_stats(self, stats: dict):
        """Handle cache statistics update."""
        self.backend_controls.update_cache_stats(stats)
    
    def _handle_search_results(self, results: list):
        """Handle knowledge search results."""
        self.backend_controls.display_search_results(results)
    
    # Override parent methods to use assistant adapter
    
    def _handle_response_ready(self, session_id: str, response: str):
        """Handle response from assistant adapter."""
        # Forward to original handler if it exists
        if hasattr(super(), '_handle_response_ready'):
            super()._handle_response_ready(session_id, response)
        else:
            # Add basic response handling if parent doesn't have it
            logging.info(f"Response ready for session {session_id}: {response[:100]}...")
    
    def _handle_error(self, error: str):
        """Handle error from assistant adapter."""
        logging.error(f"Assistant error: {error}")
        self._show_error_message(error)
    
    def _handle_thinking_update(self, thinking: str):
        """Handle thinking update from assistant adapter."""
        # Forward to original handler if it exists
        if hasattr(super(), '_handle_thinking_update'):
            super()._handle_thinking_update(thinking)
        else:
            logging.debug(f"Thinking: {thinking[:100]}...")
    
    def _handle_status_change(self, status: str):
        """Handle status change from assistant adapter."""
        # Forward to original handler if it exists
        if hasattr(super(), '_handle_status_change'):
            super()._handle_status_change(status)
        else:
            logging.info(f"Status: {status}")
    
    def _handle_file_uploaded(self, file_path: str, file_id: str):
        """Handle file upload completion."""
        logging.info(f"File uploaded: {file_path} -> {file_id}")
    
    def _show_error_message(self, message: str):
        """Show error message to user."""
        QMessageBox.critical(self, "Error", message)
    
    def _show_info_message(self, message: str):
        """Show info message to user."""
        QMessageBox.information(self, "Information", message)
    
    def closeEvent(self, event):
        """Handle application close event."""
        try:
            # Clean up assistant adapter
            self.assistant_adapter.cleanup()
            
            # Call parent close event
            super().closeEvent(event)
            
        except Exception as e:
            logging.error(f"Error during application shutdown: {e}")
            event.accept()  # Force close anyway

def create_application():
    """Create and configure the Qt application."""
    app = QApplication(sys.argv)
    app.setApplicationName("LostMind AI Gemini Chat Assistant")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("LostMindAI")
    app.setOrganizationDomain("lostmindai.com")
    
    # Set application font
    font = QFont("Segoe UI", 9)
    app.setFont(font)
    
    return app

def show_splash_screen():
    """Show splash screen during application startup."""
    try:
        # Create splash screen (you might want to add a splash image)
        splash = QSplashScreen()
        splash.setPixmap(QPixmap(400, 300))  # Placeholder size
        splash.show()
        
        # Show for 2 seconds
        QTimer.singleShot(2000, splash.close)
        
        return splash
    except Exception:
        return None

def main():
    """Main application entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="LostMind AI Gemini Chat Assistant (Enhanced)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--config", type=str, help="Path to configuration file")
    parser.add_argument("--backend-url", type=str, default="http://localhost:8000", 
                       help="Backend service URL")
    parser.add_argument("--mode", choices=["direct", "backend"], default="direct",
                       help="Initial assistant mode")
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logger = setup_logging(level=log_level)
    
    try:
        # Create application
        app = create_application()
        
        # Show splash screen
        splash = show_splash_screen()
        
        # Initialize configuration
        config_path = args.config or "config/config.json"
        config_manager = ConfigManager(config_path)
        
        # Add backend configuration from command line
        config = config_manager.get_config()
        if "backend" not in config:
            config["backend"] = {}
        config["backend"]["url"] = args.backend_url
        config["backend"]["initial_mode"] = args.mode
        
        # Create main window
        main_window = EnhancedMainWindow(config_manager)
        
        # Set initial mode if specified
        if args.mode == "backend":
            main_window.assistant_adapter.switch_to_backend_mode(args.backend_url)
            main_window.backend_controls.mode_combo.setCurrentText("Backend Service")
        
        # Show main window
        main_window.show()
        
        # Hide splash screen
        if splash:
            splash.finish(main_window)
        
        logger.info("Application started successfully")
        
        # Run application
        exit_code = app.exec()
        
        logger.info(f"Application exited with code: {exit_code}")
        return exit_code
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}", exc_info=True)
        
        # Show error dialog if possible
        try:
            QMessageBox.critical(
                None, 
                "Startup Error", 
                f"Failed to start LostMind AI Chat Assistant:\n\n{str(e)}"
            )
        except Exception:
            pass
        
        return 1

if __name__ == "__main__":
    sys.exit(main())