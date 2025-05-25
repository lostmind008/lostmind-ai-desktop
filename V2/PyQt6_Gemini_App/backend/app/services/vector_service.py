"""
Vector database service for RAG (Retrieval-Augmented Generation) capabilities.
Supports document embedding, similarity search, and knowledge base management.
"""

import hashlib
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import chromadb
import numpy as np
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from app.core.config import Settings
from app.models.knowledge import Document, KnowledgeChunk

logger = logging.getLogger(__name__)

class VectorService:
    """ChromaDB-based vector database service for RAG functionality."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client: Optional[chromadb.Client] = None
        self.embedding_model: Optional[SentenceTransformer] = None
        self.collection_name = "lostmind_knowledge"
        self.embedding_dimension = 384  # all-MiniLM-L6-v2 dimension
        
    async def initialize(self) -> bool:
        """Initialize vector database and embedding model."""
        try:
            # Initialize ChromaDB client
            if self.settings.vector_db_path:
                # Persistent storage
                self.client = chromadb.PersistentClient(
                    path=self.settings.vector_db_path,
                    settings=ChromaSettings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
            else:
                # In-memory storage for development
                self.client = chromadb.Client(
                    settings=ChromaSettings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
            
            # Initialize embedding model
            model_name = getattr(self.settings, 'embedding_model', 'all-MiniLM-L6-v2')
            self.embedding_model = SentenceTransformer(model_name)
            
            # Create or get collection
            try:
                self.collection = self.client.get_collection(
                    name=self.collection_name
                )
                logger.info(f"Connected to existing collection: {self.collection_name}")
            except ValueError:
                # Collection doesn't exist, create it
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "LostMindAI knowledge base"}
                )
                logger.info(f"Created new collection: {self.collection_name}")
            
            logger.info("Vector service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize vector service: {e}")
            return False
    
    def _generate_chunk_id(self, document_id: str, chunk_index: int) -> str:
        """Generate unique ID for a document chunk."""
        return f"{document_id}_chunk_{chunk_index}"
    
    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks for better retrieval."""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings within overlap range
                for i in range(end - overlap, end):
                    if i > start and text[i] in '.!?\n':
                        end = i + 1
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
            if start >= len(text):
                break
                
        return chunks
    
    async def add_document(
        self, 
        document: Document,
        chunk_size: int = 1000,
        overlap: int = 200
    ) -> bool:
        """Add a document to the vector database with chunking."""
        if not self.client or not self.embedding_model:
            logger.error("Vector service not initialized")
            return False
        
        try:
            # Generate document hash for deduplication
            content_hash = hashlib.md5(document.content.encode()).hexdigest()
            
            # Check if document already exists
            existing = self.collection.get(
                where={"document_hash": content_hash}
            )
            
            if existing['ids']:
                logger.info(f"Document {document.title} already exists, skipping")
                return True
            
            # Chunk the document
            chunks = self._chunk_text(document.content, chunk_size, overlap)
            
            # Generate embeddings for all chunks
            embeddings = self.embedding_model.encode(chunks).tolist()
            
            # Prepare data for ChromaDB
            ids = []
            metadatas = []
            
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_id = self._generate_chunk_id(document.id, i)
                ids.append(chunk_id)
                
                metadata = {
                    "document_id": document.id,
                    "document_title": document.title,
                    "document_hash": content_hash,
                    "document_type": document.document_type,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "created_at": document.created_at.isoformat(),
                    "source": getattr(document, 'source', 'unknown'),
                    "author": getattr(document, 'author', 'unknown')
                }
                
                # Add tags if available
                if hasattr(document, 'tags') and document.tags:
                    metadata["tags"] = ",".join(document.tags)
                
                metadatas.append(metadata)
            
            # Add to collection
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=chunks,
                metadatas=metadatas
            )
            
            logger.info(
                f"Added document '{document.title}' with {len(chunks)} chunks"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to add document {document.title}: {e}")
            return False
    
    async def search_similar(
        self,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[KnowledgeChunk]:
        """Search for similar content using semantic similarity."""
        if not self.client or not self.embedding_model:
            logger.warning("Vector service not initialized")
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query]).tolist()[0]
            
            # Prepare where clause for filtering
            where_clause = filters or {}
            
            # Search in collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where_clause if where_clause else None,
                include=["documents", "metadatas", "distances"]
            )
            
            chunks = []
            
            if results['ids'] and results['ids'][0]:
                for i, (chunk_id, document, metadata, distance) in enumerate(zip(
                    results['ids'][0],
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                )):
                    # Convert distance to similarity score (lower distance = higher similarity)
                    similarity_score = 1.0 / (1.0 + distance)
                    
                    if similarity_score >= score_threshold:
                        chunk = KnowledgeChunk(
                            id=chunk_id,
                            content=document,
                            document_id=metadata['document_id'],
                            document_title=metadata['document_title'],
                            chunk_index=metadata['chunk_index'],
                            similarity_score=similarity_score,
                            metadata=metadata
                        )
                        chunks.append(chunk)
            
            logger.info(f"Found {len(chunks)} relevant chunks for query")
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to search similar content: {e}")
            return []
    
    async def get_document_chunks(
        self, 
        document_id: str
    ) -> List[KnowledgeChunk]:
        """Get all chunks for a specific document."""
        if not self.client:
            return []
        
        try:
            results = self.collection.get(
                where={"document_id": document_id},
                include=["documents", "metadatas"]
            )
            
            chunks = []
            
            if results['ids']:
                for chunk_id, document, metadata in zip(
                    results['ids'],
                    results['documents'],
                    results['metadatas']
                ):
                    chunk = KnowledgeChunk(
                        id=chunk_id,
                        content=document,
                        document_id=metadata['document_id'],
                        document_title=metadata['document_title'],
                        chunk_index=metadata['chunk_index'],
                        similarity_score=1.0,  # Not applicable for direct retrieval
                        metadata=metadata
                    )
                    chunks.append(chunk)
            
            # Sort by chunk index
            chunks.sort(key=lambda x: x.chunk_index)
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to get document chunks for {document_id}: {e}")
            return []
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete all chunks for a document."""
        if not self.client:
            return False
        
        try:
            # Get all chunk IDs for the document
            results = self.collection.get(
                where={"document_id": document_id},
                include=["documents"]
            )
            
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                logger.info(f"Deleted {len(results['ids'])} chunks for document {document_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            return False
    
    async def update_document(
        self,
        document: Document,
        chunk_size: int = 1000,
        overlap: int = 200
    ) -> bool:
        """Update a document by deleting old chunks and adding new ones."""
        # Delete existing chunks
        await self.delete_document(document.id)
        
        # Add updated document
        return await self.add_document(document, chunk_size, overlap)
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector database collection."""
        if not self.client:
            return {"status": "not_initialized"}
        
        try:
            collection_count = self.collection.count()
            
            # Get sample of documents to analyze types
            sample_results = self.collection.get(
                limit=100,
                include=["metadatas"]
            )
            
            document_types = {}
            unique_documents = set()
            
            if sample_results['metadatas']:
                for metadata in sample_results['metadatas']:
                    doc_type = metadata.get('document_type', 'unknown')
                    document_types[doc_type] = document_types.get(doc_type, 0) + 1
                    unique_documents.add(metadata.get('document_id', 'unknown'))
            
            return {
                "status": "active",
                "total_chunks": collection_count,
                "unique_documents": len(unique_documents),
                "document_types": document_types,
                "embedding_model": self.embedding_model.get_model_name() if self.embedding_model else "unknown",
                "embedding_dimension": self.embedding_dimension,
                "collection_name": self.collection_name
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"status": "error", "error": str(e)}
    
    async def reset_collection(self) -> bool:
        """Reset the entire collection (use with caution)."""
        if not self.client:
            return False
        
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "LostMindAI knowledge base"}
            )
            logger.info("Collection reset successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset collection: {e}")
            return False
