#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Status Bar Manager for LostMind AI Gemini Chat Assistant

This module implements the status bar manager for the chat interface,
handling status messages, progress indicators, and other status information.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from PyQt6.QtWidgets import (
    QStatusBar, QLabel, QProgressBar, QHBoxLayout, QWidget
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPixmap, QIcon

class StatusBarManager:
    """
    Manager for the application status bar.
    
    Features:
    - Status messages with different types (info, warning, error)
    - Busy indicator for long operations
    - API status indicator
    - Message timeout
    """
    
    # Message types
    TYPE_INFO = "info"
    TYPE_WARNING = "warning"
    TYPE_ERROR = "error"
    TYPE_SUCCESS = "success"
    
    def __init__(self, status_bar: QStatusBar):
        """
        Initialize the status bar manager.
        
        Args:
            status_bar (QStatusBar): Status bar to manage.
        """
        self.logger = logging.getLogger(__name__)
        self.status_bar = status_bar
        
        # Initialize components
        self.init_components()
        
        # Timer for temporary messages
        self.message_timer = QTimer()
        self.message_timer.setSingleShot(True)
        self.message_timer.timeout.connect(self.clear_temporary_message)
    
    def init_components(self):
        """Initialize status bar components."""
        # Message label (left-aligned)
        self.message_label = QLabel()
        self.message_label.setStyleSheet("padding: 2px;")
        self.status_bar.addWidget(self.message_label, 1)
        
        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setFixedWidth(100)
        self.progress_bar.setFixedHeight(15)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        # API status indicator (right-aligned)
        self.api_status_label = QLabel()
        self.api_status_label.setFixedWidth(16)
        self.api_status_label.setFixedHeight(16)
        self.api_status_label.setVisible(False)
        self.status_bar.addPermanentWidget(self.api_status_label)
    
    def show_message(self, message: str, timeout: int = 5000, message_type: str = TYPE_INFO):
        """
        Show a status message.
        
        Args:
            message (str): Message to show.
            timeout (int, optional): Message timeout in milliseconds. 
                Set to 0 for persistent message. Defaults to 5000.
            message_type (str, optional): Message type. 
                One of TYPE_INFO, TYPE_WARNING, TYPE_ERROR, TYPE_SUCCESS.
                Defaults to TYPE_INFO.
        """
        # Set message text and style based on type
        self.message_label.setText(message)
        
        if message_type == self.TYPE_WARNING:
            self.message_label.setStyleSheet("color: #f39c12; padding: 2px;")
        elif message_type == self.TYPE_ERROR:
            self.message_label.setStyleSheet("color: #e74c3c; font-weight: bold; padding: 2px;")
        elif message_type == self.TYPE_SUCCESS:
            self.message_label.setStyleSheet("color: #2ecc71; padding: 2px;")
        else:
            self.message_label.setStyleSheet("color: #2c3e50; padding: 2px;")
        
        # Set timeout if specified
        if timeout > 0:
            # Stop any existing timer
            if self.message_timer.isActive():
                self.message_timer.stop()
            
            # Start new timer
            self.message_timer.start(timeout)
    
    def show_info(self, message: str, timeout: int = 5000):
        """
        Show an info message.
        
        Args:
            message (str): Message to show.
            timeout (int, optional): Message timeout in milliseconds.
                Defaults to 5000.
        """
        self.show_message(message, timeout, self.TYPE_INFO)
    
    def show_warning(self, message: str, timeout: int = 8000):
        """
        Show a warning message.
        
        Args:
            message (str): Message to show.
            timeout (int, optional): Message timeout in milliseconds.
                Defaults to 8000.
        """
        self.show_message(message, timeout, self.TYPE_WARNING)
    
    def show_error(self, message: str, timeout: int = 10000):
        """
        Show an error message.
        
        Args:
            message (str): Message to show.
            timeout (int, optional): Message timeout in milliseconds.
                Defaults to 10000.
        """
        self.show_message(message, timeout, self.TYPE_ERROR)
    
    def show_success(self, message: str, timeout: int = 5000):
        """
        Show a success message.
        
        Args:
            message (str): Message to show.
            timeout (int, optional): Message timeout in milliseconds.
                Defaults to 5000.
        """
        self.show_message(message, timeout, self.TYPE_SUCCESS)
    
    def show_busy(self, message: str = "Processing..."):
        """
        Show busy indicator with message.
        
        Args:
            message (str, optional): Message to show.
                Defaults to "Processing...".
        """
        self.message_label.setText(message)
        self.message_label.setStyleSheet("color: #2c3e50; padding: 2px;")
        self.progress_bar.setVisible(True)
        
        # Stop any active timer
        if self.message_timer.isActive():
            self.message_timer.stop()
    
    def hide_busy(self):
        """Hide busy indicator."""
        self.progress_bar.setVisible(False)
    
    def clear_message(self):
        """Clear the status message."""
        self.message_label.clear()
        self.message_label.setStyleSheet("padding: 2px;")
        
        # Stop any active timer
        if self.message_timer.isActive():
            self.message_timer.stop()
    
    def clear_temporary_message(self):
        """Clear a temporary message when timer expires."""
        # Only clear if this is the message from the timer
        self.clear_message()
    
    def set_api_status(self, is_connected: bool):
        """
        Set the API connection status indicator.
        
        Args:
            is_connected (bool): Whether API is connected.
        """
        # Set icon based on status
        if is_connected:
            # Green circle for connected
            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.GlobalColor.transparent)
            pixmap.fill(QColor(46, 204, 113))  # Green color
            self.api_status_label.setPixmap(pixmap)
            self.api_status_label.setToolTip("API Connected")
        else:
            # Red circle for disconnected
            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.GlobalColor.transparent)
            pixmap.fill(QColor(231, 76, 60))  # Red color
            self.api_status_label.setPixmap(pixmap)
            self.api_status_label.setToolTip("API Disconnected")
        
        self.api_status_label.setVisible(True)
