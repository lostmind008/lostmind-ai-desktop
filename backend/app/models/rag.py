# backend/app/models/rag.py

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class DocumentType(str, Enum):
    """Supported document types"""
    TEXT = "text"
    PDF = "pdf"
    MARKDOWN = "markdown"
    HTML = "html"
    CSV = "csv"
    JSON = "json"
    XML = "xml"
    EMAIL = "email"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


class DocumentMetadata(BaseModel):
    """Metadata for a document"""
    title: str
    source: str
    document_type: DocumentType
    author: Optional[str] = None
    created_date: Optional[datetime] = None
    file_size: Optional[int] = None
    language: str = "en"
    tags: List[str] = Field(default_factory=list)
    custom_fields: Dict[str, Any] = Field(default_factory=dict)


class DocumentChunk(BaseModel):
    """A chunk of a document with embedding"""
    id: str
    document_id: str
    chunk_index: int
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: List[float] = Field(default_factory=list)
    similarity_score: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class KnowledgeBase(BaseModel):
    """Knowledge base containing multiple documents"""
    id: str
    name: str
    description: str = ""
    document_count: int = 0
    total_chunks: int = 0
    created_at: datetime
    updated_at: datetime
    settings: Dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    """A single search result from RAG query"""
    chunk_id: str
    content: str
    metadata: Dict[str, Any]
    similarity_score: float
    document_id: Optional[str] = None


class RAGQuery(BaseModel):
    """RAG query parameters"""
    query: str
    k: int = Field(default=5, ge=1, le=20)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    include_metadata: bool = True
    filter_criteria: Optional[Dict[str, Any]] = None


class RAGResponse(BaseModel):
    """RAG query response"""
    response: str
    sources: List[SearchResult]
    query: str
    context_used: bool
    total_sources_found: int = 0
    processing_time_ms: Optional[float] = None


class DocumentUploadRequest(BaseModel):
    """Request to upload a document to knowledge base"""
    knowledge_base_id: str
    title: str
    content: str
    metadata: DocumentMetadata
    process_immediately: bool = True


class DocumentUploadResponse(BaseModel):
    """Response after uploading a document"""
    document_id: str
    chunks_created: int
    processing_status: str
    message: str


class KnowledgeBaseCreateRequest(BaseModel):
    """Request to create a new knowledge base"""
    name: str
    description: str = ""
    settings: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeBaseUpdateRequest(BaseModel):
    """Request to update knowledge base"""
    name: Optional[str] = None
    description: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class KnowledgeBaseStats(BaseModel):
    """Statistics for a knowledge base"""
    id: str
    name: str
    document_count: int
    total_chunks: int
    avg_chunk_length: float
    created_at: datetime
    updated_at: datetime
    storage_size_bytes: Optional[int] = None


class AdvancedRAGQuery(BaseModel):
    """Advanced RAG query with multiple knowledge bases and filters"""
    query: str
    knowledge_base_ids: List[str] = Field(default_factory=list)
    k: int = Field(default=10, ge=1, le=50)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    enable_reranking: bool = False
    include_metadata: bool = True
    filter_criteria: Optional[Dict[str, Any]] = None
    search_type: str = Field(default="semantic", pattern="^(semantic|keyword|hybrid)$")


class MultiKBRAGResponse(BaseModel):
    """Response from querying multiple knowledge bases"""
    response: str
    sources: List[SearchResult]
    query: str
    knowledge_bases_searched: List[str]
    total_sources_found: int
    reranked: bool = False
    processing_time_ms: Optional[float] = None


class DocumentProcessingStatus(BaseModel):
    """Status of document processing"""
    document_id: str
    status: str  # "pending", "processing", "completed", "failed"
    progress_percentage: float = 0.0
    chunks_processed: int = 0
    total_chunks: int = 0
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None


class BulkDocumentUpload(BaseModel):
    """Request for bulk document upload"""
    knowledge_base_id: str
    documents: List[DocumentUploadRequest]
    process_in_background: bool = True


class BulkUploadResponse(BaseModel):
    """Response for bulk document upload"""
    job_id: str
    total_documents: int
    estimated_processing_time_minutes: float
    status: str
    message: str


class ChatWithRAGRequest(BaseModel):
    """Request to chat with RAG context"""
    message: str
    session_id: str
    knowledge_base_ids: List[str] = Field(default_factory=list)
    rag_config: AdvancedRAGQuery
    use_conversation_history: bool = True
    max_context_length: int = Field(default=4000, ge=1000, le=8000)


class RAGChatResponse(BaseModel):
    """Response from RAG-enhanced chat"""
    response: str
    sources_used: List[SearchResult]
    context_length: int
    tokens_used: Optional[int] = None
    rag_confidence: float
    session_id: str