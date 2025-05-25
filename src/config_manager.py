#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration Manager for LostMind AI Gemini Chat Assistant

This module handles loading, validating, and providing access to application configuration.
It supports environment variable overrides and provides change notifications for UI updates.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

class ConfigManager:
    """
    Configuration manager for the application.
    Handles loading, validation, and access to configuration values.
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_path (str, optional): Path to the configuration file.
                If None, will look in standard locations.
        """
        self.logger = logging.getLogger(__name__)
        self.config_data = {}
        self.change_callbacks = []
        
        # Determine config path
        if config_path is None:
            base_dir = Path(__file__).parent.parent
            config_path = os.path.join(base_dir, 'config', 'config.json')
        
        self.config_path = config_path
        self.load_config()
    
    def load_config(self) -> bool:
        """
        Load configuration from file and apply environment variable overrides.
        
        Returns:
            bool: True if config was loaded successfully, False otherwise.
        """
        try:
            if not os.path.exists(self.config_path):
                self.logger.error(f"Configuration file not found: {self.config_path}")
                return False
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)
            
            # Apply environment variable overrides
            self._apply_env_overrides()
            
            # Validate configuration
            if not self._validate_config():
                self.logger.error("Configuration validation failed")
                return False
            
            self.logger.info(f"Configuration loaded successfully from {self.config_path}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {str(e)}")
            return False
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides to configuration."""
        # Project ID override
        project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
        if project_id:
            self.set_value(['authentication', 'vertex_ai', 'project_id'], project_id)
        
        # Location override
        location = os.environ.get('GOOGLE_CLOUD_LOCATION')
        if location:
            self.set_value(['authentication', 'vertex_ai', 'location'], location)
        
        # Logging level override
        log_level = os.environ.get('LOSTMIND_LOG_LEVEL')
        if log_level:
            self.set_value(['advanced', 'logging_level'], log_level)
    
    def _validate_config(self) -> bool:
        """
        Validate the configuration structure.
        
        Returns:
            bool: True if the configuration is valid, False otherwise.
        """
        required_sections = ['authentication', 'models', 'ui', 'file_handling', 'features']
        
        for section in required_sections:
            if section not in self.config_data:
                self.logger.error(f"Missing required configuration section: {section}")
                return False
        
        # Validate authentication section
        auth = self.config_data.get('authentication', {})
        if 'vertex_ai' not in auth:
            self.logger.error("Missing Vertex AI authentication configuration")
            return False
        
        vertex_ai = auth.get('vertex_ai', {})
        if 'project_id' not in vertex_ai or 'location' not in vertex_ai:
            self.logger.error("Missing required Vertex AI configuration parameters")
            return False
        
        # Validate models section
        models = self.config_data.get('models', [])
        if not models:
            self.logger.error("No models configured")
            return False
        
        return True
    
    def get_value(self, path: List[str], default: Any = None) -> Any:
        """
        Get a configuration value by path.
        
        Args:
            path (List[str]): Path to the configuration value.
            default (Any, optional): Default value if not found.
        
        Returns:
            Any: The configuration value.
        """
        current = self.config_data
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current
    
    def set_value(self, path: List[str], value: Any) -> bool:
        """
        Set a configuration value by path.
        
        Args:
            path (List[str]): Path to the configuration value.
            value (Any): Value to set.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            current = self.config_data
            for key in path[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            
            current[path[-1]] = value
            
            # Notify listeners
            self._notify_change(path, value)
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to set configuration value: {str(e)}")
            return False
    
    def save_config(self) -> bool:
        """
        Save the current configuration to file.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2)
            
            self.logger.info(f"Configuration saved to {self.config_path}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {str(e)}")
            return False
    
    def register_change_callback(self, callback):
        """
        Register a callback to be called when the configuration changes.
        
        Args:
            callback: Function to call when configuration changes.
                Function signature: callback(path, value)
        """
        if callback not in self.change_callbacks:
            self.change_callbacks.append(callback)
    
    def unregister_change_callback(self, callback):
        """
        Unregister a previously registered callback.
        
        Args:
            callback: Function to unregister.
        """
        if callback in self.change_callbacks:
            self.change_callbacks.remove(callback)
    
    def _notify_change(self, path: List[str], value: Any):
        """
        Notify listeners of a configuration change.
        
        Args:
            path (List[str]): Path to the changed configuration value.
            value (Any): New value.
        """
        for callback in self.change_callbacks:
            try:
                callback(path, value)
            except Exception as e:
                self.logger.error(f"Error in configuration change callback: {str(e)}")
    
    def get_model_by_id(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Get model configuration by ID.
        
        Args:
            model_id (str): Model ID to look up.
        
        Returns:
            Optional[Dict[str, Any]]: Model configuration dict, or None if not found.
        """
        models = self.get_value(['models'], [])
        for model in models:
            if model.get('id') == model_id:
                return model
        return None
    
    def get_model_display_name(self, model_id: str) -> str:
        """
        Get a model's display name by ID.
        
        Args:
            model_id (str): Model ID to look up.
        
        Returns:
            str: Display name of the model, or the ID if not found.
        """
        model = self.get_model_by_id(model_id)
        if model and 'display_name' in model:
            return model['display_name']
        return model_id
    
    def model_supports_feature(self, model_id: str, feature: str) -> bool:
        """
        Check if a model supports a specific feature.
        
        Args:
            model_id (str): Model ID to check.
            feature (str): Feature to check for.
        
        Returns:
            bool: True if the model supports the feature, False otherwise.
        """
        model = self.get_model_by_id(model_id)
        if model and 'supported_methods' in model:
            return feature in model['supported_methods']
        return False
    
    def get_supported_file_extensions(self) -> List[str]:
        """
        Get a list of all supported file extensions.
        
        Returns:
            List[str]: List of supported file extensions (with dot prefix).
        """
        extensions = []
        file_handling = self.get_value(['file_handling', 'supported_types'], {})
        
        for type_config in file_handling.values():
            extensions.extend(type_config.get('extensions', []))
        
        return extensions
    
    def get_max_file_size(self, extension: str) -> int:
        """
        Get the maximum file size for a specific extension.
        
        Args:
            extension (str): File extension to check (with dot prefix).
        
        Returns:
            int: Maximum file size in MB, or 10 (default) if not found.
        """
        file_handling = self.get_value(['file_handling', 'supported_types'], {})
        
        for type_config in file_handling.values():
            if extension in type_config.get('extensions', []):
                return type_config.get('max_size_mb', 10)
        
        return 10  # Default
    
    def get_mime_type(self, extension: str) -> str:
        """
        Get the MIME type for a specific file extension.
        
        Args:
            extension (str): File extension to check (with dot prefix).
        
        Returns:
            str: MIME type or application/octet-stream if not found.
        """
        file_handling = self.get_value(['file_handling', 'supported_types'], {})
        
        for type_config in file_handling.values():
            mime_types = type_config.get('mime_types', {})
            if extension in mime_types:
                return mime_types[extension]
        
        return "application/octet-stream"  # Default
