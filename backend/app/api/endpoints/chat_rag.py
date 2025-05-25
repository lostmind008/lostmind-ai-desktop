# backend/app/api/endpoints/chat_rag.py

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
import logging
import time

from app.services.rag_service import RAGService
from app.services.vector_store import VectorStoreService
from app.services.gcs_service import GCSService
from app.services.genai_service import GenAIService
from app.models.rag import (
    ChatWithRAGRequest, RAGChatResponse, AdvancedRAGQuery, 
    SearchResult, RAGQuery
)
from app.models.chat import ChatMessage, ChatSession
from app.core.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


# Dependency to get services
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


@router.post("/sessions/{session_id}/rag", response_model=RAGChatResponse)
async def chat_with_rag(
    session_id: str,
    request: ChatWithRAGRequest,
    rag_service: RAGService = Depends(get_rag_service),
    current_user: dict = Depends(get_current_user)
):
    """Send a message with RAG context from knowledge bases"""
    try:
        start_time = time.time()
        
        # Get conversation history if requested
        conversation_context = ""
        if request.use_conversation_history:
            # This would integrate with your existing chat service to get history
            # For now, we'll skip this and focus on RAG context
            pass
        
        # Query knowledge bases for relevant context
        relevant_sources = []
        rag_confidence = 0.0
        
        if request.knowledge_base_ids:
            # Create RAG query from the chat message
            rag_query = RAGQuery(
                query=request.message,
                k=request.rag_config.k,
                similarity_threshold=request.rag_config.similarity_threshold
            )
            
            # Query each knowledge base
            all_sources = []
            for kb_id in request.knowledge_base_ids:
                try:
                    kb_response = await rag_service.query_knowledge_base(kb_id, rag_query)
                    all_sources.extend(kb_response.sources)
                except Exception as e:
                    logger.warning(f"Error querying KB {kb_id}: {str(e)}")
                    continue
            
            # Sort by similarity and take top results
            all_sources.sort(key=lambda x: x.similarity_score, reverse=True)
            relevant_sources = all_sources[:request.rag_config.k]
            
            # Calculate average confidence
            if relevant_sources:
                rag_confidence = sum(source.similarity_score for source in relevant_sources) / len(relevant_sources)
        
        # Build context for the AI
        context_parts = []
        
        # Add conversation history if available
        if conversation_context:
            context_parts.append(f"Previous conversation:\n{conversation_context}")
        
        # Add RAG context
        if relevant_sources:
            rag_context_parts = []
            for source in relevant_sources:
                source_title = source.metadata.get('title', 'Unknown source')
                rag_context_parts.append(f"Source: {source_title}\nContent: {source.content}")
            
            rag_context = "\n\n---\n\n".join(rag_context_parts)
            context_parts.append(f"Relevant knowledge:\n{rag_context}")
        
        # Combine all context
        full_context = "\n\n" + "="*50 + "\n\n".join(context_parts) if context_parts else ""
        
        # Prepare the prompt with context
        if full_context:
            enhanced_prompt = f"""You are an AI assistant with access to relevant knowledge. Use the provided context to answer the user's question accurately and comprehensively.

{full_context}

{"="*50}

User question: {request.message}

Please provide a helpful response based on the context above. If the context doesn't contain sufficient information to fully answer the question, acknowledge this and provide what information you can."""
        else:
            enhanced_prompt = request.message
        
        # Truncate context if it exceeds max length
        if len(enhanced_prompt) > request.max_context_length:
            # Keep the user question and truncate context
            question_part = f"\n\nUser question: {request.message}\n\nPlease provide a helpful response."
            available_length = request.max_context_length - len(question_part) - 200  # Buffer
            
            if full_context and available_length > 0:
                truncated_context = full_context[:available_length] + "...\n[Context truncated]"
                enhanced_prompt = f"You are an AI assistant. Use this context to help answer the user's question:\n\n{truncated_context}{question_part}"
            else:
                enhanced_prompt = f"User question: {request.message}\n\nPlease provide a helpful response."
        
        # Generate response using Gemini
        response_text = await rag_service._generate_rag_response(request.message, full_context)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Prepare response
        rag_response = RAGChatResponse(
            response=response_text,
            sources_used=relevant_sources,
            context_length=len(enhanced_prompt),
            rag_confidence=rag_confidence,
            session_id=session_id
        )
        
        logger.info(f"RAG chat completed for session {session_id} with {len(relevant_sources)} sources")
        
        return rag_response
        
    except Exception as e:
        logger.error(f"Error in RAG chat for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/context-search", response_model=List[SearchResult])
async def search_context_for_session(
    session_id: str,
    query: str,
    knowledge_base_ids: List[str],
    k: int = 5,
    similarity_threshold: float = 0.7,
    rag_service: RAGService = Depends(get_rag_service),
    current_user: dict = Depends(get_current_user)
):
    """Search for relevant context without generating a response"""
    try:
        # Create RAG query
        rag_query = RAGQuery(
            query=query,
            k=k,
            similarity_threshold=similarity_threshold
        )
        
        # Search all specified knowledge bases
        all_sources = []
        for kb_id in knowledge_base_ids:
            try:
                kb_response = await rag_service.query_knowledge_base(kb_id, rag_query)
                all_sources.extend(kb_response.sources)
            except Exception as e:
                logger.warning(f"Error searching KB {kb_id}: {str(e)}")
                continue
        
        # Sort by similarity and return top results
        all_sources.sort(key=lambda x: x.similarity_score, reverse=True)
        return all_sources[:k]
        
    except Exception as e:
        logger.error(f"Error searching context for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/suggested-sources")
async def get_suggested_sources(
    session_id: str,
    last_n_messages: int = 3,
    rag_service: RAGService = Depends(get_rag_service),
    current_user: dict = Depends(get_current_user)
):
    """Get suggested knowledge base sources based on recent conversation"""
    try:
        # This would analyze recent messages to suggest relevant knowledge bases
        # For now, return available knowledge bases
        knowledge_bases = await rag_service.list_knowledge_bases()
        
        suggestions = []
        for kb in knowledge_bases:
            suggestions.append({
                "knowledge_base_id": kb.id,
                "name": kb.name,
                "description": kb.description,
                "document_count": kb.document_count,
                "relevance_score": 0.8  # Placeholder
            })
        
        return {"suggestions": suggestions}
        
    except Exception as e:
        logger.error(f"Error getting suggested sources for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/enable-rag")
async def enable_rag_for_session(
    session_id: str,
    knowledge_base_ids: List[str],
    rag_config: Optional[AdvancedRAGQuery] = None,
    current_user: dict = Depends(get_current_user)
):
    """Enable RAG for a chat session with specific knowledge bases"""
    try:
        # This would store the RAG configuration for the session
        # For now, just validate the knowledge bases exist
        rag_service = await get_rag_service()
        
        valid_kbs = []
        for kb_id in knowledge_base_ids:
            kb = await rag_service.get_knowledge_base(kb_id)
            if kb:
                valid_kbs.append(kb_id)
        
        if not valid_kbs:
            raise HTTPException(status_code=400, detail="No valid knowledge bases found")
        
        # Store session RAG configuration (this would go to database in real implementation)
        session_config = {
            "session_id": session_id,
            "knowledge_base_ids": valid_kbs,
            "rag_config": rag_config.dict() if rag_config else {},
            "enabled": True
        }
        
        logger.info(f"RAG enabled for session {session_id} with {len(valid_kbs)} knowledge bases")
        
        return {
            "message": "RAG enabled for session",
            "knowledge_bases_count": len(valid_kbs),
            "configuration": session_config
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enabling RAG for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))