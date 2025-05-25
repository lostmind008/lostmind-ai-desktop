# backend/app/services/rag_service.py

import os
import logging
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio

from google import genai
from google.genai import types
import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import get_settings
from app.models.rag import (
    DocumentChunk, KnowledgeBase, RAGQuery, RAGResponse, 
    DocumentMetadata, SearchResult
)
from app.services.vector_store import VectorStoreService
from app.services.gcs_service import GCSService

logger = logging.getLogger(__name__)
settings = get_settings()


class DocumentProcessor:
    """Document processing and chunking service"""
    
    def __init__(self):
        self.chunk_size = 1000
        self.chunk_overlap = 200
        
    async def process_document(self, content: str, doc_id: str, 
                             metadata: DocumentMetadata) -> List[DocumentChunk]:
        """Process a document into chunks for RAG"""
        try:
            # Simple text chunking - can be enhanced with semantic chunking
            chunks = self._chunk_text(content, self.chunk_size, self.chunk_overlap)
            
            document_chunks = []
            for i, chunk_text in enumerate(chunks):
                chunk = DocumentChunk(
                    id=f"{doc_id}_chunk_{i}",
                    document_id=doc_id,
                    chunk_index=i,
                    content=chunk_text,
                    metadata=metadata.dict(),
                    created_at=datetime.utcnow()
                )
                document_chunks.append(chunk)
                
            logger.info(f"Processed document {doc_id} into {len(document_chunks)} chunks")
            return document_chunks
            
        except Exception as e:
            logger.error(f"Error processing document {doc_id}: {str(e)}")
            raise
    
    def _chunk_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Split text into overlapping chunks"""
        if len(text) <= chunk_size:
            return [text]
            
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Find the last sentence boundary within the chunk
            if end < len(text):
                # Look for sentence endings
                for punct in ['. ', '! ', '? ', '\n\n']:
                    last_punct = text.rfind(punct, start, end)
                    if last_punct != -1:
                        end = last_punct + len(punct)
                        break
                        
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
                
            start = end - overlap
            if start >= len(text):
                break
                
        return chunks


class EmbeddingService:
    """Embedding generation service using Gemini text embedding models"""
    
    def __init__(self, genai_client):
        self.genai_client = genai_client
        self.embedding_model = "text-embedding-004"
        
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        try:
            embeddings = []
            
            # Process in batches to avoid rate limits
            batch_size = 10
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                batch_embeddings = await self._generate_batch_embeddings(batch)
                embeddings.extend(batch_embeddings)
                
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            raise
    
    async def _generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts"""
        embeddings = []
        
        for text in texts:
            try:
                # Use the Gemini embedding API
                text_part = types.Part.from_text(text=text)
                
                response = self.genai_client.models.embed_content(
                    model=self.embedding_model,
                    content=[text_part],
                    config=types.EmbedContentConfig(
                        task_type="RETRIEVAL_DOCUMENT"
                    )
                )
                
                embeddings.append(response.embedding.values)
                
            except Exception as e:
                logger.error(f"Error generating embedding for text: {str(e)}")
                # Use zero vector as fallback
                embeddings.append([0.0] * 768)
                
        return embeddings


