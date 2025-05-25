#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
File Handler for LostMind AI Gemini Chat Assistant

This module handles file operations, validation, and processing
for various file types used in the application.
"""

import os
import re
import logging
import base64
import tempfile
from typing import Dict, Any, Optional, Tuple, List, BinaryIO
from pathlib import Path
from PIL import Image

from config_manager import ConfigManager

class FileHandler:
    """
    Handles file operations, validation, and processing.
    """
    
    def __init__(self, config: ConfigManager):
        """
        Initialize the file handler.
        
        Args:
            config (ConfigManager): Application configuration manager.
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
    
    def validate_file(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a file for use in the application.
        
        Args:
            file_path (str): Path to the file.
        
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                return False, f"File '{file_path}' not found."
            
            # Check if file is a directory
            if os.path.isdir(file_path):
                return False, f"'{file_path}' is a directory, not a file."
            
            # Check file extension
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext not in self.config.get_supported_file_extensions():
                return False, f"Unsupported file type: {file_ext}"
            
            # Check file size
            file_size = os.path.getsize(file_path)
            max_size_mb = self.config.get_max_file_size(file_ext)
            max_size_bytes = max_size_mb * 1024 * 1024
            
            if file_size > max_size_bytes:
                return False, f"File is too large ({file_size/1024/1024:.1f} MB). Maximum size is {max_size_mb} MB."
            
            return True, None
            
        except Exception as e:
            self.logger.error(f"Error validating file '{file_path}': {str(e)}")
            return False, f"Error validating file: {str(e)}"
    
    def get_file_category(self, file_path: str) -> Optional[str]:
        """
        Get the category of a file based on its extension.
        
        Args:
            file_path (str): Path to the file.
        
        Returns:
            Optional[str]: File category (image, document, video) or None if not found.
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        
        file_handling = self.config.get_value(['file_handling', 'supported_types'], {})
        for category, config in file_handling.items():
            if file_ext in config.get('extensions', []):
                return category
        
        return None
    
    def get_mime_type(self, file_path: str) -> str:
        """
        Get the MIME type for a file.
        
        Args:
            file_path (str): Path to the file.
        
        Returns:
            str: MIME type or 'application/octet-stream' if not found.
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        return self.config.get_mime_type(file_ext)
    
    def read_text_file(self, file_path: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Read a text file.
        
        Args:
            file_path (str): Path to the file.
        
        Returns:
            Tuple[bool, Optional[str], Optional[str]]: (success, content, error_message)
        """
        try:
            # Validate file
            valid, error = self.validate_file(file_path)
            if not valid:
                return False, None, error
            
            # Check if it's a text file
            category = self.get_file_category(file_path)
            if category != "document":
                return False, None, f"Not a text file: {file_path}"
            
            # Read file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return True, content, None
            
        except UnicodeDecodeError:
            self.logger.error(f"Unicode error reading file '{file_path}', trying binary mode")
            try:
                # Try binary mode with different encoding detection
                with open(file_path, 'rb') as f:
                    binary_data = f.read()
                    # Try to detect encoding
                    for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
                        try:
                            content = binary_data.decode(encoding)
                            return True, content, None
                        except UnicodeDecodeError:
                            continue
                
                return False, None, f"Could not decode file '{file_path}' with any known encoding"
                
            except Exception as e:
                self.logger.error(f"Error reading file in binary mode: {str(e)}")
                return False, None, f"Error reading file: {str(e)}"
                
        except Exception as e:
            self.logger.error(f"Error reading text file '{file_path}': {str(e)}")
            return False, None, f"Error reading file: {str(e)}"
    
    def read_binary_file(self, file_path: str) -> Tuple[bool, Optional[bytes], Optional[str]]:
        """
        Read a binary file.
        
        Args:
            file_path (str): Path to the file.
        
        Returns:
            Tuple[bool, Optional[bytes], Optional[str]]: (success, content, error_message)
        """
        try:
            # Validate file
            valid, error = self.validate_file(file_path)
            if not valid:
                return False, None, error
            
            # Read file
            with open(file_path, 'rb') as f:
                content = f.read()
            
            return True, content, None
            
        except Exception as e:
            self.logger.error(f"Error reading binary file '{file_path}': {str(e)}")
            return False, None, f"Error reading file: {str(e)}"
    
    def image_to_base64(self, image_path: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Convert an image file to base64 string.
        
        Args:
            image_path (str): Path to the image file.
        
        Returns:
            Tuple[bool, Optional[str], Optional[str]]: (success, base64_string, error_message)
        """
        try:
            # Read image
            success, binary_data, error = self.read_binary_file(image_path)
            if not success:
                return False, None, error
            
            # Convert to base64
            base64_string = base64.b64encode(binary_data).decode('utf-8')
            
            return True, base64_string, None
            
        except Exception as e:
            self.logger.error(f"Error converting image to base64: {str(e)}")
            return False, None, f"Error processing image: {str(e)}"
    
    def get_image_thumbnail(self, image_path: str, max_size: int = 300) -> Tuple[bool, Optional[Image.Image], Optional[str]]:
        """
        Create a thumbnail of an image.
        
        Args:
            image_path (str): Path to the image file.
            max_size (int, optional): Maximum dimension (width or height). Defaults to 300.
        
        Returns:
            Tuple[bool, Optional[Image.Image], Optional[str]]: (success, thumbnail, error_message)
        """
        try:
            # Validate file
            valid, error = self.validate_file(image_path)
            if not valid:
                return False, None, error
            
            # Check if it's an image
            category = self.get_file_category(image_path)
            if category != "image":
                return False, None, f"Not an image file: {image_path}"
            
            # Open and resize image
            image = Image.open(image_path)
            image.thumbnail((max_size, max_size))
            
            return True, image, None
            
        except Exception as e:
            self.logger.error(f"Error creating image thumbnail: {str(e)}")
            return False, None, f"Error processing image: {str(e)}"
    
    def validate_gcs_uri(self, gcs_uri: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a Google Cloud Storage URI.
        
        Args:
            gcs_uri (str): Google Cloud Storage URI (gs://bucket/path/to/file).
        
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        if not gcs_uri.startswith("gs://"):
            return False, f"Invalid GCS URI: {gcs_uri}. Must start with 'gs://'"
        
        # Check URI format
        pattern = r"^gs://[\w\.-]+/[\w\.-/]*[\w\.-]+$"
        if not re.match(pattern, gcs_uri):
            return False, f"Invalid GCS URI format: {gcs_uri}"
        
        return True, None
    
    def validate_youtube_url(self, youtube_url: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate a YouTube URL and extract the video ID.
        
        Args:
            youtube_url (str): YouTube video URL.
        
        Returns:
            Tuple[bool, Optional[str], Optional[str]]: (is_valid, video_id, error_message)
        """
        # YouTube URL patterns
        patterns = [
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([\w\-]+)',
            r'(?:https?:\/\/)?(?:www\.)?youtu\.be\/([\w\-]+)',
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([\w\-]+)'
        ]
        
        for pattern in patterns:
            match = re.match(pattern, youtube_url)
            if match:
                video_id = match.group(1)
                return True, video_id, None
        
        return False, None, f"Invalid YouTube URL: {youtube_url}"
    
    def extract_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from a file.
        
        Args:
            file_path (str): Path to the file.
        
        Returns:
            Dict[str, Any]: File metadata.
        """
        try:
            # Get basic file info
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_path)[1].lower()
            file_size = os.path.getsize(file_path)
            file_category = self.get_file_category(file_path)
            
            metadata = {
                "name": file_name,
                "extension": file_ext,
                "size": file_size,
                "size_formatted": self._format_file_size(file_size),
                "category": file_category,
                "mime_type": self.get_mime_type(file_path),
                "path": file_path
            }
            
            # Get additional metadata based on file type
            if file_category == "image":
                # Get image dimensions
                try:
                    with Image.open(file_path) as img:
                        metadata["dimensions"] = f"{img.width}x{img.height}"
                        metadata["format"] = img.format
                        metadata["mode"] = img.mode
                except Exception as e:
                    self.logger.warning(f"Error getting image metadata: {str(e)}")
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error extracting file metadata: {str(e)}")
            return {
                "name": os.path.basename(file_path),
                "error": str(e)
            }
    
    def _format_file_size(self, size_bytes: int) -> str:
        """
        Format file size in human-readable form.
        
        Args:
            size_bytes (int): File size in bytes.
        
        Returns:
            str: Formatted file size.
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
