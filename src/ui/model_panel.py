#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Model Panel for LostMind AI Gemini Chat Assistant

This module implements the model information panel for the chat interface,
displaying details about the selected model and its capabilities.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QGroupBox, QFormLayout, QSizePolicy, QTreeWidget,
    QTreeWidgetItem, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor

from config_manager import ConfigManager
from model_registry import ModelRegistry
from gemini_assistant import GeminiAssistant

class ModelPanel(QScrollArea):
    """
    Panel for displaying information about the selected model.
    
    Features:
    - Model details (name, description, etc.)
    - Capability information
    - Feature support
    """
    
    def __init__(self, config: ConfigManager, model_registry: ModelRegistry, assistant: GeminiAssistant):
        """
        Initialize the model panel.
        
        Args:
            config (ConfigManager): Application configuration manager.
            model_registry (ModelRegistry): Model registry.
            assistant (GeminiAssistant): Gemini assistant instance.
        """
        super().__init__()
        
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.model_registry = model_registry
        self.assistant = assistant
        
        self.init_ui()
        
        # Update model info when initialized
        self.update_model_info(self.assistant.selected_model)
    
    def init_ui(self):
        """Set up the UI components."""
        # Create widget to hold model info
        self.model_widget = QWidget()
        self.setWidget(self.model_widget)
        
        # Make scroll area resizable
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Main layout
        self.main_layout = QVBoxLayout(self.model_widget)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(15)
        
        # Header
        self.header_label = QLabel("Model Information")
        self.header_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.main_layout.addWidget(self.header_label)
        
        # Model name and description
        self.info_group = QGroupBox("Details")
        info_layout = QVBoxLayout(self.info_group)
        
        # Model name
        self.model_name_label = QLabel()
        self.model_name_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.model_name_label.setWordWrap(True)
        info_layout.addWidget(self.model_name_label)
        
        # Model ID
        self.model_id_layout = QHBoxLayout()
        self.model_id_label = QLabel("Model ID:")
        self.model_id_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.model_id_layout.addWidget(self.model_id_label)
        
        self.model_id_value = QLabel()
        self.model_id_value.setWordWrap(True)
        self.model_id_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.model_id_layout.addWidget(self.model_id_value)
        
        info_layout.addLayout(self.model_id_layout)
        
        # Model type
        self.model_type_layout = QHBoxLayout()
        self.model_type_label = QLabel("Type:")
        self.model_type_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.model_type_layout.addWidget(self.model_type_label)
        
        self.model_type_value = QLabel()
        self.model_type_layout.addWidget(self.model_type_value)
        
        info_layout.addLayout(self.model_type_layout)
        
        # Base model (if applicable)
        self.base_model_container = QWidget()
        self.base_model_layout = QHBoxLayout(self.base_model_container)
        self.base_model_layout.setContentsMargins(0, 0, 0, 0)
        
        self.base_model_label = QLabel("Base Model:")
        self.base_model_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.base_model_layout.addWidget(self.base_model_label)
        
        self.base_model_value = QLabel()
        self.base_model_layout.addWidget(self.base_model_value)
        
        info_layout.addWidget(self.base_model_container)
        
        # Model description
        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        self.description_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        info_layout.addWidget(self.description_label)
        
        self.main_layout.addWidget(self.info_group)
        
        # Capabilities group
        self.capabilities_group = QGroupBox("Capabilities")
        capabilities_layout = QVBoxLayout(self.capabilities_group)
        
        # Capabilities table
        self.capabilities_table = QTableWidget(0, 2)
        self.capabilities_table.setHorizontalHeaderLabels(["Feature", "Support"])
        self.capabilities_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.capabilities_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.capabilities_table.verticalHeader().setVisible(False)
        self.capabilities_table.setAlternatingRowColors(True)
        self.capabilities_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        capabilities_layout.addWidget(self.capabilities_table)
        
        self.main_layout.addWidget(self.capabilities_group)
        
        # Add spacer to push everything to the top
        self.main_layout.addStretch()
    
    def update_model_info(self, model_id: str):
        """
        Update the model information display.
        
        Args:
            model_id (str): Model ID to display information for.
        """
        # Get model information
        model_info = self.model_registry.get_model_by_id(model_id)
        
        if not model_info:
            # Model not found, show placeholder
            self.model_name_label.setText("Unknown Model")
            self.model_id_value.setText(model_id)
            self.model_type_value.setText("Unknown")
            self.base_model_value.setText("N/A")
            self.description_label.setText("No information available for this model.")
            
            # Hide base model container if not applicable
            self.base_model_container.setVisible(False)
            
            # Clear capabilities
            self.capabilities_table.setRowCount(0)
            return
        
        # Show model information
        display_name = model_info.get('display_name', model_id)
        self.model_name_label.setText(display_name)
        self.model_id_value.setText(model_id)
        
        # Model type
        model_type = model_info.get('type', 'base')
        self.model_type_value.setText(model_type.capitalize())
        
        # Base model (only for tuned models)
        if model_type == 'tuned' and 'base_model' in model_info:
            self.base_model_value.setText(model_info['base_model'])
            self.base_model_container.setVisible(True)
        else:
            self.base_model_value.setText("N/A")
            self.base_model_container.setVisible(False)
        
        # Description
        description = model_info.get('description', '')
        if not description:
            # Generate a description based on model name
            if "flash" in model_id.lower():
                description = "Optimized for faster responses with balanced quality."
            elif "pro" in model_id.lower():
                description = "Optimized for high-quality responses and complex tasks."
            
            # Add version info
            if "1.5" in model_id:
                description += " Gemini 1.5 model with enhanced capabilities."
            elif "2.0" in model_id:
                description += " Latest Gemini 2.0 model with advanced features."
        
        self.description_label.setText(description)
        
        # Update capabilities
        self.update_capabilities(model_info)
    
    def update_capabilities(self, model_info: Dict[str, Any]):
        """
        Update the capabilities table.
        
        Args:
            model_info (Dict[str, Any]): Model information.
        """
        # Clear existing items
        self.capabilities_table.setRowCount(0)
        
        # Get supported methods
        supported_methods = model_info.get('supported_methods', [])
        
        # Define capabilities to display
        capabilities = [
            {
                "name": "Text Generation",
                "feature": "generateContent",
                "description": "Generate text responses"
            },
            {
                "name": "Streaming",
                "feature": "streamGenerateContent",
                "description": "Stream responses in real-time"
            },
            {
                "name": "Token Counting",
                "feature": "countTokens",
                "description": "Count tokens in messages"
            },
            {
                "name": "Google Search",
                "feature": "googleSearch",
                "description": "Ground responses with web search"
            },
            {
                "name": "Thinking Mode",
                "feature": "thinkingMode",
                "description": "Step-by-step reasoning for complex tasks"
            },
            {
                "name": "Function Calling",
                "feature": "functionCalling",
                "description": "Call external functions and tools"
            },
            {
                "name": "Multimodal Input",
                "feature": "multimodalInput",
                "description": "Process images, videos, and text"
            },
            {
                "name": "Context Caching",
                "feature": "createCachedContent",
                "description": "Cache context for efficient reuse"
            }
        ]
        
        # Add capabilities to table
        self.capabilities_table.setRowCount(len(capabilities))
        
        for i, capability in enumerate(capabilities):
            # Check if feature is supported
            is_supported = capability["feature"] in supported_methods
            
            # For special checks based on model ID
            model_id = model_info.get('id', '')
            
            # Multimodal is supported by all Gemini models
            if capability["feature"] == "multimodalInput":
                is_supported = True
            
            # Google Search is available in Gemini 2.0
            if capability["feature"] == "googleSearch" and "gemini-2" in model_id:
                is_supported = True
            
            # Thinking mode is available in Pro models
            if capability["feature"] == "thinkingMode" and "pro" in model_id:
                is_supported = True
            
            # Create table items
            name_item = QTableWidgetItem(capability["name"])
            name_item.setToolTip(capability["description"])
            
            # Create support indicator
            support_text = "✅ Yes" if is_supported else "❌ No"
            support_item = QTableWidgetItem(support_text)
            support_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Set text color based on support
            if is_supported:
                support_item.setForeground(QColor(0, 128, 0))  # Green
            else:
                support_item.setForeground(QColor(192, 0, 0))  # Red
            
            # Add items to table
            self.capabilities_table.setItem(i, 0, name_item)
            self.capabilities_table.setItem(i, 1, support_item)
        
        # Resize rows to contents
        self.capabilities_table.resizeRowsToContents()
