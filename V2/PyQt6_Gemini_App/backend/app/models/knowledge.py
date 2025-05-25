"""
Data models for knowledge management and RAG functionality.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

class Document(BaseModel):
    """Document model for knowledge base storage."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    content: str
    document_type: str = Field(default="text")  # text, pdf, markdown, code, etc.
    source: Optional[str] = None  # URL, file path, etc.
    author: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class DocumentCreate(BaseModel):
    """Model for creating new documents."""
    
    title: str
    content: str
    document_type: str = "text"
    source: Optional[str] = None
    author: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class DocumentUpdate(BaseModel):
    """Model for updating documents."""
    
    title: Optional[str] = None
    content: Optional[str] = None
    document_type: Optional[str] = None
    source: Optional[str] = None
    author: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

class KnowledgeChunk(BaseModel):
    """Individual chunk of a document with embedding information."""
    
    id: str
    content: str
    document_id: str
    document_title: str
    chunk_index: int
    similarity_score: float = Field(ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
class SearchQuery(BaseModel):
    """Model for knowledge base search queries."""
    
    query: str
    limit: int = Field(default=5, ge=1, le=50)
    score_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    document_types: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    author: Optional[str] = None
    
class SearchResult(BaseModel):
    """Model for search results."""
    
    query: str
    chunks: List[KnowledgeChunk]
    total_results: int
    search_time_ms: float
    
class KnowledgeStats(BaseModel):
    """Statistics about the knowledge base."""
    
    total_documents: int
    total_chunks: int
    document_types: Dict[str, int]
    authors: Dict[str, int]
    tags: Dict[str, int]
    last_updated: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class RAGContext(BaseModel):
    """Context retrieved for RAG prompting."""
    
    query: str
    relevant_chunks: List[KnowledgeChunk]
    context_text: str  # Concatenated and formatted context
    source_documents: List[str]  # List of document titles
    confidence_score: float  # Average similarity score
    
class RAGRequest(BaseModel):
    """Request for RAG-enhanced chat."""
    
    message: str
    use_rag: bool = True
    rag_limit: int = Field(default=3, ge=1, le=10)
    rag_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    knowledge_filters: Optional[Dict[str, Any]] = None

class RAGResponse(BaseModel):
    """Response from RAG-enhanced chat."""
    
    response: str
    rag_context: Optional[RAGContext] = None
    model_used: str
    thinking_content: Optional[str] = None
    sources_used: List[str] = Field(default_factory=list)
    
class KnowledgeBase(BaseModel):
    """Complete knowledge base metadata."""
    
    name: str
    description: str
    documents: List[Document]
    stats: KnowledgeStats
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }