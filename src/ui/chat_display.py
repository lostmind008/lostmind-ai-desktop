#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Chat Display for LostMind AI Gemini Chat Assistant

This module implements the chat display component for the Gemini Chat Assistant,
including message rendering, markdown support, and styling.
"""

import re
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from PyQt6.QtWidgets import (
    QScrollArea, QWidget, QVBoxLayout, QLabel, QFrame,
    QSizePolicy, QHBoxLayout, QSpacerItem
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont, QTextCursor, QPixmap

from ui.markdown_renderer import MarkdownTextEdit

class ChatBubble(QFrame):
    """A chat bubble widget representing a message."""
    
    def __init__(self, role: str, content: str, timestamp: Optional[datetime] = None):
        """
        Initialize a chat bubble.
        
        Args:
            role (str): Message role (user, ai, system, error).
            content (str): Message content.
            timestamp (Optional[datetime], optional): Message timestamp. 
                Defaults to current time.
        """
        super().__init__()
        
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now()
        self.search_used = False
        
        self.init_ui()
    
    def init_ui(self):
        """Set up the UI components."""
        # Main layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(5)
        
        # Header with role and timestamp
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(5)
        
        # Role label
        self.role_label = QLabel()
        self.role_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        
        self.role_label.setText(self.role.capitalize())
        if self.role == "user":
            self.role_label.setStyleSheet("color: #0066cc;")
        elif self.role == "ai":
            self.role_label.setStyleSheet("color: #009933;")
        elif self.role == "system":
            self.role_label.setStyleSheet("color: #666666;")
        elif self.role == "error":
            self.role_label.setStyleSheet("color: #cc3300;")        



        
        header_layout.addWidget(self.role_label)
        
        # Search indicator (hidden by default)
        self.search_indicator = QLabel("Search")
        self.search_indicator.setFont(QFont("Arial", 10))
        self.search_indicator.setStyleSheet(
            "background-color: #808080; color: white; padding: 2px 5px; border-radius: 4px;"
        )
        self.search_indicator.setVisible(False)
        header_layout.addWidget(self.search_indicator)
        
        # Add spacer to push timestamp to the right
        header_layout.addItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        # Timestamp label
        self.timestamp_label = QLabel(self.timestamp.strftime("%H:%M:%S"))
        self.timestamp_label.setFont(QFont("Arial", 10))
        self.timestamp_label.setStyleSheet("color: #888888;")
        header_layout.addWidget(self.timestamp_label)
        
        self.layout.addLayout(header_layout)
        
        # Message content
        self.text_edit = MarkdownTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setMarkdown(self.content)
        
        # Ensure text edit auto-expands and doesn't scroll
        self.text_edit.setMinimumHeight(30)
        self.text_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # These settings help ensure the text is fully visible without scrolling
        doc = self.text_edit.document()
        doc.setDocumentMargin(0)
        
        # Force document to calculate its size
        doc.adjustSize()
        # Set the height of the text edit to match the document's height
        doc_height = doc.size().height()
        self.text_edit.setFixedHeight(int(doc_height + 10))  # Add padding
        
        # Set stylesheet based on role
        if self.role == "user":
            self.setStyleSheet("""
                ChatBubble {
                    background-color: #FFF8E1;
                    border: 1px solid #E6DFC8;
                    border-radius: 8px;
                }
                QTextEdit {
                    color: #000000;         
                    font-size: 14pt;      
                    background: transparent;
                }
            """)
        elif self.role == "ai":
            self.setStyleSheet("""
                ChatBubble {
                    background-color: #FFFAF0;
                    border: 1px solid #EAE0D0;
                    border-radius: 8px;
                }
                QTextEdit {
                    color: #000000;        
                    font-size: 14pt;        
                    background: transparent;
                }
            """)
        elif self.role == "system":
            self.setStyleSheet("""
                ChatBubble {
                    background-color: #FFF5EB;
                    border: 1px solid #E8DFD5;
                    border-radius: 8px;
                }
                QTextEdit {
                    color: #000000;        
                    font-size: 14pt;      
                    background: transparent;
                    font-style: italic;
                }
            """)
        elif self.role == "error":
            self.setStyleSheet("""
                ChatBubble {
                    background-color: #ffe6e6;
                    border: 1px solid #e9c0c0;
                    border-radius: 8px;
                }
                QTextEdit {
                    color: #cc0000;        
                    font-size: 14pt;      
                    background: transparent;
                }
            """)
        
        self.layout.addWidget(self.text_edit)
    
    def append_content(self, additional_content: str):
        """
        Append additional content to the message.
        
        Args:
            additional_content (str): Content to append.
        """
        self.content += additional_content
        self.text_edit.setMarkdown(self.content)
        
        # Recalculate height after adding content
        doc = self.text_edit.document()
        doc.adjustSize()
        doc_height = doc.size().height()
        self.text_edit.setFixedHeight(int(doc_height + 10))  # Add padding
        
        # Ensure text is visible by scrolling to the end
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.text_edit.setTextCursor(cursor)
    
    def set_search_used(self, used: bool):
        """
        Set whether search was used in this message.
        
        Args:
            used (bool): Whether search was used.
        """
        self.search_used = used
        self.search_indicator.setVisible(used)

class ChatDisplay(QScrollArea):
    """
    Widget for displaying chat messages.
    
    Features:
    - Message bubbles for different roles (user, ai, system, error)
    - Markdown rendering for message content
    - Search indicators for messages that used Google Search
    - Automatic scrolling to new messages
    """
    
    def __init__(self):
        """Initialize the chat display."""
        super().__init__()
        
        self.logger = logging.getLogger(__name__)
        self.messages = []
        
        self.init_ui()
    
    def init_ui(self):
        """Set up the UI components."""
        # Set up scroll area
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Create widget to hold messages
        self.messages_widget = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.messages_layout.setContentsMargins(10, 10, 10, 10)
        self.messages_layout.setSpacing(15)
        
        # Add spacer to push messages to the top
        self.spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.messages_layout.addItem(self.spacer)
        
        # Set the widget for the scroll area
        self.setWidget(self.messages_widget)
        
        # Set style
        self.setStyleSheet("""
            QScrollArea {
                background-color: #FFF5E6;
                border: none;
            }
            QWidget#messages_widget {
                background-color: #FFF5E6;
            }
        """)
        
        # Set object name for styling
        self.messages_widget.setObjectName("messages_widget")
    
    def add_message(self, role: str, content: str) -> ChatBubble:
        """
        Add a message to the chat display.
        
        Args:
            role (str): Message role (user, ai, system, error).
            content (str): Message content.
        
        Returns:
            ChatBubble: The created message bubble.
        """
        # Remove spacer before adding new message
        self.messages_layout.removeItem(self.spacer)
        
        # Create message bubble
        bubble = ChatBubble(role, content)
        self.messages.append(bubble)
        
        # Add bubble to layout
        self.messages_layout.addWidget(bubble)
        
        # Add spacer back to push messages to the top
        self.messages_layout.addItem(self.spacer)
        
        # Scroll to bottom to show the new message
        QTimer.singleShot(100, self.scroll_to_bottom)
        
        return bubble
    
    def add_user_message(self, content: str) -> ChatBubble:
        """
        Add a user message.
        
        Args:
            content (str): Message content.
        
        Returns:
            ChatBubble: The created message bubble.
        """
        return self.add_message("user", content)
    
    def add_ai_message(self, content: str) -> ChatBubble:
        """
        Add an AI message.
        
        Args:
            content (str): Message content.
        
        Returns:
            ChatBubble: The created message bubble.
        """
        return self.add_message("ai", content)
    
    def add_system_message(self, content: str) -> ChatBubble:
        """
        Add a system message.
        
        Args:
            content (str): Message content.
        
        Returns:
            ChatBubble: The created message bubble.
        """
        return self.add_message("system", content)
    
    def add_error_message(self, content: str) -> ChatBubble:
        """
        Add an error message.
        
        Args:
            content (str): Message content.
        
        Returns:
            ChatBubble: The created message bubble.
        """
        return self.add_message("error", content)
    
    def append_to_last_message(self, content: str):
        """
        Append content to the last message.
        
        Args:
            content (str): Content to append.
        """
        if self.messages:
            last_message = self.messages[-1]
            last_message.append_content(content)
            
            # Scroll to bottom to show the updated message
            QTimer.singleShot(10, self.scroll_to_bottom)
    
    def set_last_message_search_used(self, used: bool):
        """
        Set whether search was used in the last message.
        
        Args:
            used (bool): Whether search was used.
        """
        if self.messages:
            last_message = self.messages[-1]
            last_message.set_search_used(used)
    
    def clear(self):
        """Clear all messages from the display."""
        # Remove all messages
        while self.messages:
            message = self.messages.pop()
            self.messages_layout.removeWidget(message)
            message.deleteLater()
    
    def scroll_to_bottom(self):
        """Scroll to the bottom of the chat display."""
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
