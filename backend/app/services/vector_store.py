# backend/app/services/vector_store.py

import logging
import asyncio
from typing import List, Dict, Any, Optional
import numpy as np
from datetime import datetime

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, text
from pgvector.sqlalchemy import Vector

from app.core.database import get_db_session
from app.models.rag import DocumentChunk
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class VectorStoreService:
    """Vector store service using PostgreSQL with pgvector extension"""
    
    def __init__(self):
        self.dimension = 768  # Gemini embedding dimension
        self._redis_client = None
        
    async def get_redis_client(self):
        """Get Redis client for caching"""
        if self._redis_client is None:
            self._redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
        return self._redis_client
    
    async def create_collection(self, collection_name: str) -> bool:
        """Create a vector collection (table) for a knowledge base"""
        try:
            async with get_db_session() as session:
                # Create table for this collection
                table_name = f"vectors_{collection_name.replace('-', '_')}"
                
                create_table_sql = f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id VARCHAR PRIMARY KEY,
                    document_id VARCHAR NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    metadata JSONB DEFAULT '{{}}',
                    embedding vector({self.dimension}),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS {table_name}_embedding_idx 
                ON {table_name} USING ivfflat (embedding vector_cosine_ops);
                
                CREATE INDEX IF NOT EXISTS {table_name}_document_idx 
                ON {table_name} (document_id);
                """
                
                await session.execute(text(create_table_sql))
                await session.commit()
                
            logger.info(f"Created vector collection: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating collection {collection_name}: {str(e)}")
            return False
    
    async def store_chunks(self, collection_name: str, chunks: List[DocumentChunk]) -> bool:
        """Store document chunks with embeddings"""
        try:
            async with get_db_session() as session:
                table_name = f"vectors_{collection_name.replace('-', '_')}"
                
                for chunk in chunks:
                    # Convert embedding to vector format
                    embedding_vector = f"[{','.join(map(str, chunk.embedding))}]"
                    
                    insert_sql = f"""
                    INSERT INTO {table_name} 
                    (id, document_id, chunk_index, content, metadata, embedding)
                    VALUES (:id, :document_id, :chunk_index, :content, :metadata, :embedding::vector)
                    ON CONFLICT (id) DO UPDATE SET
                        content = EXCLUDED.content,
                        metadata = EXCLUDED.metadata,
                        embedding = EXCLUDED.embedding,
                        updated_at = CURRENT_TIMESTAMP
                    """
                    
                    await session.execute(text(insert_sql), {
                        'id': chunk.id,
                        'document_id': chunk.document_id,
                        'chunk_index': chunk.chunk_index,
                        'content': chunk.content,
                        'metadata': chunk.metadata,
                        'embedding': embedding_vector
                    })
                
                await session.commit()
                
            # Cache embeddings in Redis for faster access
            redis_client = await self.get_redis_client()
            for chunk in chunks:
                cache_key = f"embedding:{collection_name}:{chunk.id}"
                await redis_client.set(
                    cache_key, 
                    str(chunk.embedding), 
                    ex=3600  # 1 hour cache
                )
            
            logger.info(f"Stored {len(chunks)} chunks in collection {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing chunks in {collection_name}: {str(e)}")
            return False
    
    async def search_similar(self, collection_name: str, query_embedding: List[float], 
                           k: int = 5, similarity_threshold: float = 0.7) -> List[DocumentChunk]:
        """Search for similar chunks using cosine similarity"""
        try:
            async with get_db_session() as session:
                table_name = f"vectors_{collection_name.replace('-', '_')}"
                query_vector = f"[{','.join(map(str, query_embedding))}]"
                
                search_sql = f"""
                SELECT 
                    id, document_id, chunk_index, content, metadata,
                    1 - (embedding <=> :query_vector::vector) as similarity_score
                FROM {table_name}
                WHERE 1 - (embedding <=> :query_vector::vector) >= :threshold
                ORDER BY embedding <=> :query_vector::vector
                LIMIT :k
                """
                
                result = await session.execute(text(search_sql), {
                    'query_vector': query_vector,
                    'threshold': similarity_threshold,
                    'k': k
                })
                
                chunks = []
                for row in result:
                    chunk = DocumentChunk(
                        id=row.id,
                        document_id=row.document_id,
                        chunk_index=row.chunk_index,
                        content=row.content,
                        metadata=row.metadata or {},
                        embedding=[],  # Don't load embedding for search results
                        similarity_score=row.similarity_score,
                        created_at=datetime.utcnow()
                    )
                    chunks.append(chunk)
                
            logger.info(f"Found {len(chunks)} similar chunks in {collection_name}")
            return chunks
            
        except Exception as e:
            logger.error(f"Error searching collection {collection_name}: {str(e)}")
            return []
    
    async def get_chunk_by_id(self, collection_name: str, chunk_id: str) -> Optional[DocumentChunk]:
        """Get a specific chunk by ID"""
        try:
            async with get_db_session() as session:
                table_name = f"vectors_{collection_name.replace('-', '_')}"
                
                select_sql = f"""
                SELECT id, document_id, chunk_index, content, metadata, created_at
                FROM {table_name}
                WHERE id = :chunk_id
                """
                
                result = await session.execute(text(select_sql), {'chunk_id': chunk_id})
                row = result.first()
                
                if row:
                    return DocumentChunk(
                        id=row.id,
                        document_id=row.document_id,
                        chunk_index=row.chunk_index,
                        content=row.content,
                        metadata=row.metadata or {},
                        embedding=[],
                        created_at=row.created_at
                    )
                    
            return None
            
        except Exception as e:
            logger.error(f"Error getting chunk {chunk_id}: {str(e)}")
            return None
    
    async def delete_document_chunks(self, collection_name: str, document_id: str) -> bool:
        """Delete all chunks for a specific document"""
        try:
            async with get_db_session() as session:
                table_name = f"vectors_{collection_name.replace('-', '_')}"
                
                delete_sql = f"DELETE FROM {table_name} WHERE document_id = :document_id"
                await session.execute(text(delete_sql), {'document_id': document_id})
                await session.commit()
                
            # Clear Redis cache
            redis_client = await self.get_redis_client()
            cache_pattern = f"embedding:{collection_name}:{document_id}_*"
            
            async for key in redis_client.scan_iter(match=cache_pattern):
                await redis_client.delete(key)
                
            logger.info(f"Deleted chunks for document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document chunks: {str(e)}")
            return False
    
    async def delete_collection(self, collection_name: str) -> bool:
        """Delete an entire collection (table)"""
        try:
            async with get_db_session() as session:
                table_name = f"vectors_{collection_name.replace('-', '_')}"
                
                drop_table_sql = f"DROP TABLE IF EXISTS {table_name}"
                await session.execute(text(drop_table_sql))
                await session.commit()
                
            # Clear Redis cache
            redis_client = await self.get_redis_client()
            cache_pattern = f"embedding:{collection_name}:*"
            
            async for key in redis_client.scan_iter(match=cache_pattern):
                await redis_client.delete(key)
                
            logger.info(f"Deleted collection {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting collection {collection_name}: {str(e)}")
            return False
    
    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get statistics for a collection"""
        try:
            async with get_db_session() as session:
                table_name = f"vectors_{collection_name.replace('-', '_')}"
                
                stats_sql = f"""
                SELECT 
                    COUNT(*) as total_chunks,
                    COUNT(DISTINCT document_id) as unique_documents,
                    AVG(LENGTH(content)) as avg_content_length
                FROM {table_name}
                """
                
                result = await session.execute(text(stats_sql))
                row = result.first()
                
                if row:
                    return {
                        'total_chunks': row.total_chunks,
                        'unique_documents': row.unique_documents,
                        'avg_content_length': float(row.avg_content_length or 0)
                    }
                    
            return {'total_chunks': 0, 'unique_documents': 0, 'avg_content_length': 0}
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            return {'error': str(e)}