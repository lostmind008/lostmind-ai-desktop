#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Controls Panel for LostMind AI Gemini Chat Assistant

This module implements the controls panel for the chat interface,
including message input, send button, and other controls.
"""

import logging
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QCheckBox, QFrame, QSizePolicy, QToolButton,
    QMenu
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QIcon, QKeySequence, QShortcut, QAction

from config_manager import ConfigManager
from gemini_assistant import GeminiAssistant

class ExpandingTextEdit(QTextEdit):
    """
    A text edit that expands vertically to fit content, up to a maximum height.
    """
    
    def __init__(self, min_height: int = 36, max_height: int = 150):
        """
        Initialize the expanding text edit.
        
        Args:
            min_height (int, optional): Minimum height. Defaults to 36.
            max_height (int, optional): Maximum height. Defaults to 150.
        """
        super().__init__()
        
        self.min_height = min_height
        self.max_height = max_height
        
        # Set initial size policy and height
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setMinimumHeight(min_height)
        self.setMaximumHeight(max_height)
        
        # Set placeholder text
        self.setPlaceholderText("Type your message here...")
        
        # Add style
        self.setStyleSheet("""
            ExpandingTextEdit {
                border: 1px solid #c0c0c0;
                border-radius: 4px;
                background-color: #f5f5f5;
                color: #000080;
                padding: 4px;
                font-family: Arial, sans-serif;
                font-size: 14pt;
            }
        """)
    
    def sizeHint(self):
        """
        Get the preferred size.
        
        Returns:
            QSize: Preferred size.
        """
        size = super().sizeHint()
        doc_height = self.document().size().height()
        height = min(max(doc_height + 10, self.min_height), self.max_height)
        return QSize(size.width(), int(height))
    
    def keyPressEvent(self, event):
        """
        Handle key press events.
        
        Args:
            event: Key press event.
        """
        # Update height when text changes
        super().keyPressEvent(event)
        self.updateGeometry()
        
        # Handle Ctrl+Enter shortcut
        if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.parent().send_message()
            return
        
        # Handle Shift+Enter for line breaks
        if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
            # Let the normal behavior happen (insert line break)
            return
        
        # Handle plain Enter to send message
        if event.key() == Qt.Key.Key_Return and not event.modifiers():
            # Send message
            self.parent().send_message()
            event.accept()  # Prevent the newline from being inserted
            return

class ControlsPanel(QWidget):
    """
    Panel containing message input and control buttons.
    """
    
    # Signals
    message_sent = pyqtSignal(str)
    clear_requested = pyqtSignal()
    export_requested = pyqtSignal()
    
    def __init__(self, config: ConfigManager, assistant: GeminiAssistant):
        """
        Initialize the controls panel.
        
        Args:
            config (ConfigManager): Application configuration manager.
            assistant (GeminiAssistant): Gemini assistant instance.
        """
        super().__init__()
        
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.assistant = assistant
        
        self.init_ui()
    
    def init_ui(self):
        """Set up the UI components."""
        # Main layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)
        
        # Features layout for checkboxes
        features_layout = QHBoxLayout()
        features_layout.setContentsMargins(0, 0, 0, 0)
        features_layout.setSpacing(10)
        
        # Checkboxes for features
        self.streaming_checkbox = QCheckBox("Streaming")
        self.streaming_checkbox.setChecked(self.assistant.streaming)
        self.streaming_checkbox.setToolTip("Enable streaming responses")
        self.streaming_checkbox.toggled.connect(self.on_streaming_toggled)
        features_layout.addWidget(self.streaming_checkbox)
        
        # Search checkbox (only visible for Gemini 2.0)
        self.search_checkbox = QCheckBox("Google Search")
        self.search_checkbox.setChecked(self.assistant.use_search)
        self.search_checkbox.setToolTip("Enable Google Search grounding")
        self.search_checkbox.toggled.connect(self.on_search_toggled)
        features_layout.addWidget(self.search_checkbox)
        
        # Thinking mode checkbox (only for supported models)
        self.thinking_checkbox = QCheckBox("Thinking Mode")
        self.thinking_checkbox.setChecked(self.assistant.thinking_mode)
        self.thinking_checkbox.setToolTip("Enable thinking mode for step-by-step reasoning")
        self.thinking_checkbox.toggled.connect(self.on_thinking_toggled)
        features_layout.addWidget(self.thinking_checkbox)
        
        # Add spacer to push everything to the left
        features_layout.addStretch()
        
        # Add features layout
        self.layout.addLayout(features_layout)
        
        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("background-color: #c0c0c0;")
        self.layout.addWidget(separator)
        
        # Input layout
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(10)
        
        # Text input
        self.input_edit = ExpandingTextEdit()
        input_layout.addWidget(self.input_edit)
        
        # Control buttons
        buttons_layout = QVBoxLayout()
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(5)
        
        # Send button
        self.send_button = QPushButton("Send")
        self.send_button.setToolTip("Send message (Ctrl+Enter)")
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setDefault(True)
        
        # Style the send button
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        
        buttons_layout.addWidget(self.send_button)
        
        # More options button (menu)
        self.more_button = QToolButton()
        self.more_button.setText("More")
        self.more_button.setToolTip("More options")
        self.more_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        
        # Create menu for more button
        menu = QMenu(self)
        
        # Clear action
        clear_action = QAction("Clear Chat", self)
        clear_action.triggered.connect(self.clear_requested.emit)
        menu.addAction(clear_action)
        
        # Export action
        export_action = QAction("Export Chat", self)
        export_action.triggered.connect(self.export_requested.emit)
        menu.addAction(export_action)
        
        # Set menu to more button
        self.more_button.setMenu(menu)
        
        buttons_layout.addWidget(self.more_button)
        buttons_layout.addStretch()
        
        input_layout.addLayout(buttons_layout)
        
        self.layout.addLayout(input_layout)
        
        # Update feature visibility
        self.update_feature_visibility()
    
    def send_message(self):
        """Send the current message."""
        # Get message text
        message = self.input_edit.toPlainText().strip()
        
        if not message:
            return
        
        # Clear input field
        self.input_edit.clear()
        
        # Emit signal with message
        self.message_sent.emit(message)
    
    def on_streaming_toggled(self, checked: bool):
        """
        Handle streaming checkbox toggle.
        
        Args:
            checked (bool): Whether the checkbox is checked.
        """
        self.assistant.streaming = checked
    
    def on_search_toggled(self, checked: bool):
        """
        Handle search checkbox toggle.
        
        Args:
            checked (bool): Whether the checkbox is checked.
        """
        self.assistant.use_search = checked
    
    def on_thinking_toggled(self, checked: bool):
        """
        Handle thinking mode checkbox toggle.
        
        Args:
            checked (bool): Whether the checkbox is checked.
        """
        self.assistant.thinking_mode = checked
    
    def update_feature_visibility(self):
        """Update visibility of feature checkboxes based on model support."""
        # Update search checkbox visibility
        can_use_search = self.model_supports_search()
        self.search_checkbox.setVisible(can_use_search)
        
        # Update thinking mode checkbox visibility
        can_use_thinking = self.model_supports_thinking()
        self.thinking_checkbox.setVisible(can_use_thinking)
    
    def model_supports_search(self) -> bool:
        """
        Check if the current model supports Google Search.
        
        Returns:
            bool: True if search is supported, False otherwise.
        """
        if not self.assistant.selected_model:
            return False
        return "gemini-2" in self.assistant.selected_model and \
            self.assistant.model_registry.model_supports_feature(
                self.assistant.selected_model, "googleSearch"
            )
    
    def model_supports_thinking(self) -> bool:
        """
        Check if the current model supports thinking mode.
        
        Returns:
            bool: True if thinking mode is supported, False otherwise.
        """
        if not self.assistant.selected_model:
            return False
        return self.assistant.model_registry.model_supports_feature(
            self.assistant.selected_model, "thinkingMode"
        )
    
    def enable_controls(self):
        """Enable controls after chat is started."""
        self.send_button.setEnabled(True)
        self.more_button.setEnabled(True)
        self.input_edit.setEnabled(True)
        self.streaming_checkbox.setEnabled(True)
        self.search_checkbox.setEnabled(True)
        self.thinking_checkbox.setEnabled(True)
        
        # Update feature visibility
        self.update_feature_visibility()
    
    def disable_controls(self):
        """Disable controls before chat is started."""
        self.send_button.setEnabled(False)
        self.more_button.setEnabled(False)
        self.input_edit.setEnabled(False)
        self.streaming_checkbox.setEnabled(False)
        self.search_checkbox.setEnabled(False)
        self.thinking_checkbox.setEnabled(False)
    
    def set_controls_enabled(self, enabled: bool):
        """
        Set whether controls are enabled.
        
        Args:
            enabled (bool): Whether controls are enabled.
        """
        if enabled:
            self.enable_controls()
        else:
            self.disable_controls()