class RAGService:
    """Main RAG service coordinating document processing, embedding, and retrieval"""
    
    def __init__(self, genai_client, vector_store: VectorStoreService, 
                 gcs_service: GCSService):
        self.genai_client = genai_client
        self.vector_store = vector_store
        self.gcs_service = gcs_service
        self.document_processor = DocumentProcessor()
        self.embedding_service = EmbeddingService(genai_client)
        
        # Knowledge bases storage
        self.knowledge_bases: Dict[str, KnowledgeBase] = {}
        
    async def create_knowledge_base(self, name: str, description: str = "") -> KnowledgeBase:
        """Create a new knowledge base"""
        kb_id = hashlib.md5(f"{name}_{datetime.utcnow()}".encode()).hexdigest()
        
        knowledge_base = KnowledgeBase(
            id=kb_id,
            name=name,
            description=description,
            document_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.knowledge_bases[kb_id] = knowledge_base
        
        # Create vector store collection for this knowledge base
        await self.vector_store.create_collection(kb_id)
        
        logger.info(f"Created knowledge base: {name} ({kb_id})")
        return knowledge_base
    
    async def add_document_to_kb(self, kb_id: str, content: str, 
                                metadata: DocumentMetadata) -> str:
        """Add a document to a knowledge base"""
        if kb_id not in self.knowledge_bases:
            raise ValueError(f"Knowledge base {kb_id} not found")
            
        try:
            # Generate document ID
            doc_id = hashlib.md5(f"{metadata.title}_{metadata.source}_{datetime.utcnow()}".encode()).hexdigest()
            
            # Process document into chunks
            chunks = await self.document_processor.process_document(content, doc_id, metadata)
            
            # Generate embeddings for chunks
            chunk_texts = [chunk.content for chunk in chunks]
            embeddings = await self.embedding_service.generate_embeddings(chunk_texts)
            
            # Add embeddings to chunks
            for chunk, embedding in zip(chunks, embeddings):
                chunk.embedding = embedding
                
            # Store chunks in vector store
            await self.vector_store.store_chunks(kb_id, chunks)
            
            # Upload document content to GCS
            doc_blob_name = f"knowledge_bases/{kb_id}/documents/{doc_id}.txt"
            gcs_uri = await self.gcs_service.upload_to_gcs(
                content=content,
                destination_blob_name=doc_blob_name,
                content_type="text/plain"
            )
            
            # Update knowledge base metadata
            kb = self.knowledge_bases[kb_id]
            kb.document_count += 1
            kb.updated_at = datetime.utcnow()
            
            logger.info(f"Added document {doc_id} to knowledge base {kb_id}")
            return doc_id
            
        except Exception as e:
            logger.error(f"Error adding document to knowledge base {kb_id}: {str(e)}")
            raise
    
    async def query_knowledge_base(self, kb_id: str, query: RAGQuery) -> RAGResponse:
        """Query a knowledge base using RAG"""
        if kb_id not in self.knowledge_bases:
            raise ValueError(f"Knowledge base {kb_id} not found")
            
        try:
            # Generate query embedding
            query_embeddings = await self.embedding_service.generate_embeddings([query.query])
            query_embedding = query_embeddings[0]
            
            # Search for similar chunks
            similar_chunks = await self.vector_store.search_similar(
                kb_id, query_embedding, k=query.k
            )
            
            # Filter by similarity threshold
            filtered_chunks = [
                chunk for chunk in similar_chunks 
                if chunk.similarity_score >= query.similarity_threshold
            ]
            
            # Prepare context from retrieved chunks
            context_parts = []
            search_results = []
            
            for chunk in filtered_chunks[:query.k]:
                context_parts.append(f"Source: {chunk.metadata.get('title', 'Unknown')}\n{chunk.content}")
                search_results.append(SearchResult(
                    chunk_id=chunk.id,
                    content=chunk.content,
                    metadata=chunk.metadata,
                    similarity_score=chunk.similarity_score
                ))
            
            context = "\n\n---\n\n".join(context_parts)
            
            # Generate response using retrieved context
            response_text = await self._generate_rag_response(query.query, context)
            
            return RAGResponse(
                response=response_text,
                sources=search_results,
                query=query.query,
                context_used=len(filtered_chunks) > 0
            )
            
        except Exception as e:
            logger.error(f"Error querying knowledge base {kb_id}: {str(e)}")
            raise
    
    async def _generate_rag_response(self, query: str, context: str) -> str:
        """Generate response using retrieved context"""
        try:
            prompt = f"""Based on the following context, please answer the question. If the context doesn't contain enough information to answer the question, say so.

Context:
{context}

Question: {query}

Answer:"""

            text_part = types.Part.from_text(text=prompt)
            contents = [types.Content(role="user", parts=[text_part])]
            
            config = types.GenerateContentConfig(
                max_output_tokens=2048,
                temperature=0.7
            )
            
            response = self.genai_client.models.generate_content(
                model=settings.DEFAULT_MODEL,
                contents=contents,
                config=config
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Error generating RAG response: {str(e)}")
            raise
    
    async def list_knowledge_bases(self) -> List[KnowledgeBase]:
        """List all knowledge bases"""
        return list(self.knowledge_bases.values())
    
    async def get_knowledge_base(self, kb_id: str) -> Optional[KnowledgeBase]:
        """Get a specific knowledge base"""
        return self.knowledge_bases.get(kb_id)
    
    async def delete_knowledge_base(self, kb_id: str) -> bool:
        """Delete a knowledge base and all its documents"""
        if kb_id not in self.knowledge_bases:
            return False
            
        try:
            # Delete from vector store
            await self.vector_store.delete_collection(kb_id)
            
            # Delete from GCS
            await self.gcs_service.delete_prefix(f"knowledge_bases/{kb_id}/")
            
            # Remove from memory
            del self.knowledge_bases[kb_id]
            
            logger.info(f"Deleted knowledge base {kb_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting knowledge base {kb_id}: {str(e)}")
            return False