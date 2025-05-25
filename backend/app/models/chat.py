"""
Chat data models for LostMindAI Backend API.

Pydantic models for chat sessions, messages, and API requests/responses.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from enum import Enum


class MessageRole(str, Enum):
    """Message role enumeration."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class FileType(str, Enum):
    """Supported file types."""
    IMAGE = "image"
    DOCUMENT = "document"
    VIDEO = "video"
    AUDIO = "audio"


class ChatMessage(BaseModel):
    """Chat message model."""
    id: Optional[str] = None
    content: str
    role: MessageRole
    timestamp: datetime = Field(default_factory=datetime.now)
    is_visible: bool = True
    used_search: bool = False
    has_error: bool = False
    response_time: float = 0.0
    thinking_content: Optional[str] = None
    files: List[Dict[str, Any]] = Field(default_factory=list)


class UploadedFile(BaseModel):
    """Uploaded file model."""
    id: str
    file_path: str
    display_name: str
    file_type: FileType
    size: int
    mime_type: str
    timestamp: datetime = Field(default_factory=datetime.now)
    processed: bool = False


class ChatSession(BaseModel):
    """Chat session model."""
    id: str
    title: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    messages: List[ChatMessage] = Field(default_factory=list)
    files: List[UploadedFile] = Field(default_factory=list)
    model_id: str
    system_instruction: Optional[str] = None
    settings: Dict[str, Any] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    """Chat message request model."""
    message: str
    session_id: Optional[str] = None
    files: List[str] = Field(default_factory=list)  # File IDs
    stream: bool = True
    use_search: bool = True
    thinking_mode: bool = False


class ChatResponse(BaseModel):
    """Chat response model."""
    message: ChatMessage
    session_id: str
    model_used: str
    tokens_used: Optional[int] = None
    cost_estimate: Optional[float] = None
    context_used: List[str] = Field(default_factory=list)  # Context sources


class ModelInfo(BaseModel):
    """Model information model."""
    id: str
    display_name: str
    description: str
    type: str = "base"
    supported_methods: List[str] = Field(default_factory=list)
    context_window: Optional[int] = None
    max_output_tokens: Optional[int] = None
    supports_system_instruction: bool = True
    supports_search: bool = False
    supports_thinking: bool = False


class ModelCapabilities(BaseModel):
    """Model capabilities response."""
    models: List[ModelInfo]
    default_model: str


class ThinkingBudget(BaseModel):
    """Thinking budget configuration."""
    auto_detect: bool = True
    light: int = 1024
    moderate: int = 4096
    deep: int = 8192
    maximum: int = 24576


class GenerationConfig(BaseModel):
    """Generation configuration for Gemini models."""
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    top_p: float = Field(default=0.95, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(default=None, ge=1)
    max_output_tokens: int = Field(default=8192, ge=1)
    candidate_count: int = Field(default=1, ge=1, le=1)
    stop_sequences: List[str] = Field(default_factory=list)


class SessionCreateRequest(BaseModel):
    """Request to create a new chat session."""
    title: Optional[str] = None
    model_id: str
    system_instruction: Optional[str] = None
    generation_config: Optional[GenerationConfig] = None


class SessionUpdateRequest(BaseModel):
    """Request to update a chat session."""
    title: Optional[str] = None
    system_instruction: Optional[str] = None
    generation_config: Optional[GenerationConfig] = None


class SessionListResponse(BaseModel):
    """Response for listing chat sessions."""
    sessions: List[ChatSession]
    total: int
    page: int = 1
    page_size: int = 20


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: Optional[str] = None
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ModelSelection(BaseModel):
    """Available model selection information."""
    name: str
    display_name: str
    description: str
    max_input_tokens: int
    max_output_tokens: int
    supports_images: bool = False
    supports_audio: bool = False
    supports_video: bool = False
    supports_search: bool = False
    supports_thinking: bool = False
    version: str = "1.0"


class UsageStats(BaseModel):
    """Usage statistics for a chat session."""
    session_id: str
    total_messages: int
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    model_used: str
    session_duration_minutes: float = 0.0
    created_at: datetime
    last_activity: datetime