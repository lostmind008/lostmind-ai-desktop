# backend/app/api/endpoints/rag.py

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import List, Optional
import logging
import time
from datetime import datetime

from app.services.rag_service import RAGService
from app.services.vector_store import VectorStoreService
from app.services.gcs_service import GCSService
from app.services.genai_service import GenAIService
from app.models.rag import (
    KnowledgeBase, KnowledgeBaseCreateRequest, KnowledgeBaseUpdateRequest,
    RAGQuery, RAGResponse, DocumentUploadRequest, DocumentUploadResponse,
    KnowledgeBaseStats, AdvancedRAGQuery, MultiKBRAGResponse,
    DocumentMetadata, DocumentType
)
from app.core.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


# Dependency to get RAG service
async def get_rag_service() -> RAGService:
    """Get RAG service instance"""
    genai_service = GenAIService()
    vector_store = VectorStoreService()
    gcs_service = GCSService()
    
    return RAGService(
        genai_client=genai_service.client,
        vector_store=vector_store,
        gcs_service=gcs_service
    )


@router.post("/knowledge-bases", response_model=KnowledgeBase)
async def create_knowledge_base(
    request: KnowledgeBaseCreateRequest,
    rag_service: RAGService = Depends(get_rag_service),
    current_user: dict = Depends(get_current_user)
):
    """Create a new knowledge base"""
    try:
        kb = await rag_service.create_knowledge_base(
            name=request.name,
            description=request.description
        )
        logger.info(f"User {current_user.get('id')} created knowledge base {kb.id}")
        return kb
    except Exception as e:
        logger.error(f"Error creating knowledge base: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge-bases", response_model=List[KnowledgeBase])
async def list_knowledge_bases(
    rag_service: RAGService = Depends(get_rag_service),
    current_user: dict = Depends(get_current_user)
):
    """List all knowledge bases"""
    try:
        knowledge_bases = await rag_service.list_knowledge_bases()
        return knowledge_bases
    except Exception as e:
        logger.error(f"Error listing knowledge bases: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge-bases/{kb_id}", response_model=KnowledgeBase)
