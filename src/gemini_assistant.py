#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gemini Assistant for LostMind AI Gemini Chat Assistant

This module handles interactions with the Gemini models through Vertex AI,
including chat sessions, message processing, and file handling.
"""

import os
import re
import json
import logging
import traceback
import base64
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Callable, Union
from pathlib import Path

from google import genai
from google.genai import types

from config_manager import ConfigManager
from model_registry import ModelRegistry

class UploadedFile:
    """Class to represent an uploaded file with metadata."""
    
    def __init__(self, file_path: str, part: Any, display_name: str, file_type: str, size: int):
        """
        Initialize an uploaded file.
        
        Args:
            file_path (str): Path to the file.
            part (Any): File part for GenAI API.
            display_name (str): Display name for the file.
            file_type (str): Type of file (image, document, etc.).
            size (int): File size in bytes.
        """
        self.file_path = file_path
        self.part = part
        self.display_name = display_name
        self.file_type = file_type
        self.size = size
        self.timestamp = datetime.now()
    
    def get_size_str(self) -> str:
        """Get human-readable file size."""
        kb = self.size / 1024
        if kb < 1024:
            return f"{kb:.1f} KB"
        mb = kb / 1024
        return f"{mb:.1f} MB"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "file_path": self.file_path,
            "display_name": self.display_name,
            "file_type": self.file_type,
            "size": self.size,
            "timestamp": self.timestamp.isoformat()
        }

class ChatMessage:
    """Class to represent a chat message."""
    
    def __init__(self, content: str, role: str, is_visible: bool = True, timestamp: datetime = None):
        """
        Initialize a chat message.
        
        Args:
            content (str): Message content.
            role (str): Message role (user, ai, system).
            is_visible (bool, optional): Whether the message is visible in the chat. 
                Defaults to True.
            timestamp (datetime, optional): Message timestamp. 
                Defaults to current time.
        """
        self.content = content
        self.role = role
        self.is_visible = is_visible
        self.timestamp = timestamp or datetime.now()
        self.used_search = False  # Whether Google Search was used
        self.has_error = False    # Whether there was an error
        self.response_time = 0.0  # Response time in seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "content": self.content,
            "role": self.role,
            "is_visible": self.is_visible,
            "timestamp": self.timestamp.isoformat(),
            "used_search": self.used_search,
            "has_error": self.has_error,
            "response_time": self.response_time
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatMessage':
        """Create a ChatMessage from a dictionary."""
        msg = cls(
            content=data["content"],
            role=data["role"],
            is_visible=data.get("is_visible", True),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else None
        )
        msg.used_search = data.get("used_search", False)
        msg.has_error = data.get("has_error", False)
        msg.response_time = data.get("response_time", 0.0)
        return msg

class GeminiAssistant:
    """
    Core class for interacting with Gemini models.
    
    Handles:
    - Authentication with Vertex AI
    - Chat sessions and message processing
    - File uploads and handling
    - Streaming and non-streaming responses
    - Error handling and recovery
    """
    
    def __init__(self, config: ConfigManager, model_registry: ModelRegistry):
        """
        Initialize the Gemini Assistant.
        
        Args:
            config (ConfigManager): Application configuration manager.
            model_registry (ModelRegistry): Model registry for model information.
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.model_registry = model_registry
        
        # Initialize variables
        self.chat_history = []
        self.uploaded_files = []
        self.client = None
        self.chat = None
        
        # Settings
        self.selected_model = self.config.get_value(['default_settings', 'default_model'])
        self.system_instruction = self.config.get_value(
            ['default_settings', 'default_instruction'], 
            "You are a helpful AI assistant."
        )
        self.temperature = self.config.get_value(['default_settings', 'temperature'], 0.7)
        self.top_p = self.config.get_value(['default_settings', 'top_p'], 0.95)
        self.max_output_tokens = self.config.get_value(['default_settings', 'max_output_tokens'], 8192)
        
        # Feature flags
        self.streaming = self.config.get_value(['features', 'streaming'], True)
        self.use_search = self.config.get_value(['features', 'search_grounding'], True)
        self.thinking_mode = False
        
        # Debug flags
        self.debug_search = False
    
    def initialize(self) -> bool:
        """
        Initialize the Gemini client and prepare for interaction.
        
        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        try:
            # Ensure model registry is initialized with client
            if not self.model_registry.client:
                if not self.model_registry.initialize_client():
                    self.logger.error("Failed to initialize model registry client")
                    return False
            
            # Use the same client
            self.client = self.model_registry.client
            
            # Check if selected model exists
            if not self.model_registry.get_model_by_id(self.selected_model):
                default_model = self.model_registry.get_default_model()
                self.selected_model = default_model['id']
                self.logger.warning(f"Selected model not found, using default: {self.selected_model}")
            
            self.logger.info(f"Gemini Assistant initialized with model: {self.selected_model}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Gemini Assistant: {str(e)}")
            return False
    
    def start_chat(self) -> Tuple[bool, Optional[str]]:
        """
        Start a new chat session with the current settings.
        
        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        try:
            # Ensure client is initialized
            if not self.client:
                if not self.initialize():
                    return False, "Failed to initialize Gemini client"
            
            # Clear history
            self.chat_history = []
            
            # Add system instruction to history
            system_msg = ChatMessage(
                content=self.system_instruction,
                role="user",
                is_visible=False
            )
            self.chat_history.append(system_msg)
            
            # Process system instruction
            try:
                # First try to create a chat session
                supports_chat = self.model_registry.model_supports_feature(
                    self.selected_model, "createChatSession"
                )
                
                if supports_chat:
                    self.logger.info(f"Creating chat session with model: {self.selected_model}")
                    self.chat = self.client.chats.create(model=self.selected_model)
                    
                    # Process system instruction in chat
                    system_content = types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=self.system_instruction)]
                    )
                    
                    generation_config = self._create_generation_config()
                    response = self.client.models.generate_content(
                        model=self.selected_model,
                        contents=[system_content],
                        config=generation_config
                    )
                    
                    # Add system response to history
                    system_response = ChatMessage(
                        content=response.text,
                        role="ai",
                        is_visible=False
                    )
                    self.chat_history.append(system_response)
                    
                else:
                    # No chat session support, use generate_content
                    self.chat = None
                    self.logger.info(f"Using generate_content mode for model: {self.selected_model}")
                    
                    # Process system instruction
                    system_content = types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=self.system_instruction)]
                    )
                    
                    generation_config = self._create_generation_config()
                    response = self.client.models.generate_content(
                        model=self.selected_model,
                        contents=[system_content],
                        config=generation_config
                    )
                    
                    # Add system response to history
                    system_response = ChatMessage(
                        content=response.text,
                        role="ai",
                        is_visible=False
                    )
                    self.chat_history.append(system_response)
                
                self.logger.info("Chat started successfully")
                return True, None
                
            except Exception as e:
                self.logger.error(f"Failed to process system instruction: {str(e)}")
                
                # Fallback to generate_content mode
                self.chat = None
                self.logger.info("Using generate_content mode without system instruction")
                
                # Add placeholder system response
                system_response = ChatMessage(
                    content="Ready to assist you.",
                    role="ai",
                    is_visible=False
                )
                self.chat_history.append(system_response)
                
                return True, f"Warning: {str(e)}"
                
        except Exception as e:
            error_message = f"Failed to start chat: {str(e)}"
            self.logger.error(error_message)
            return False, error_message
    
    def _create_generation_config(self, include_safety_settings: bool = True) -> types.GenerateContentConfig:
        """
        Create a generation configuration with current settings.
        
        Args:
            include_safety_settings (bool, optional): Whether to include safety settings.
                Defaults to True.
        
        Returns:
            types.GenerateContentConfig: Generation configuration.
        """
        config = types.GenerateContentConfig(
            temperature=self.temperature,
            top_p=self.top_p,
            max_output_tokens=self.max_output_tokens,
            response_modalities=["TEXT"]
        )
        
        # Add safety settings if requested
        if include_safety_settings:
            config.safety_settings = [
                types.SafetySetting(
                    category="HARM_CATEGORY_HATE_SPEECH",
                    threshold="OFF"
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_DANGEROUS_CONTENT",
                    threshold="OFF"
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    threshold="OFF"
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_HARASSMENT",
                    threshold="OFF"
                )
            ]
        
        return config
    
    def get_visible_chat_history(self) -> List[ChatMessage]:
        """
        Get only the visible messages in the chat history.
        
        Returns:
            List[ChatMessage]: List of visible messages.
        """
        return [msg for msg in self.chat_history if msg.is_visible]
    
    def send_message(
        self, 
        user_input: str, 
        include_files: bool = True,
        streaming_callback: Optional[Callable[[str], None]] = None
    ) -> Tuple[bool, Optional[str], Optional[ChatMessage]]:
        """
        Send a message to the model and get the response.
        
        Args:
            user_input (str): User message text.
            include_files (bool, optional): Whether to include uploaded files. 
                Defaults to True.
            streaming_callback (Callable[[str], None], optional): Callback for streaming. 
                Defaults to None.
        
        Returns:
            Tuple[bool, Optional[str], Optional[ChatMessage]]: 
                (success, error_message, response_message)
        """
        start_time = datetime.now()
        
        try:
            # Add user message to history
            user_message = ChatMessage(
                content=user_input,
                role="user",
                is_visible=True
            )
            self.chat_history.append(user_message)
            
            # Determine if we should use search grounding
            use_search = (
                self.use_search and 
                "gemini-2" in self.selected_model and
                self.model_registry.model_supports_feature(self.selected_model, "googleSearch")
            )
            
            if use_search and self.debug_search:
                self.logger.info("Google Search grounding will be enabled for this request")
            
            # Get response based on mode (chat session or generate_content)
            if self.chat:
                response = self._send_message_chat_session(
                    user_input, 
                    include_files, 
                    use_search,
                    streaming_callback
                )
            else:
                response = self._send_message_generate_content(
                    user_input, 
                    include_files, 
                    use_search,
                    streaming_callback
                )
            
            # Calculate response time
            response_time = (datetime.now() - start_time).total_seconds()
            
            # Add AI response to history
            response_message = ChatMessage(
                content=response,
                role="ai",
                is_visible=True
            )
            response_message.response_time = response_time
            
            # Detect if search was used
            response_message.used_search = self._detect_search_usage(response)
            
            self.chat_history.append(response_message)
            
            self.logger.info(f"Response received in {response_time:.2f} seconds")
            if response_message.used_search:
                self.logger.info("Google Search was used in the response")
            
            return True, None, response_message
            
        except Exception as e:
            error_message = f"Failed to send message: {str(e)}"
            self.logger.error(error_message)
            
            # Calculate response time even for errors
            response_time = (datetime.now() - start_time).total_seconds()
            
            # Add error message to history
            error_response = ChatMessage(
                content=f"Error: {str(e)}",
                role="ai",
                is_visible=True
            )
            error_response.has_error = True
            error_response.response_time = response_time
            self.chat_history.append(error_response)
            
            return False, error_message, error_response
    
    def _send_message_chat_session(
        self, 
        user_input: str, 
        include_files: bool, 
        use_search: bool,
        streaming_callback: Optional[Callable[[str], None]]
    ) -> str:
        """
        Send a message using the chat session API.
        
        Args:
            user_input (str): User message text.
            include_files (bool): Whether to include uploaded files.
            use_search (bool): Whether to use Google Search grounding.
            streaming_callback (Optional[Callable[[str], None]]): Callback for streaming.
        
        Returns:
            str: Model response text.
        """
        try:
            # Create parts for the message
            parts = []
            
            # Include uploaded files if requested
            if include_files and self.uploaded_files:
                for uploaded_file in self.uploaded_files:
                    parts.append(uploaded_file.part)
            
            # Add the text content
            parts.append(types.Part.from_text(text=user_input))
            
            # Configure generation parameters
            generation_params = {}
            
            # Add thinking mode if enabled
            if self.thinking_mode and self.model_registry.model_supports_feature(
                self.selected_model, "thinkingMode"
            ):
                generation_params["generation_mode"] = "thinking"
                
            # Add search tool if enabled
            if use_search:
                search_tool = types.Tool(google_search=types.GoogleSearch())
                generation_params["tools"] = [search_tool]
            
            # Set up temperature and other parameters
            generation_params["temperature"] = self.temperature
            generation_params["top_p"] = self.top_p
            generation_params["max_output_tokens"] = self.max_output_tokens
            
            # Choose streaming or non-streaming based on settings
            if self.streaming and streaming_callback:
                # Streaming mode
                response_text = ""
                
                # Stream the response
                for chunk in self.chat.send_message_stream(
                    parts,
                    **generation_params
                ):
                    if chunk.text:
                        response_text += chunk.text
                        streaming_callback(chunk.text)
                
                return response_text
            else:
                # Non-streaming mode
                response = self.chat.send_message(
                    parts,
                    **generation_params
                )
                
                return response.text
                
        except Exception as e:
            self.logger.error(f"Error in chat session mode: {str(e)}")
            
            # Try to recover by falling back to generate_content mode
            self.logger.info("Falling back to generate_content mode")
            self.chat = None
            
            return self._send_message_generate_content(
                user_input, 
                include_files, 
                use_search,
                streaming_callback
            )
    
    def _send_message_generate_content(
        self, 
        user_input: str, 
        include_files: bool, 
        use_search: bool,
        streaming_callback: Optional[Callable[[str], None]]
    ) -> str:
        """
        Send a message using the generate_content API.
        
        Args:
            user_input (str): User message text.
            include_files (bool): Whether to include uploaded files.
            use_search (bool): Whether to use Google Search grounding.
            streaming_callback (Optional[Callable[[str], None]]): Callback for streaming.
        
        Returns:
            str: Model response text.
        """
        # Prepare contents list with visible chat history
        contents = []
        for entry in self.chat_history:
            if not entry.is_visible:
                continue
            
            if entry.role == "user":
                parts = []
                
                # Include uploaded files if this is the latest message and include_files is True
                if include_files and entry == self.chat_history[-1] and self.uploaded_files:
                    for uploaded_file in self.uploaded_files:
                        parts.append(uploaded_file.part)
                
                # Add the text content
                parts.append(types.Part.from_text(text=entry.content))
                
                contents.append(types.Content(role="user", parts=parts))
            else:  # AI responses
                contents.append(types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=entry.content)]
                ))
        
        # Set up generation config
        generation_config = self._create_generation_config()
        
        # Add thinking mode if enabled
        if self.thinking_mode and self.model_registry.model_supports_feature(
            self.selected_model, "thinkingMode"
        ):
            generation_config.generation_mode = "thinking"
        
        # Add Google Search tool if enabled
        if use_search:
            search_tool = types.Tool(google_search=types.GoogleSearch())
            generation_config.tools = [search_tool]
        
        # Choose streaming or non-streaming based on settings
        if self.streaming and streaming_callback:
            # Streaming mode
            response_text = ""
            
            # Stream the response
            for chunk in self.client.models.generate_content_stream(
                model=self.selected_model,
                contents=contents,
                config=generation_config
            ):
                if chunk.text:
                    response_text += chunk.text
                    streaming_callback(chunk.text)
            
            return response_text
        else:
            # Non-streaming mode
            response = self.client.models.generate_content(
                model=self.selected_model,
                contents=contents,
                config=generation_config
            )
            
            return response.text
    
    def _detect_search_usage(self, response_text: str) -> bool:
        """
        Detect if Google Search was used in the response.
        
        Args:
            response_text (str): Model response text.
        
        Returns:
            bool: True if Google Search was likely used, False otherwise.
        """
        # Look for Google Search indicators
        search_indicators = [
            "search results show",
            "according to search results",
            "based on search results",
            "search indicates",
            "searching for",
            "search shows",
            "I searched for",
            "from Google Search",
            "a Google search for"
        ]
        
        for indicator in search_indicators:
            if indicator.lower() in response_text.lower():
                return True
        
        # Look for URL patterns commonly found in search-grounded responses
        url_pattern = r'https?://[^\s)">]+'
        urls = re.findall(url_pattern, response_text)
        
        if urls:
            return True
        
        # Look for citation patterns like [1], [2], etc.
        citation_pattern = r'\[\d+\]'
        citations = re.findall(citation_pattern, response_text)
        
        if len(citations) >= 2:  # Multiple citations often indicate search usage
            return True
        
        return False
    
    def upload_file(self, file_path: str) -> Tuple[bool, Optional[str], Optional[UploadedFile]]:
        """
        Process and upload a file to be used in the conversation.
        
        Args:
            file_path (str): Path to the file.
        
        Returns:
            Tuple[bool, Optional[str], Optional[UploadedFile]]: 
                (success, error_message, uploaded_file)
        """
        try:
            if not os.path.exists(file_path):
                return False, f"File '{file_path}' not found.", None
            
            # Get file info
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_path)[1].lower()
            file_size = os.path.getsize(file_path)
            
            # Check if file type is supported
            if file_ext not in self.config.get_supported_file_extensions():
                return False, f"Unsupported file type: {file_ext}", None
            
            # Check file size
            max_size_mb = self.config.get_max_file_size(file_ext)
            max_size_bytes = max_size_mb * 1024 * 1024
            
            if file_size > max_size_bytes:
                return False, f"File is too large ({file_size/1024/1024:.2f}MB). Maximum size is {max_size_mb}MB.", None
            
            # Process file based on type
            mime_type = self.config.get_mime_type(file_ext)
            
            # For image files
            if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                
                # Create file part
                file_part = types.Part.from_bytes(
                    data=file_data,
                    mime_type=mime_type
                )
                
                # Create uploaded file
                uploaded_file = UploadedFile(
                    file_path=file_path,
                    part=file_part,
                    display_name=file_name,
                    file_type="image",
                    size=file_size
                )
                
            # For text files
            elif file_ext in ['.txt', '.md', '.py', '.java', '.js', '.html', '.css', '.json', '.csv']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
                
                # Create file part
                file_part = types.Part.from_text(
                    text=f"FILE CONTENT ({file_name}):\n\n{text_content}"
                )
                
                # Create uploaded file
                uploaded_file = UploadedFile(
                    file_path=file_path,
                    part=file_part,
                    display_name=file_name,
                    file_type="document",
                    size=file_size
                )
                
            # For PDF files
            elif file_ext == '.pdf':
                with open(file_path, 'rb') as f:
                    pdf_data = f.read()
                
                # Create file part
                file_part = types.Part.from_bytes(
                    data=pdf_data,
                    mime_type=mime_type
                )
                
                # Create uploaded file
                uploaded_file = UploadedFile(
                    file_path=file_path,
                    part=file_part,
                    display_name=file_name,
                    file_type="document",
                    size=file_size
                )
                
            else:
                return False, f"Unsupported file type: {file_ext}", None
            
            # Add to uploaded files
            self.uploaded_files.append(uploaded_file)
            
            self.logger.info(f"File '{file_name}' uploaded successfully")
            return True, None, uploaded_file
            
        except Exception as e:
            error_message = f"Failed to upload file: {str(e)}"
            self.logger.error(error_message)
            return False, error_message, None
    
    def upload_gcs_file(self, gcs_uri: str) -> Tuple[bool, Optional[str], Optional[UploadedFile]]:
        """
        Upload a file from Google Cloud Storage.
        
        Args:
            gcs_uri (str): Google Cloud Storage URI (gs://bucket/path/to/file).
        
        Returns:
            Tuple[bool, Optional[str], Optional[UploadedFile]]: 
                (success, error_message, uploaded_file)
        """
        try:
            if not gcs_uri.startswith("gs://"):
                return False, f"Invalid GCS URI: {gcs_uri}. Must start with 'gs://'", None
            
            # Extract filename from GCS URI
            file_name = gcs_uri.split("/")[-1]
            file_ext = os.path.splitext(file_name)[1].lower()
            
            # Determine file type and MIME type
            mime_type = self.config.get_mime_type(file_ext)
            
            # Determine file type category
            file_type = None
            for category, config in self.config.get_value(['file_handling', 'supported_types'], {}).items():
                if file_ext in config.get('extensions', []):
                    file_type = category
                    break
            
            if not file_type:
                return False, f"Unsupported file type: {file_ext}", None
            
            # Create file part
            file_part = types.Part.from_uri(
                file_uri=gcs_uri,
                mime_type=mime_type
            )
            
            # Create uploaded file (size unknown for GCS files)
            uploaded_file = UploadedFile(
                file_path=gcs_uri,
                part=file_part,
                display_name=file_name,
                file_type=file_type,
                size=0  # Size unknown for GCS files
            )
            
            # Add to uploaded files
            self.uploaded_files.append(uploaded_file)
            
            self.logger.info(f"GCS file '{file_name}' uploaded successfully")
            return True, None, uploaded_file
            
        except Exception as e:
            error_message = f"Failed to upload GCS file: {str(e)}"
            self.logger.error(error_message)
            return False, error_message, None
    
    def upload_youtube_video(self, youtube_url: str) -> Tuple[bool, Optional[str], Optional[UploadedFile]]:
        """
        Upload a YouTube video for analysis.
        
        Args:
            youtube_url (str): YouTube video URL.
        
        Returns:
            Tuple[bool, Optional[str], Optional[UploadedFile]]: 
                (success, error_message, uploaded_file)
        """
        try:
            # Check if YouTube support is enabled
            if not self.config.get_value(['features', 'youtube_support'], True):
                return False, "YouTube video support is disabled", None
            
            # Check if it's a valid YouTube URL
            youtube_regex = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com|youtu\.be)\/(?:watch\?v=)?([^\s&]+)'
            match = re.match(youtube_regex, youtube_url)
            
            if not match:
                return False, f"Invalid YouTube URL: {youtube_url}", None
            
            # Extract video ID
            video_id = match.group(1)
            display_name = f"YouTube Video: {video_id}"
            
            # Create file part
            file_part = types.Part.from_uri(
                file_uri=youtube_url,
                mime_type="video/*"
            )
            
            # Create uploaded file
            uploaded_file = UploadedFile(
                file_path=youtube_url,
                part=file_part,
                display_name=display_name,
                file_type="video",
                size=0  # Size unknown for YouTube videos
            )
            
            # Add to uploaded files
            self.uploaded_files.append(uploaded_file)
            
            self.logger.info(f"YouTube video '{display_name}' uploaded successfully")
            return True, None, uploaded_file
            
        except Exception as e:
            error_message = f"Failed to upload YouTube video: {str(e)}"
            self.logger.error(error_message)
            return False, error_message, None
    
    def clear_uploaded_files(self):
        """Clear all uploaded files."""
        self.uploaded_files = []
        self.logger.info("Cleared all uploaded files")
    
    def remove_uploaded_file(self, file_path: str) -> bool:
        """
        Remove a specific uploaded file by path.
        
        Args:
            file_path (str): Path or URI of the file to remove.
        
        Returns:
            bool: True if removed, False if not found.
        """
        for i, file in enumerate(self.uploaded_files):
            if file.file_path == file_path:
                del self.uploaded_files[i]
                self.logger.info(f"Removed uploaded file: {file.display_name}")
                return True
        
        return False
    
    def export_chat_to_html(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Export the chat history to an HTML file.
        
        Args:
            file_path (str): Path where to save the file.
        
        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LostMind AI Chat Export</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            padding: 20px;
            max-width: 800px;
            margin: 0 auto;
            background-color: #f0f0f0;
        }}
        h1, h2, h3 {{
            color: #333;
        }}
        .message {{
            margin-bottom: 20px;
            padding: 15px;
            border-radius: 10px;
        }}
        .user {{
            background-color: #e6f3ff;
            border-left: 5px solid #3498db;
        }}
        .ai {{
            background-color: #e9ffe6;
            border-left: 5px solid #2ecc71;
        }}
        .system {{
            background-color: #f5f5f5;
            border-left: 5px solid #95a5a6;
            font-style: italic;
        }}
        .error {{
            background-color: #ffe6e6;
            border-left: 5px solid #e74c3c;
        }}
        .message strong {{
            display: block;
            margin-bottom: 5px;
            font-size: 1.1em;
        }}
        .message .meta {{
            font-size: 0.8em;
            color: #7f8c8d;
            margin-top: 10px;
        }}
        pre {{
            white-space: pre-wrap;
            word-wrap: break-word;
            background-color: #f8f8f8;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 10px;
        }}
        code {{
            background-color: #f8f8f8;
            padding: 2px 4px;
            border-radius: 4px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin-bottom: 10px;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        th {{
            background-color: #f2f2f2;
        }}
        ul {{
            margin-top: 0;
            margin-bottom: 10px;
        }}
        .search-indicator {{
            display: inline-block;
            background-color: #3498db;
            color: white;
            font-size: 0.7em;
            padding: 2px 6px;
            border-radius: 4px;
            margin-left: 8px;
        }}
    </style>
</head>
<body>
    <h1>LostMind AI Chat Export</h1>
    <div class="chat-meta">
        <p><strong>Date:</strong> {timestamp}</p>
        <p><strong>Model:</strong> {self.selected_model}</p>
        <p><strong>Temperature:</strong> {self.temperature}</p>
        <p><strong>Top_p:</strong> {self.top_p}</p>
    </div>
    <hr>
"""
            
            # Add chat messages
            for msg in self.chat_history:
                if not msg.is_visible:
                    continue
                
                # Determine message class
                if msg.role == "user":
                    css_class = "user"
                    role_display = "You"
                elif msg.role == "ai":
                    css_class = "error" if msg.has_error else "ai"
                    role_display = "AI"
                else:
                    css_class = "system"
                    role_display = "System"
                
                # Format search indicator
                search_indicator = '<span class="search-indicator">Search</span>' if msg.used_search else ''
                
                # Format message content
                content = self._markdown_to_html(msg.content)
                
                # Format timestamp
                timestamp = msg.timestamp.strftime("%H:%M:%S")
                
                # Add to HTML
                html_content += f"""
    <div class="message {css_class}">
        <strong>{role_display}: {search_indicator}</strong>
        {content}
        <div class="meta">
            <span>{timestamp}</span>
            {f'<span> • Response time: {msg.response_time:.2f}s</span>' if msg.response_time > 0 else ''}
        </div>
    </div>
"""
            
            # Close HTML
            html_content += """
</body>
</html>
"""
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.info(f"Chat exported to HTML: {file_path}")
            return True, None
            
        except Exception as e:
            error_message = f"Failed to export chat to HTML: {str(e)}"
            self.logger.error(error_message)
            return False, error_message
    
    def export_chat_to_text(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Export the chat history to a plain text file.
        
        Args:
            file_path (str): Path where to save the file.
        
        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("LostMind AI Chat Export\n")
                f.write("=" * 50 + "\n\n")
                
                f.write(f"Date: {timestamp}\n")
                f.write(f"Model: {self.selected_model}\n")
                f.write(f"Temperature: {self.temperature}\n")
                f.write(f"Top_p: {self.top_p}\n\n")
                f.write("=" * 50 + "\n\n")
                
                for msg in self.chat_history:
                    if not msg.is_visible:
                        continue
                    
                    # Determine role display
                    if msg.role == "user":
                        role_display = "You"
                    elif msg.role == "ai":
                        role_display = "AI"
                    else:
                        role_display = "System"
                    
                    # Format timestamp
                    timestamp = msg.timestamp.strftime("%H:%M:%S")
                    
                    # Write message
                    f.write(f"{role_display} ({timestamp}):")
                    if msg.used_search:
                        f.write(" [Search used]")
                    f.write("\n")
                    f.write(msg.content)
                    f.write("\n\n")
                    
                    # Add separator between messages
                    f.write("-" * 50 + "\n\n")
            
            self.logger.info(f"Chat exported to text: {file_path}")
            return True, None
            
        except Exception as e:
            error_message = f"Failed to export chat to text: {str(e)}"
            self.logger.error(error_message)
            return False, error_message
    
    def _markdown_to_html(self, text: str) -> str:
        """
        Convert markdown to HTML.
        
        Args:
            text (str): Markdown text.
        
        Returns:
            str: HTML text.
        """
        # Convert code blocks
        text = re.sub(r'```(\w*)\n(.*?)\n```', r'<pre><code class="\1">\2</code></pre>', text, flags=re.DOTALL)
        
        # Convert inline code
        text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
        
        # Convert headers
        text = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
        text = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
        text = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
        
        # Convert bold
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
        
        # Convert italic
        text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
        
        # Convert lists
        text = re.sub(r'^- (.*?)$', r'<li>\1</li>', text, flags=re.MULTILINE)
        
        # Wrap lists in ul
        def replace_list(match):
            return f'<ul>{match.group(0)}</ul>'
        
        text = re.sub(r'(<li>.*?</li>\n)+', replace_list, text, flags=re.DOTALL)
        
        # Convert URLs
        text = re.sub(r'(?<!\()\b(https?://[^\s\)]+)\b', r'<a href="\1" target="_blank">\1</a>', text)
        
        # Convert newlines to br tags (except where we already have HTML)
        text = re.sub(r'\n(?!<)', r'<br>', text)
        
        return text
    
    def handle_api_error(self, error: Exception) -> Tuple[str, str]:
        """
        Handle API errors and provide informative messages.
        
        Args:
            error (Exception): The error that occurred.
        
        Returns:
            Tuple[str, str]: (error_code, error_message)
        """
        error_str = str(error)
        error_code = "UNKNOWN"
        error_message = error_str
        
        try:
            # Check for common error patterns
            if "404" in error_str or "not found" in error_str.lower():
                error_code = "NOT_FOUND"
                error_message = "The selected model could not be found. It may not be available in your project or region."
            
            elif "429" in error_str or "quota" in error_str.lower() or "rate limit" in error_str.lower():
                error_code = "RATE_LIMIT"
                error_message = "Rate limit or quota exceeded. Please wait and try again later."
            
            elif "403" in error_str or "permission" in error_str.lower() or "access" in error_str.lower():
                error_code = "PERMISSION_DENIED"
                error_message = "Permission denied. Please check your authentication and project permissions."
            
            elif "401" in error_str or "unauthorized" in error_str.lower() or "authentication" in error_str.lower():
                error_code = "UNAUTHORIZED"
                error_message = "Authentication failed. Please check your credentials."
            
            elif "timeout" in error_str.lower() or "deadline exceeded" in error_str.lower():
                error_code = "TIMEOUT"
                error_message = "The request timed out. The model may be overloaded or the request may be too complex."
            
            elif "invalid" in error_str.lower() and "argument" in error_str.lower():
                error_code = "INVALID_ARGUMENT"
                error_message = "Invalid request parameters. Please check your settings."
            
            elif "content" in error_str.lower() and "safety" in error_str.lower():
                error_code = "SAFETY_ERROR"
                error_message = "The request was blocked due to safety concerns."
            
            # Record the full error for debugging
            self.logger.error(f"API Error ({error_code}): {error_str}")
            
            # Add traceback for detailed debugging
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            
        except Exception as e:
            self.logger.error(f"Error while handling API error: {str(e)}")
        
        return error_code, error_message
