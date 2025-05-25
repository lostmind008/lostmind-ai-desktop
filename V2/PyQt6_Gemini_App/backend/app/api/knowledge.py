"""
Knowledge management API endpoints for document storage and RAG functionality.
"""

import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.core.dependencies import get_vector_service, get_cache_service
from app.models.knowledge import (
    Document, DocumentCreate, DocumentUpdate, KnowledgeChunk,
    SearchQuery, SearchResult, RAGRequest, RAGResponse, RAGContext,
    KnowledgeStats
)
from app.services.vector_service import VectorService
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

@router.post("/documents", response_model=Document)
async def create_document(
    document_data: DocumentCreate,
    vector_service: VectorService = Depends(get_vector_service)
) -> Document:
    """Create a new document and add it to the knowledge base."""
    try:
        # Create document instance
        document = Document(**document_data.dict())
        
        # Add to vector database
        success = await vector_service.add_document(document)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to add document to knowledge base"
            )
        
        logger.info(f"Created document: {document.title}")
        return document
        
    except Exception as e:
        logger.error(f"Error creating document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/{document_id}", response_model=Document)
async def get_document(
    document_id: str,
    vector_service: VectorService = Depends(get_vector_service)
) -> Document:
    """Get a specific document by ID."""
    try:
        chunks = await vector_service.get_document_chunks(document_id)
        
        if not chunks:
            raise HTTPException(
                status_code=404,
                detail=f"Document {document_id} not found"
            )
        
        # Reconstruct document from chunks
        first_chunk = chunks[0]
        content = "\n".join([chunk.content for chunk in chunks])
        
        metadata = first_chunk.metadata
        document = Document(
            id=document_id,
            title=first_chunk.document_title,
            content=content,
            document_type=metadata.get("document_type", "text"),
            source=metadata.get("source"),
            author=metadata.get("author"),
            tags=metadata.get("tags", "").split(",") if metadata.get("tags") else None,
            metadata=metadata,
            created_at=metadata.get("created_at"),
            updated_at=metadata.get("created_at")  # Using created_at as fallback
        )
        
        return document
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/documents/{document_id}", response_model=Document)
async def update_document(
    document_id: str,
    document_update: DocumentUpdate,
    vector_service: VectorService = Depends(get_vector_service)
) -> Document:
    """Update an existing document."""
    try:
        # Get existing document
        existing_chunks = await vector_service.get_document_chunks(document_id)
        
        if not existing_chunks:
            raise HTTPException(
                status_code=404,
                detail=f"Document {document_id} not found"
            )
        
        # Reconstruct existing document
        first_chunk = existing_chunks[0]
        existing_content = "\n".join([chunk.content for chunk in existing_chunks])
        existing_metadata = first_chunk.metadata
        
        # Apply updates
        updated_data = {
            "id": document_id,
            "title": document_update.title or first_chunk.document_title,
            "content": document_update.content or existing_content,
            "document_type": document_update.document_type or existing_metadata.get("document_type", "text"),
            "source": document_update.source or existing_metadata.get("source"),
            "author": document_update.author or existing_metadata.get("author"),
            "tags": document_update.tags or (existing_metadata.get("tags", "").split(",") if existing_metadata.get("tags") else None),
            "metadata": {**existing_metadata, **(document_update.metadata or {})},
            "created_at": existing_metadata.get("created_at"),
            "updated_at": time.time()
        }
        
        updated_document = Document(**updated_data)
        
        # Update in vector database
        success = await vector_service.update_document(updated_document)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to update document in knowledge base"
            )
        
        logger.info(f"Updated document: {updated_document.title}")
        return updated_document
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    vector_service: VectorService = Depends(get_vector_service)
) -> JSONResponse:
    """Delete a document from the knowledge base."""
    try:
        success = await vector_service.delete_document(document_id)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete document from knowledge base"
            )
        
        logger.info(f"Deleted document: {document_id}")
        return JSONResponse(
            content={"message": f"Document {document_id} deleted successfully"}
        )
        
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search", response_model=SearchResult)
async def search_knowledge(
    search_query: SearchQuery,
    vector_service: VectorService = Depends(get_vector_service)
) -> SearchResult:
    """Search the knowledge base for relevant content."""
    try:
        start_time = time.time()
        
        # Build filters
        filters = {}
        if search_query.document_types:
            filters["document_type"] = {"$in": search_query.document_types}
        if search_query.author:
            filters["author"] = search_query.author
        if search_query.tags:
            # Note: This is a simplified tag filter
            filters["tags"] = {"$contains": search_query.tags[0]}
        
        # Search for similar chunks
        chunks = await vector_service.search_similar(
            query=search_query.query,
            limit=search_query.limit,
            score_threshold=search_query.score_threshold,
            filters=filters if filters else None
        )
        
        search_time_ms = (time.time() - start_time) * 1000
        
        result = SearchResult(
            query=search_query.query,
            chunks=chunks,
            total_results=len(chunks),
            search_time_ms=search_time_ms
        )
        
        logger.info(f"Knowledge search completed: {len(chunks)} results in {search_time_ms:.2f}ms")
        return result
        
    except Exception as e:
        logger.error(f"Error searching knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload", response_model=Document)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    document_type: str = Form("text"),
    author: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # Comma-separated tags
    vector_service: VectorService = Depends(get_vector_service)
) -> Document:
    """Upload a file and add it to the knowledge base."""
    try:
        # Read file content
        content = await file.read()
        
        # Handle different file types
        if file.content_type and "text" in file.content_type:
            text_content = content.decode("utf-8")
        else:
            # For non-text files, we might need additional processing
            # For now, just convert to string representation
            text_content = str(content)
        
        # Prepare document data
        document_data = DocumentCreate(
            title=title or file.filename or "Uploaded Document",
            content=text_content,
            document_type=document_type,
            source=f"upload:{file.filename}",
            author=author,
            tags=tags.split(",") if tags else None,
            metadata={
                "original_filename": file.filename,
                "content_type": file.content_type,
                "file_size": len(content)
            }
        )
        
        # Create and store document
        document = Document(**document_data.dict())
        success = await vector_service.add_document(document)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to process uploaded document"
            )
        
        logger.info(f"Uploaded document: {document.title}")
        return document
        
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", response_model=Dict[str, Any])
async def get_knowledge_stats(
    vector_service: VectorService = Depends(get_vector_service)
) -> Dict[str, Any]:
    """Get statistics about the knowledge base."""
    try:
        stats = await vector_service.get_collection_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Error getting knowledge stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset")
async def reset_knowledge_base(
    vector_service: VectorService = Depends(get_vector_service)
) -> JSONResponse:
    """Reset the entire knowledge base (use with caution)."""
    try:
        success = await vector_service.reset_collection()
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to reset knowledge base"
            )
        
        logger.warning("Knowledge base reset completed")
        return JSONResponse(
            content={"message": "Knowledge base reset successfully"}
        )
        
    except Exception as e:
        logger.error(f"Error resetting knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Cache management endpoints
@router.get("/cache/stats")
async def get_cache_stats(
    cache_service: CacheService = Depends(get_cache_service)
) -> Dict[str, Any]:
    """Get cache statistics and health information."""
    try:
        stats = await cache_service.get_cache_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cache/clear")
async def clear_cache(
    cache_service: CacheService = Depends(get_cache_service)
) -> JSONResponse:
    """Clear expired cache entries."""
    try:
        deleted_count = await cache_service.clear_expired_sessions()
        
        return JSONResponse(
            content={
                "message": f"Cache cleanup completed",
                "deleted_entries": deleted_count
            }
        )
        
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))