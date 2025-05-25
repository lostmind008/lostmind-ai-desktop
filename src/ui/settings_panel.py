#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Settings Panel for LostMind AI Gemini Chat Assistant

This module implements the settings panel for the chat interface,
including model selection, parameter settings, and system instruction.
"""

import logging
from typing import Optional, Dict, Any, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSlider, QTextEdit, QPushButton, QGroupBox, QCheckBox,
    QFormLayout, QSpinBox, QDoubleSpinBox, QFrame,
    QSizePolicy, QScrollArea, QMessageBox
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QFont

from config_manager import ConfigManager
from model_registry import ModelRegistry
from gemini_assistant import GeminiAssistant

class SettingsPanel(QScrollArea):
    """
    Panel for configuring chat settings.
    
    Features:
    - Model selection
    - Temperature and other parameter settings
    - System instruction configuration
    - Chat session controls
    """
    
    # Signals
    model_changed = pyqtSignal(str)
    chat_started = pyqtSignal()
    settings_updated = pyqtSignal()
    
    def __init__(self, config: ConfigManager, model_registry: ModelRegistry, assistant: GeminiAssistant):
        """
        Initialize the settings panel.
        
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
    
    def init_ui(self):
        """Set up the UI components."""
        # Create widget to hold settings
        self.settings_widget = QWidget()
        self.setWidget(self.settings_widget)
        
        # Make scroll area resizable
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Main layout
        self.main_layout = QVBoxLayout(self.settings_widget)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(15)
        
        # Header
        header_label = QLabel("Chat Settings")
        header_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.main_layout.addWidget(header_label)
        
        # Model selection group
        self.create_model_section()
        
        # Generation parameters group
        self.create_parameters_section()
        
        # System instruction group
        self.create_instruction_section()
        
        # Control buttons
        self.create_control_section()
        
        # Add a spacer to push everything to the top
        self.main_layout.addStretch()
    
    def create_model_section(self):
        """Create the model selection section."""
        model_group = QGroupBox("Model Selection")
        model_layout = QVBoxLayout(model_group)
        
        # Model combobox
        model_form = QFormLayout()
        model_form.setVerticalSpacing(10)
        
        self.model_combo = QComboBox()
        
        # Get display names of available models
        model_display_names = []
        self.model_id_map = {}
        
        for model in self.model_registry.get_models():
            model_id = model['id']
            display_name = model.get('display_name', model_id)
            model_display_names.append(display_name)
            self.model_id_map[display_name] = model_id
        
        # Add models to combo box
        self.model_combo.addItems(model_display_names)
        
        # Set current model
        current_model_display = self.model_registry.get_model_by_id(
            self.assistant.selected_model
        ).get('display_name', self.assistant.selected_model)
        
        self.model_combo.setCurrentText(current_model_display)
        
        # Connect signal
        self.model_combo.currentTextChanged.connect(self.on_model_selection_changed)
        
        model_form.addRow("Select Model:", self.model_combo)
        
        # Refresh button
        refresh_layout = QHBoxLayout()
        refresh_layout.addStretch()
        
        self.refresh_button = QPushButton("Refresh Model List")
        self.refresh_button.clicked.connect(self.refresh_models)
        refresh_layout.addWidget(self.refresh_button)
        
        model_layout.addLayout(model_form)
        model_layout.addLayout(refresh_layout)
        
        self.main_layout.addWidget(model_group)
    
    def create_parameters_section(self):
        """Create the generation parameters section."""
        params_group = QGroupBox("Generation Parameters")
        params_layout = QVBoxLayout(params_group)
        
        # Parameters form
        params_form = QFormLayout()
        params_form.setVerticalSpacing(10)
        
        # Temperature slider
        temp_layout = QHBoxLayout()
        self.temp_slider = QSlider(Qt.Orientation.Horizontal)
        self.temp_slider.setMinimum(0)
        self.temp_slider.setMaximum(100)
        self.temp_slider.setValue(int(self.assistant.temperature * 100))
        self.temp_slider.setTracking(True)
        self.temp_slider.valueChanged.connect(self.on_temp_changed)
        temp_layout.addWidget(self.temp_slider)
        
        self.temp_label = QLabel(f"{self.assistant.temperature:.2f}")
        self.temp_label.setMinimumWidth(40)
        temp_layout.addWidget(self.temp_label)
        
        params_form.addRow("Temperature:", temp_layout)
        
        # Top P slider
        top_p_layout = QHBoxLayout()
        self.top_p_slider = QSlider(Qt.Orientation.Horizontal)
        self.top_p_slider.setMinimum(0)
        self.top_p_slider.setMaximum(100)
        self.top_p_slider.setValue(int(self.assistant.top_p * 100))
        self.top_p_slider.setTracking(True)
        self.top_p_slider.valueChanged.connect(self.on_top_p_changed)
        top_p_layout.addWidget(self.top_p_slider)
        
        self.top_p_label = QLabel(f"{self.assistant.top_p:.2f}")
        self.top_p_label.setMinimumWidth(40)
        top_p_layout.addWidget(self.top_p_label)
        
        params_form.addRow("Top P:", top_p_layout)
        
        # Max output tokens
        max_tokens_layout = QHBoxLayout()
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setMinimum(1)
        self.max_tokens_spin.setMaximum(32768)
        self.max_tokens_spin.setValue(self.assistant.max_output_tokens)
        self.max_tokens_spin.setSingleStep(1024)
        self.max_tokens_spin.valueChanged.connect(self.on_max_tokens_changed)
        max_tokens_layout.addWidget(self.max_tokens_spin)
        
        params_form.addRow("Max Output Tokens:", max_tokens_layout)
        
        # Default button
        default_layout = QHBoxLayout()
        default_layout.addStretch()
        
        self.default_button = QPushButton("Reset to Defaults")
        self.default_button.clicked.connect(self.reset_parameters)
        default_layout.addWidget(self.default_button)
        
        params_layout.addLayout(params_form)
        params_layout.addLayout(default_layout)
        
        self.main_layout.addWidget(params_group)
    
    def create_instruction_section(self):
        """Create the system instruction section."""
        instruction_group = QGroupBox("System Instruction")
        instruction_layout = QVBoxLayout(instruction_group)
        
        # Instruction text edit
        self.instruction_edit = QTextEdit()
        self.instruction_edit.setPlainText(self.assistant.system_instruction)
        self.instruction_edit.setMinimumHeight(100)
        instruction_layout.addWidget(self.instruction_edit)
        
        # Buttons for preset instructions
        presets_layout = QHBoxLayout()
        
        self.default_inst_button = QPushButton("Default")
        self.default_inst_button.clicked.connect(self.use_default_instruction)
        presets_layout.addWidget(self.default_inst_button)
        
        self.general_inst_button = QPushButton("General Assistant")
        self.general_inst_button.clicked.connect(self.use_general_instruction)
        presets_layout.addWidget(self.general_inst_button)
        
        self.coder_inst_button = QPushButton("Coding Assistant")
        self.coder_inst_button.clicked.connect(self.use_coding_instruction)
        presets_layout.addWidget(self.coder_inst_button)
        
        instruction_layout.addLayout(presets_layout)
        
        self.main_layout.addWidget(instruction_group)
    
    def create_control_section(self):
        """Create the control buttons section."""
        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(0, 10, 0, 10)
        
        # Save settings button
        self.save_button = QPushButton("Save Settings")
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        self.save_button.clicked.connect(self.save_settings)
        control_layout.addWidget(self.save_button)
        
        # Add spacer
        control_layout.addStretch()
        
        # Start chat button
        self.start_button = QPushButton("Start Chat")
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.start_button.clicked.connect(self.start_chat)
        control_layout.addWidget(self.start_button)
        
        self.main_layout.addLayout(control_layout)
    
    def on_model_selection_changed(self, model_display_name: str):
        """
        Handle model selection change.
        
        Args:
            model_display_name (str): Selected model display name.
        """
        # Convert display name to model ID
        model_id = self.model_id_map.get(model_display_name)
        
        if model_id:
            # Update assistant
            self.assistant.selected_model = model_id
            
            # Emit signal
            self.model_changed.emit(model_id)
    
    def on_temp_changed(self, value: int):
        """
        Handle temperature slider change.
        
        Args:
            value (int): Slider value (0-100).
        """
        # Convert to 0.0-1.0 range
        temperature = value / 100.0
        
        # Update label
        self.temp_label.setText(f"{temperature:.2f}")
        
        # Update assistant
        self.assistant.temperature = temperature
    
    def on_top_p_changed(self, value: int):
        """
        Handle top P slider change.
        
        Args:
            value (int): Slider value (0-100).
        """
        # Convert to 0.0-1.0 range
        top_p = value / 100.0
        
        # Update label
        self.top_p_label.setText(f"{top_p:.2f}")
        
        # Update assistant
        self.assistant.top_p = top_p
    
    def on_max_tokens_changed(self, value: int):
        """
        Handle max tokens spinner change.
        
        Args:
            value (int): Spinner value.
        """
        # Update assistant
        self.assistant.max_output_tokens = value
    
    def reset_parameters(self):
        """Reset generation parameters to defaults."""
        # Get default values from config
        default_temp = self.config.get_value(['default_settings', 'temperature'], 0.7)
        default_top_p = self.config.get_value(['default_settings', 'top_p'], 0.95)
        default_max_tokens = self.config.get_value(['default_settings', 'max_output_tokens'], 8192)
        
        # Update UI
        self.temp_slider.setValue(int(default_temp * 100))
        self.top_p_slider.setValue(int(default_top_p * 100))
        self.max_tokens_spin.setValue(default_max_tokens)
        
        # Update assistant
        self.assistant.temperature = default_temp
        self.assistant.top_p = default_top_p
        self.assistant.max_output_tokens = default_max_tokens
    
    def use_default_instruction(self):
        """Use the default system instruction."""
        default_instruction = self.config.get_value(
            ['default_settings', 'default_instruction'], 
            """You are Sumit Mondal's personal AI assistant. When responding:
1. Keep greetings brief and professional
2. Avoid repeating user's greeting phrases
3. Focus on being helpful and direct
4. Maintain a consistent, professional tone"""
        )
        self.instruction_edit.setPlainText(default_instruction)
    
    def use_general_instruction(self):
        """Use a general assistant system instruction."""
        general_instruction = """You are a helpful AI assistant designed to assist users with a wide variety of tasks and questions. Your primary goals are to:

1. Provide accurate and up-to-date information on any topic the user asks about.
2. Offer step-by-step guidance for complex tasks or processes.
3. Help brainstorm ideas and solutions for creative or problem-solving tasks.
4. Explain complex concepts in simple, easy-to-understand terms.
5. Assist with analysis and interpretation of data or information the user provides.

Always strive to be clear, concise, and helpful in your responses. If a user's query is ambiguous, ask for clarification to ensure you provide the most relevant assistance. Remember to consider ethical implications in your advice and inform the user if a task they're asking about could be harmful or illegal."""
        
        self.instruction_edit.setPlainText(general_instruction)
    
    def use_coding_instruction(self):
        """Use a coding assistant system instruction."""
        coding_instruction = """You are an expert coding assistant with extensive programming knowledge across multiple languages and frameworks. Your main responsibilities are to:

1. Provide clear, efficient, and well-documented code examples.
2. Debug and fix issues in code that users share with you.
3. Explain programming concepts and patterns clearly.
4. Help users optimize their code for better performance and readability.
5. Recommend best practices and modern approaches for development tasks.

When writing code, prioritize:
- Clarity and readability over clever optimizations
- Comprehensive error handling
- Adherence to language/framework conventions and best practices
- Security considerations
- Detailed comments for complex or non-obvious sections

For debugging issues, analyze the problem systematically and explain your reasoning while suggesting fixes. When explaining concepts, use examples to illustrate your points."""
        
        self.instruction_edit.setPlainText(coding_instruction)
    
    def save_settings(self):
        """Save current settings to configuration."""
        # Update configuration with current settings
        self.config.set_value(['default_settings', 'default_model'], self.assistant.selected_model)
        self.config.set_value(['default_settings', 'temperature'], self.assistant.temperature)
        self.config.set_value(['default_settings', 'top_p'], self.assistant.top_p)
        self.config.set_value(['default_settings', 'max_output_tokens'], self.assistant.max_output_tokens)
        self.config.set_value(['default_settings', 'default_instruction'], self.instruction_edit.toPlainText())
        
        # Save configuration
        self.config.save_config()
        
        # Emit signal
        self.settings_updated.emit()
        
        # Show confirmation
        QMessageBox.information(
            self,
            "Settings Saved",
            "Settings have been saved as defaults."
        )
    
    def start_chat(self):
        """Start a new chat session with current settings."""
        # Update assistant
        self.assistant.system_instruction = self.instruction_edit.toPlainText()
        
        # Emit signal
        self.chat_started.emit()
    
    def refresh_models(self):
        """Refresh the model list from Vertex AI."""
        # Disable button during refresh
        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("Refreshing...")
        
        # Refresh models
        if self.model_registry.discover_models():
            # Update model combo box
            self.model_combo.clear()
            self.model_id_map.clear()
            
            # Get display names of available models
            model_display_names = []
            
            for model in self.model_registry.get_models():
                model_id = model['id']
                display_name = model.get('display_name', model_id)
                model_display_names.append(display_name)
                self.model_id_map[display_name] = model_id
            
            # Add models to combo box
            self.model_combo.addItems(model_display_names)
            
            # Set current model
            current_model_display = self.model_registry.get_model_by_id(
                self.assistant.selected_model
            ).get('display_name', self.assistant.selected_model)
            
            self.model_combo.setCurrentText(current_model_display)
            
            # Show confirmation
            QMessageBox.information(
                self,
                "Models Refreshed",
                f"Successfully refreshed model list. Found {len(model_display_names)} models."
            )
        else:
            # Show error
            QMessageBox.warning(
                self,
                "Refresh Failed",
                "Failed to refresh model list. Please check your connection and authentication."
            )
        
        # Re-enable button
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("Refresh Model List")
    
    def focus_start_button(self):
        """Focus the start chat button."""
        self.start_button.setFocus()
