#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Model Registry for LostMind AI Gemini Chat Assistant

This module handles discovery and management of available Gemini models
through the Vertex AI API. It maintains information about models and their capabilities.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from google.cloud import aiplatform
from google import genai

from config_manager import ConfigManager

class ModelRegistry:
    """
    Model Registry maintains information about available models and their capabilities.
    
    It handles:
    - Model discovery via Vertex AI API
    - Static model configuration from the config file
    - Mapping between model IDs, display names, and capabilities
    - Detecting model feature support
    """
    
    def __init__(self, config: ConfigManager):
        """
        Initialize the model registry.
        
        Args:
            config (ConfigManager): Application configuration manager.
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.models = []
        self.client = None
        
        # Load initial models from config
        self._load_models_from_config()
    
    def _load_models_from_config(self):
        """Load initial model information from the configuration file."""
        self.models = self.config.get_value(['models'], [])
        if not self.models:
            self.logger.warning("No models found in configuration")
    
    def initialize_client(self) -> bool:
        """
        Initialize the GenAI client for Vertex AI.
        
        Returns:
            bool: True if client was initialized successfully, False otherwise.
        """
        try:
            project_id = self.config.get_value(['authentication', 'vertex_ai', 'project_id'])
            location = self.config.get_value(['authentication', 'vertex_ai', 'location'])
            
            if not project_id or not location:
                self.logger.error("Missing project ID or location for Vertex AI")
                return False
            
            # Initialize Vertex AI
            aiplatform.init(project=project_id, location=location)
            
            # Create GenAI client
            self.client = genai.Client(
                vertexai=True,
                project=project_id,
                location=location,
                http_options={'api_version': 'v1'}
            )
            
            self.logger.info(f"GenAI client initialized with project={project_id}, location={location}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize GenAI client: {str(e)}")
            return False
    
    def discover_models(self) -> bool:
        """
        Discover available models from Vertex AI API and update model list.
        
        Returns:
            bool: True if discovery was successful, False otherwise.
        """
        if not self.client:
            if not self.initialize_client():
                return False
        
        try:
            self.logger.info("Discovering models from Vertex AI...")
            
            # Retrieve available models from Vertex AI
            api_models = list(self.client.models.list())
            
            # Process discovered models
            discovered_models = []
            for model in api_models:
                # Only process Gemini models (excluding vision-specific models)
                if "gemini" in model.name.lower() and not model.name.endswith("vision"):
                    model_info = self._process_model(model)
                    if model_info:
                        discovered_models.append(model_info)
            
            if not discovered_models:
                self.logger.warning("No Gemini models found in Vertex AI")
                return False
            
            # Update the models list, preserving models from config
            self._merge_discovered_models(discovered_models)
            
            self.logger.info(f"Discovered {len(discovered_models)} models from Vertex AI")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to discover models: {str(e)}")
            return False
    
    def _process_model(self, model) -> Optional[Dict[str, Any]]:
        """
        Process a model from the API and extract relevant information.
        
        Args:
            model: Model object from the API.
        
        Returns:
            Optional[Dict[str, Any]]: Model information dict, or None if processing failed.
        """
        try:
            # Extract model ID from full name
            if hasattr(model, "publisher_model") and model.publisher_model:
                # This is a tuned model
                model_id = model.name  # The full resource name for tuned models
                model_type = "tuned"
                display_name = model.display_name if hasattr(model, "display_name") else model_id.split("/")[-1]
                # For tuned models, the publisher_model is the base model
                base_model = model.publisher_model.split("/")[-1] if model.publisher_model else None
            else:
                # This is a base model
                if "/" in model.name:
                    model_id = model.name.split('/')[-1]
                else:
                    model_id = model.name
                model_type = "base"
                display_name = self._get_friendly_model_name(model_id)
                base_model = None
            
            # Determine supported methods
            supported_methods = self._detect_model_capabilities(model_id)
            
            return {
                "id": model_id,
                "display_name": display_name,
                "description": getattr(model, "description", ""),
                "type": model_type,
                "base_model": base_model,
                "supported_methods": supported_methods
            }
            
        except Exception as e:
            self.logger.error(f"Failed to process model {model.name}: {str(e)}")
            return None
    
    def _merge_discovered_models(self, discovered_models: List[Dict[str, Any]]):
        """
        Merge discovered models with those from config.
        
        Args:
            discovered_models (List[Dict[str, Any]]): Models discovered from API.
        """
        # Create a map of existing models by ID
        existing_models = {model['id']: model for model in self.models}
        
        # Merge discovered models with existing ones
        for model in discovered_models:
            model_id = model['id']
            if model_id in existing_models:
                # Update existing model, preserving user-configured fields
                existing_models[model_id].update(model)
            else:
                # Add new model
                self.models.append(model)
    
    def _detect_model_capabilities(self, model_id: str) -> List[str]:
        """
        Detect capabilities of a model based on its ID and version.
        
        Args:
            model_id (str): Model ID.
        
        Returns:
            List[str]: List of supported capabilities.
        """
        capabilities = ["generateContent", "countTokens"]
        
        # Add streaming for all Gemini models
        capabilities.append("streamGenerateContent")
        
        # Add Google Search capability for Gemini 2.0 models
        if "gemini-2" in model_id:
            capabilities.append("googleSearch")
        
        # Add thinking mode for Pro models
        if "pro" in model_id:
            capabilities.append("thinkingMode")
        
        return capabilities
    
    def _get_friendly_model_name(self, model_id: str) -> str:
        """
        Generate a user-friendly display name for a model.
        
        Args:
            model_id (str): Model ID.
        
        Returns:
            str: User-friendly display name.
        """
        parts = model_id.split('-')
        
        if len(parts) >= 3:
            # Handle different model naming patterns
            if parts[0] == "gemini":
                version = parts[1]
                variant = parts[2].capitalize()
                if len(parts) > 3:
                    suffix = f" {'-'.join(parts[3:])}"
                else:
                    suffix = ""
                return f"Gemini {version} {variant}{suffix}"
        
        # Fallback to prettified ID
        return model_id.replace('-', ' ').title()
    
    def get_models(self) -> List[Dict[str, Any]]:
        """
        Get the list of available models.
        
        Returns:
            List[Dict[str, Any]]: List of model information dicts.
        """
        return self.models
    
    def get_model_by_id(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Get model information by ID.
        
        Args:
            model_id (str): Model ID to look up.
        
        Returns:
            Optional[Dict[str, Any]]: Model information or None if not found.
        """
        for model in self.models:
            if model['id'] == model_id:
                return model
        return None
    
    def get_default_model(self) -> Dict[str, Any]:
        """
        Get the default model based on config.
        
        Returns:
            Dict[str, Any]: Default model information dict.
        """
        default_model_id = self.config.get_value(['default_settings', 'default_model'])
        
        # Try to find the default model
        if default_model_id:
            for model in self.models:
                if model['id'] == default_model_id:
                    return model
        
        # If not found, return the first model in the list
        if self.models:
            return self.models[0]
        
        # If no models available, return a placeholder
        return {
            "id": "gemini-1.5-pro-002",
            "display_name": "Gemini 1.5 Pro (Default)",
            "type": "base",
            "supported_methods": ["generateContent", "streamGenerateContent", "countTokens"]
        }
    
    def get_model_ids(self) -> List[str]:
        """
        Get a list of all model IDs.
        
        Returns:
            List[str]: List of model IDs.
        """
        return [model['id'] for model in self.models]
    
    def get_model_display_names(self) -> List[str]:
        """
        Get a list of all model display names.
        
        Returns:
            List[str]: List of model display names.
        """
        return [model['display_name'] for model in self.models]
    
    def get_model_id_from_display_name(self, display_name: str) -> Optional[str]:
        """
        Get model ID from display name.
        
        Args:
            display_name (str): Display name to look up.
        
        Returns:
            Optional[str]: Model ID or None if not found.
        """
        for model in self.models:
            if model['display_name'] == display_name:
                return model['id']
        return None
    
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
    
    def save_models_to_config(self) -> bool:
        """
        Save the current models to the configuration.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            self.config.set_value(['models'], self.models)
            return self.config.save_config()
        except Exception as e:
            self.logger.error(f"Failed to save models to config: {str(e)}")
            return False