async def get_knowledge_base(
    kb_id: str,
    rag_service: RAGService = Depends(get_rag_service),
    current_user: dict = Depends(get_current_user)
):
    """Get a specific knowledge base"""
    try:
        kb = await rag_service.get_knowledge_base(kb_id)
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")
        return kb
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting knowledge base {kb_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/knowledge-bases/{kb_id}")
async def delete_knowledge_base(
    kb_id: str,
    rag_service: RAGService = Depends(get_rag_service),
    current_user: dict = Depends(get_current_user)
):
    """Delete a knowledge base"""
    try:
        success = await rag_service.delete_knowledge_base(kb_id)
        if not success:
            raise HTTPException(status_code=404, detail="Knowledge base not found")
        
        logger.info(f"User {current_user.get('id')} deleted knowledge base {kb_id}")
        return {"message": "Knowledge base deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting knowledge base {kb_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge-bases/{kb_id}/documents", response_model=DocumentUploadResponse)
async def add_document_to_kb(
    kb_id: str,
    request: DocumentUploadRequest,
    rag_service: RAGService = Depends(get_rag_service),
    current_user: dict = Depends(get_current_user)
):
    """Add a document to a knowledge base"""
    try:
        doc_id = await rag_service.add_document_to_kb(
            kb_id=kb_id,
            content=request.content,
            metadata=request.metadata
        )
        
        # Get chunk count (estimate based on content length)
        estimated_chunks = len(request.content) // 1000 + 1
        
        logger.info(f"User {current_user.get('id')} added document {doc_id} to KB {kb_id}")
        
        return DocumentUploadResponse(
            document_id=doc_id,
            chunks_created=estimated_chunks,
            processing_status="completed",
            message="Document processed and added to knowledge base"
        )
    except Exception as e:
        logger.error(f"Error adding document to KB {kb_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge-bases/{kb_id}/upload-file", response_model=DocumentUploadResponse)
async def upload_file_to_kb(
    kb_id: str,
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(""),
    tags: str = Form(""),
    rag_service: RAGService = Depends(get_rag_service),
    current_user: dict = Depends(get_current_user)
):
    """Upload a file to a knowledge base"""
    try:
        # Read file content
        content = await file.read()
        
        # Determine document type from file extension
        file_ext = file.filename.split('.')[-1].lower() if file.filename else 'txt'
        doc_type_map = {
            'txt': DocumentType.TEXT,
            'pdf': DocumentType.PDF,
            'md': DocumentType.MARKDOWN,
            'html': DocumentType.HTML,
            'csv': DocumentType.CSV,
            'json': DocumentType.JSON,
            'xml': DocumentType.XML
        }
        doc_type = doc_type_map.get(file_ext, DocumentType.TEXT)
        
        # Create metadata
        metadata = DocumentMetadata(
            title=title,
            source=file.filename or "uploaded_file",
            document_type=doc_type,
            file_size=len(content),
            tags=tags.split(',') if tags else [],
            custom_fields={"uploaded_by": current_user.get("id", "unknown")}
        )
        
        # Process content based on file type
        if doc_type == DocumentType.TEXT:
            text_content = content.decode('utf-8')
        else:
            # For other file types, we'd need specific parsers
            # For now, treat as text
            text_content = content.decode('utf-8', errors='ignore')
        
        doc_id = await rag_service.add_document_to_kb(
            kb_id=kb_id,
            content=text_content,
            metadata=metadata
        )
        
        estimated_chunks = len(text_content) // 1000 + 1
        
        logger.info(f"User {current_user.get('id')} uploaded file {file.filename} to KB {kb_id}")
        
        return DocumentUploadResponse(
            document_id=doc_id,
            chunks_created=estimated_chunks,
            processing_status="completed",
            message=f"File {file.filename} processed and added to knowledge base"
        )
        
    except Exception as e:
        logger.error(f"Error uploading file to KB {kb_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge-bases/{kb_id}/query", response_model=RAGResponse)
async def query_knowledge_base(
    kb_id: str,
    query: RAGQuery,
    rag_service: RAGService = Depends(get_rag_service),
    current_user: dict = Depends(get_current_user)
):
    """Query a knowledge base using RAG"""
    try:
        start_time = time.time()
        
        response = await rag_service.query_knowledge_base(kb_id, query)
        
        processing_time = (time.time() - start_time) * 1000
        response.processing_time_ms = processing_time
        response.total_sources_found = len(response.sources)
        
        logger.info(f"User {current_user.get('id')} queried KB {kb_id}: '{query.query[:50]}...'")
        
        return response
    except Exception as e:
        logger.error(f"Error querying KB {kb_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query-multiple", response_model=MultiKBRAGResponse)
async def query_multiple_knowledge_bases(
    query: AdvancedRAGQuery,
    rag_service: RAGService = Depends(get_rag_service),
    current_user: dict = Depends(get_current_user)
):
    """Query multiple knowledge bases with advanced options"""
    try:
        start_time = time.time()
        
        if not query.knowledge_base_ids:
            # Query all available knowledge bases
            all_kbs = await rag_service.list_knowledge_bases()
            query.knowledge_base_ids = [kb.id for kb in all_kbs]
        
        # Query each knowledge base and aggregate results
        all_sources = []
        for kb_id in query.knowledge_base_ids:
            try:
                kb_query = RAGQuery(
                    query=query.query,
                    k=query.k // len(query.knowledge_base_ids) + 1,
                    similarity_threshold=query.similarity_threshold
                )
                
                kb_response = await rag_service.query_knowledge_base(kb_id, kb_query)
                all_sources.extend(kb_response.sources)
            except Exception as e:
                logger.warning(f"Error querying KB {kb_id}: {str(e)}")
                continue
        
        # Sort by similarity score and take top k
        all_sources.sort(key=lambda x: x.similarity_score, reverse=True)
        top_sources = all_sources[:query.k]
        
        # Generate aggregated response
        if top_sources:
            context_parts = [f"Source: {source.metadata.get('title', 'Unknown')}\n{source.content}" 
                           for source in top_sources]
            context = "\n\n---\n\n".join(context_parts)
            
            # Use RAG service to generate response
            response_text = await rag_service._generate_rag_response(query.query, context)
        else:
            response_text = "I couldn't find relevant information in the knowledge bases to answer your question."
        
        processing_time = (time.time() - start_time) * 1000
        
        logger.info(f"User {current_user.get('id')} queried multiple KBs: '{query.query[:50]}...'")
        
        return MultiKBRAGResponse(
            response=response_text,
            sources=top_sources,
            query=query.query,
            knowledge_bases_searched=query.knowledge_base_ids,
            total_sources_found=len(all_sources),
            reranked=query.enable_reranking,
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error querying multiple knowledge bases: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge-bases/{kb_id}/stats", response_model=KnowledgeBaseStats)
async def get_knowledge_base_stats(
    kb_id: str,
    rag_service: RAGService = Depends(get_rag_service),
    current_user: dict = Depends(get_current_user)
):
    """Get statistics for a knowledge base"""
    try:
        kb = await rag_service.get_knowledge_base(kb_id)
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")
        
        # Get vector store stats
        vector_stats = await rag_service.vector_store.get_collection_stats(kb_id)
        
        return KnowledgeBaseStats(
            id=kb.id,
            name=kb.name,
            document_count=vector_stats.get('unique_documents', 0),
            total_chunks=vector_stats.get('total_chunks', 0),
            avg_chunk_length=vector_stats.get('avg_content_length', 0),
            created_at=kb.created_at,
            updated_at=kb.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting KB stats {kb_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))