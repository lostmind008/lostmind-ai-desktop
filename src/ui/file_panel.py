#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
File Panel for LostMind AI Gemini Chat Assistant

This module implements the file panel for the chat interface,
including file upload, management, and display.
"""

import os
import logging
import re
from typing import Optional, Dict, Any, List
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QListWidget, QListWidgetItem, QCheckBox,
    QGroupBox, QSizePolicy, QInputDialog, QMessageBox,
    QMenu, QToolButton, QFrame
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap, QColor, QFont, QAction

from config_manager import ConfigManager
from gemini_assistant import GeminiAssistant

class UploadedFileItem(QListWidgetItem):
    """List widget item representing an uploaded file."""
    
    def __init__(self, file_info: Dict[str, Any]):
        """
        Initialize an uploaded file item.
        
        Args:
            file_info (Dict[str, Any]): Information about the uploaded file.
        """
        super().__init__()
        
        self.file_info = file_info
        self.display_name = file_info.get("display_name", "Unknown file")
        self.file_path = file_info.get("file_path", "")
        self.file_type = file_info.get("file_type", "unknown")
        self.file_size = file_info.get("size", 0)
        
        # Set display text
        self.setText(self.display_name)
        
        # Set icon based on file type
        self.set_icon()
        
        # Set tooltip with file details
        self.set_tooltip()
    
    def set_icon(self):
        """Set the appropriate icon based on file type."""
        if self.file_type == "image":
            self.setIcon(QIcon.fromTheme("image-x-generic"))
        elif self.file_type == "document":
            self.setIcon(QIcon.fromTheme("text-x-generic"))
        elif self.file_type == "video":
            self.setIcon(QIcon.fromTheme("video-x-generic"))
        else:
            self.setIcon(QIcon.fromTheme("unknown"))
    
    def set_tooltip(self):
        """Set tooltip with file details."""
        size_str = self.format_file_size(self.file_size)
        
        if self.file_path.startswith("gs://"):
            location = "Google Cloud Storage"
        elif "youtube.com" in self.file_path or "youtu.be" in self.file_path:
            location = "YouTube"
        else:
            location = "Local file"
        
        tooltip = f"""
            <b>{self.display_name}</b><br>
            Type: {self.file_type.capitalize()}<br>
            Size: {size_str}<br>
            Location: {location}<br>
            Path: {self.file_path}
        """
        
        self.setToolTip(tooltip)
    
    def format_file_size(self, size_bytes: int) -> str:
        """
        Format file size in human-readable form.
        
        Args:
            size_bytes (int): File size in bytes.
        
        Returns:
            str: Formatted file size.
        """
        if size_bytes == 0:
            return "Unknown"
            
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

class FilePanel(QWidget):
    """
    Panel for managing uploaded files.
    
    Features:
    - File upload from local disk
    - Google Cloud Storage file upload
    - YouTube video upload
    - File management (view, remove)
    - Include/exclude files in messages
    """
    
    # Signals
    file_uploaded = pyqtSignal(dict)
    files_cleared = pyqtSignal()
    
    def __init__(self, config: ConfigManager, assistant: GeminiAssistant):
        """
        Initialize the file panel.
        
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
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(10)
        
        # File upload section
        upload_group = QGroupBox("Upload Files")
        upload_layout = QVBoxLayout(upload_group)
        
        # Upload buttons
        buttons_layout = QHBoxLayout()
        
        # Local file button
        self.local_button = QPushButton("Local File")
        self.local_button.clicked.connect(self.upload_local_file)
        buttons_layout.addWidget(self.local_button)
        
        # GCS file button
        self.gcs_button = QPushButton("GCS File")
        self.gcs_button.clicked.connect(self.upload_gcs_file)
        # Only show if GCS support is enabled
        if self.config.get_value(['features', 'gcs_support'], True):
            buttons_layout.addWidget(self.gcs_button)
        
        # YouTube button
        self.youtube_button = QPushButton("YouTube")
        self.youtube_button.clicked.connect(self.upload_youtube_video)
        # Only show if YouTube support is enabled
        if self.config.get_value(['features', 'youtube_support'], True):
            buttons_layout.addWidget(self.youtube_button)
        
        upload_layout.addLayout(buttons_layout)
        
        self.layout.addWidget(upload_group)
        
        # File list section
        files_group = QGroupBox("Uploaded Files")
        files_layout = QVBoxLayout(files_group)
        
        # Include files checkbox
        self.include_checkbox = QCheckBox("Include files in messages")
        self.include_checkbox.setChecked(True)
        self.include_checkbox.setToolTip("Include files in messages when sending")
        files_layout.addWidget(self.include_checkbox)
        
        # File list
        self.file_list = QListWidget()
        self.file_list.setMinimumHeight(150)
        self.file_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.file_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_list.customContextMenuRequested.connect(self.show_context_menu)
        self.file_list.itemDoubleClicked.connect(self.show_file_details)
        files_layout.addWidget(self.file_list)
        
        # File actions
        actions_layout = QHBoxLayout()
        
        # Remove button
        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self.remove_selected_files)
        self.remove_button.setEnabled(False)
        actions_layout.addWidget(self.remove_button)
        
        # Clear button
        self.clear_button = QPushButton("Clear All")
        self.clear_button.clicked.connect(self.clear_files)
        self.clear_button.setEnabled(False)
        actions_layout.addWidget(self.clear_button)
        
        files_layout.addLayout(actions_layout)
        
        self.layout.addWidget(files_group)
        
        # Add spacer
        self.layout.addStretch()
        
        # Connect signals
        self.file_list.itemSelectionChanged.connect(self.update_button_states)
        
        # Load existing files
        self.refresh_file_list()
    
    def upload_local_file(self):
        """Upload a file from local disk."""
        # Get file size limits from config
        file_extensions = []
        for category, config in self.config.get_value(['file_handling', 'supported_types'], {}).items():
            file_extensions.extend(config.get('extensions', []))
        
        # Create filter string
        filter_str = "All Supported Files ("
        filter_str += " ".join(["*" + ext for ext in file_extensions])
        filter_str += ")"
        
        for category, config in self.config.get_value(['file_handling', 'supported_types'], {}).items():
            extensions = config.get('extensions', [])
            if extensions:
                filter_str += ";;" + category.capitalize() + " Files ("
                filter_str += " ".join(["*" + ext for ext in extensions])
                filter_str += ")"
        
        filter_str += ";;All Files (*)"
        
        # Open file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File to Upload",
            "",
            filter_str
        )
        
        if not file_path:
            return
        
        # Upload file
        success, error, uploaded_file = self.assistant.upload_file(file_path)
        
        if success:
            # Add to list
            self.add_file_to_list(uploaded_file)
            
            # Emit signal
            self.file_uploaded.emit(uploaded_file.to_dict())
        else:
            QMessageBox.warning(
                self,
                "Upload Failed",
                f"Failed to upload file: {error}"
            )
    
    def upload_gcs_file(self):
        """Upload a file from Google Cloud Storage."""
        # Show input dialog
        gcs_uri, ok = QInputDialog.getText(
            self,
            "GCS File Upload",
            "Enter Google Cloud Storage URI (gs://bucket/path/to/file):"
        )
        
        if not ok or not gcs_uri:
            return
        
        # Validate URI format
        if not gcs_uri.startswith("gs://"):
            QMessageBox.warning(
                self,
                "Invalid URI",
                "GCS URI must start with 'gs://'."
            )
            return
        
        # Upload file
        success, error, uploaded_file = self.assistant.upload_gcs_file(gcs_uri)
        
        if success:
            # Add to list
            self.add_file_to_list(uploaded_file)
            
            # Emit signal
            self.file_uploaded.emit(uploaded_file.to_dict())
        else:
            QMessageBox.warning(
                self,
                "Upload Failed",
                f"Failed to upload GCS file: {error}"
            )
    
    def upload_youtube_video(self):
        """Upload a YouTube video."""
        # Show input dialog
        youtube_url, ok = QInputDialog.getText(
            self,
            "YouTube Video Upload",
            "Enter YouTube URL:"
        )
        
        if not ok or not youtube_url:
            return
        
        # Validate URL
        youtube_regex = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com|youtu\.be)\/(?:watch\?v=)?([^\s&]+)'
        if not re.match(youtube_regex, youtube_url):
            QMessageBox.warning(
                self,
                "Invalid URL",
                "Please enter a valid YouTube URL."
            )
            return
        
        # Upload video
        success, error, uploaded_file = self.assistant.upload_youtube_video(youtube_url)
        
        if success:
            # Add to list
            self.add_file_to_list(uploaded_file)
            
            # Emit signal
            self.file_uploaded.emit(uploaded_file.to_dict())
        else:
            QMessageBox.warning(
                self,
                "Upload Failed",
                f"Failed to upload YouTube video: {error}"
            )
    
    def add_file_to_list(self, uploaded_file):
        """
        Add an uploaded file to the list.
        
        Args:
            uploaded_file: Uploaded file object.
        """
        # Create list item
        item = UploadedFileItem(uploaded_file.to_dict())
        
        # Add to list
        self.file_list.addItem(item)
        
        # Update button states
        self.update_button_states()
    
    def refresh_file_list(self):
        """Refresh the file list from assistant's uploaded files."""
        # Clear list
        self.file_list.clear()
        
        # Add files
        for file in self.assistant.uploaded_files:
            self.add_file_to_list(file)
        
        # Update button states
        self.update_button_states()
    
    def update_button_states(self):
        """Update button enabled states based on selection."""
        has_files = self.file_list.count() > 0
        has_selection = len(self.file_list.selectedItems()) > 0
        
        self.remove_button.setEnabled(has_selection)
        self.clear_button.setEnabled(has_files)
    
    def remove_selected_files(self):
        """Remove selected files from the list."""
        selected_items = self.file_list.selectedItems()
        
        if not selected_items:
            return
        
        # Confirm removal
        if len(selected_items) == 1:
            msg = f"Remove file '{selected_items[0].display_name}'?"
        else:
            msg = f"Remove {len(selected_items)} files?"
        
        reply = QMessageBox.question(
            self,
            "Remove Files",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Remove files
        for item in selected_items:
            # Remove from assistant
            self.assistant.remove_uploaded_file(item.file_path)
            
            # Remove from list
            row = self.file_list.row(item)
            self.file_list.takeItem(row)
        
        # Update button states
        self.update_button_states()
    
    def clear_files(self):
        """Clear all files from the list."""
        if self.file_list.count() == 0:
            return
        
        # Confirm clear
        reply = QMessageBox.question(
            self,
            "Clear Files",
            "Remove all uploaded files?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Clear files
        self.file_list.clear()
        self.assistant.clear_uploaded_files()
        
        # Update button states
        self.update_button_states()
        
        # Emit signal
        self.files_cleared.emit()
    
    def show_context_menu(self, position):
        """
        Show context menu for file list.
        
        Args:
            position: Position where to show the menu.
        """
        # Get selected items
        selected_items = self.file_list.selectedItems()
        
        if not selected_items:
            return
        
        # Create menu
        menu = QMenu(self)
        
        # Remove action
        remove_action = QAction("Remove", self)
        remove_action.triggered.connect(self.remove_selected_files)
        menu.addAction(remove_action)
        
        # Details action
        if len(selected_items) == 1:
            details_action = QAction("Show Details", self)
            details_action.triggered.connect(lambda: self.show_file_details(selected_items[0]))
            menu.addAction(details_action)
        
        # Open action for local files
        if len(selected_items) == 1 and os.path.exists(selected_items[0].file_path):
            open_action = QAction("Open File", self)
            open_action.triggered.connect(lambda: self.open_file(selected_items[0].file_path))
            menu.addAction(open_action)
        
        # Show menu at position
        menu.exec(self.file_list.mapToGlobal(position))
    
    def show_file_details(self, item):
        """
        Show details of a file.
        
        Args:
            item: File list item.
        """
        if isinstance(item, QListWidgetItem):
            # Check if it's our custom class
            if not hasattr(item, 'file_info'):
                return
            
            # Build details string
            details = f"<b>File:</b> {item.display_name}<br>"
            details += f"<b>Type:</b> {item.file_type.capitalize()}<br>"
            
            if item.file_size > 0:
                details += f"<b>Size:</b> {item.format_file_size(item.file_size)}<br>"
            
            details += f"<b>Path:</b> {item.file_path}<br>"
            
            if hasattr(item, 'file_info') and 'timestamp' in item.file_info:
                timestamp = item.file_info['timestamp']
                if isinstance(timestamp, str):
                    details += f"<b>Uploaded:</b> {timestamp}<br>"
                elif hasattr(timestamp, 'strftime'):
                    details += f"<b>Uploaded:</b> {timestamp.strftime('%Y-%m-%d %H:%M:%S')}<br>"
            
            # Show details
            QMessageBox.information(
                self,
                "File Details",
                details
            )
    
    def open_file(self, file_path):
        """
        Open a file with the default application.
        
        Args:
            file_path (str): Path to the file.
        """
        if not os.path.exists(file_path):
            QMessageBox.warning(
                self,
                "File Not Found",
                f"The file '{file_path}' does not exist."
            )
            return
        
        try:
            from PyQt6.QtGui import QDesktopServices
            from PyQt6.QtCore import QUrl
            
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
        except Exception as e:
            self.logger.error(f"Error opening file: {str(e)}")
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to open file: {str(e)}"
            )
    
    def get_include_files(self) -> bool:
        """
        Get whether to include files in messages.
        
        Returns:
            bool: Whether to include files.
        """
        return self.include_checkbox.isChecked()
