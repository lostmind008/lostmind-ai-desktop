#!/usr/bin/env python3
"""
RAG Setup and Demo Script

This script demonstrates the RAG capabilities by:
1. Creating a sample knowledge base
2. Adding documents from various sources
3. Running sample queries to show RAG in action

Run: python setup_rag_demo.py
"""

import asyncio
import logging
import json
from datetime import datetime
from pathlib import Path

from app.services.rag_service import RAGService
from app.services.vector_store import VectorStoreService
from app.services.gcs_service import GCSService
from app.services.genai_service import GenAIService
from app.models.rag import (
    DocumentMetadata, DocumentType, RAGQuery, 
    KnowledgeBaseCreateRequest
)
from app.core.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGDemo:
    """RAG demonstration and setup class"""
    
    def __init__(self):
        self.settings = get_settings()
        self.rag_service = None
        
    async def initialize_services(self):
        """Initialize all required services"""
        logger.info("Initializing RAG services...")
        
        genai_service = GenAIService()
        vector_store = VectorStoreService()
        gcs_service = GCSService()
        
        self.rag_service = RAGService(
            genai_client=genai_service.client,
            vector_store=vector_store,
            gcs_service=gcs_service
        )
        
        logger.info("Services initialized successfully")
    
    async def create_demo_knowledge_base(self):
        """Create a sample knowledge base with demo content"""
        logger.info("Creating demo knowledge base...")
        
        # Create knowledge base
        kb = await self.rag_service.create_knowledge_base(
            name="LostMindAI Demo Knowledge Base",
            description="A demonstration knowledge base showing RAG capabilities"
        )
        
        logger.info(f"Created knowledge base: {kb.name} ({kb.id})")
        
        # Sample documents to add
        demo_documents = [
            {
                "title": "Introduction to LostMindAI",
                "content": """
                LostMindAI is an advanced AI assistant platform that combines the power of 
                Google's Gemini models with sophisticated retrieval-augmented generation (RAG) 
                capabilities. The platform provides both desktop and web interfaces, allowing 
                users to have intelligent conversations enhanced by their own knowledge bases.
                
                Key features include:
                - Multi-modal AI conversations (text, images, documents)
                - Custom knowledge base creation and management
                - RAG-powered responses using your own documents
                - Real-time streaming responses
                - Advanced thinking process visualization
                - Cross-platform compatibility (desktop PyQt6 app and web interface)
                
                The platform is built on FastAPI for the backend, PostgreSQL with pgvector 
                for vector storage, and offers both PyQt6 desktop and Next.js web clients.
                """,
                "metadata": DocumentMetadata(
                    title="Introduction to LostMindAI",
                    source="internal_documentation",
                    document_type=DocumentType.TEXT,
                    author="LostMindAI Team",
                    tags=["introduction", "features", "platform"]
                )
            },
            {
                "title": "RAG Implementation Guide",
                "content": """
                Retrieval-Augmented Generation (RAG) is a powerful technique that enhances 
                large language models by providing them with relevant context from external 
                knowledge sources. In LostMindAI, RAG is implemented using:
                
                1. Document Processing:
                   - Text chunking with overlap for better context preservation
                   - Multiple document format support (PDF, text, markdown, etc.)
                   - Metadata extraction and storage
                
                2. Embedding Generation:
                   - Using Google's text-embedding-004 model
                   - 768-dimensional embeddings for semantic similarity
                   - Batch processing for efficiency
                
                3. Vector Storage:
                   - PostgreSQL with pgvector extension
                   - Cosine similarity search
                   - Indexed for fast retrieval
                
                4. Query Processing:
                   - Semantic search across knowledge bases
                   - Similarity threshold filtering
                   - Context length management
                   - Multi-knowledge base queries
                
                5. Response Generation:
                   - Context-aware prompting
                   - Source attribution
                   - Confidence scoring
                """,
                "metadata": DocumentMetadata(
                    title="RAG Implementation Guide",
                    source="technical_documentation",
                    document_type=DocumentType.MARKDOWN,
                    tags=["rag", "implementation", "technical", "guide"]
                )
            },
            {
                "title": "API Endpoints Reference",
                "content": """
                LostMindAI Backend API provides comprehensive endpoints for all platform features:
                
                Knowledge Base Management:
                - POST /api/v1/rag/knowledge-bases - Create new knowledge base
                - GET /api/v1/rag/knowledge-bases - List all knowledge bases
                - GET /api/v1/rag/knowledge-bases/{id} - Get specific knowledge base
                - DELETE /api/v1/rag/knowledge-bases/{id} - Delete knowledge base
                
                Document Management:
                - POST /api/v1/rag/knowledge-bases/{id}/documents - Add document to KB
                - POST /api/v1/rag/knowledge-bases/{id}/upload-file - Upload file to KB
                
                RAG Queries:
                - POST /api/v1/rag/knowledge-bases/{id}/query - Query single KB
                - POST /api/v1/rag/query-multiple - Query multiple KBs
                
                Chat with RAG:
                - POST /api/v1/chat/sessions/{id}/rag - Chat with RAG context
                - POST /api/v1/chat/sessions/{id}/context-search - Search for context
                - POST /api/v1/chat/sessions/{id}/enable-rag - Enable RAG for session
                
                All endpoints support authentication and provide detailed error responses.
                """,
                "metadata": DocumentMetadata(
                    title="API Endpoints Reference",
                    source="api_documentation",
                    document_type=DocumentType.TEXT,
                    tags=["api", "endpoints", "reference", "documentation"]
                )
            },
            {
                "title": "Vector Search and Similarity",
                "content": """
                Vector search is at the heart of LostMindAI's RAG implementation. The system 
                uses semantic embeddings to find relevant content:
                
                Embedding Model: text-embedding-004
                - 768 dimensions
                - Trained on diverse text corpus
                - Optimized for retrieval tasks
                
                Similarity Metrics:
                - Cosine similarity (default)
                - Configurable similarity thresholds
                - Support for hybrid search (future)
                
                Search Process:
                1. Query embedding generation
                2. Vector similarity search in PostgreSQL
                3. Threshold filtering
                4. Ranking by relevance
                5. Context aggregation
                
                Performance Optimizations:
                - IVFFlat indexing for fast search
                - Redis caching for frequently accessed embeddings
                - Batch processing for bulk operations
                - Async processing for real-time responses
                
                The vector store can handle millions of documents while maintaining 
                sub-second query response times.
                """,
                "metadata": DocumentMetadata(
                    title="Vector Search and Similarity",
                    source="technical_documentation",
                    document_type=DocumentType.TEXT,
                    tags=["vector", "search", "similarity", "performance"]
                )
            }
        ]
        
        # Add documents to knowledge base
        for doc_data in demo_documents:
            try:
                doc_id = await self.rag_service.add_document_to_kb(
                    kb_id=kb.id,
                    content=doc_data["content"],
                    metadata=doc_data["metadata"]
                )
                logger.info(f"Added document: {doc_data['title']} ({doc_id})")
            except Exception as e:
                logger.error(f"Error adding document {doc_data['title']}: {str(e)}")
        
        return kb
    
    async def run_demo_queries(self, kb_id: str):
        """Run demonstration queries to show RAG capabilities"""
        logger.info("Running demo queries...")
        
        demo_queries = [
            {
                "query": "What is LostMindAI and what are its main features?",
                "description": "Basic information query"
            },
            {
                "query": "How does the RAG implementation work in LostMindAI?",
                "description": "Technical implementation query"
            },
            {
                "query": "What API endpoints are available for knowledge base management?",
                "description": "API reference query"
            },
            {
                "query": "Explain vector search and similarity in the platform",
                "description": "Vector search technical details"
            },
            {
                "query": "How can I create a new knowledge base and add documents?",
                "description": "Usage instructions query"
            }
        ]
        
        results = []
        
        for demo_query in demo_queries:
            try:
                logger.info(f"\n--- {demo_query['description']} ---")
                logger.info(f"Query: {demo_query['query']}")
                
                rag_query = RAGQuery(
                    query=demo_query["query"],
                    k=3,
                    similarity_threshold=0.6
                )
                
                response = await self.rag_service.query_knowledge_base(kb_id, rag_query)
                
                logger.info(f"Response: {response.response[:200]}...")
                logger.info(f"Sources found: {len(response.sources)}")
                
                if response.sources:
                    for i, source in enumerate(response.sources[:2]):
                        logger.info(f"  Source {i+1}: {source.metadata.get('title', 'Unknown')} "
                                  f"(similarity: {source.similarity_score:.3f})")
                
                results.append({
                    "query": demo_query["query"],
                    "response": response.response,
                    "sources_count": len(response.sources),
                    "avg_similarity": sum(s.similarity_score for s in response.sources) / len(response.sources) if response.sources else 0
                })
                
            except Exception as e:
                logger.error(f"Error running query '{demo_query['query']}': {str(e)}")
        
        return results
    
    async def generate_demo_report(self, kb, query_results):
        """Generate a demonstration report"""
        logger.info("Generating demo report...")
        
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "knowledge_base": {
                "id": kb.id,
                "name": kb.name,
                "description": kb.description,
                "document_count": kb.document_count
            },
            "query_results": query_results,
            "summary": {
                "total_queries": len(query_results),
                "avg_sources_per_query": sum(r["sources_count"] for r in query_results) / len(query_results) if query_results else 0,
                "avg_similarity_score": sum(r["avg_similarity"] for r in query_results) / len(query_results) if query_results else 0
            }
        }
        
        # Save report to file
        report_path = Path("rag_demo_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Demo report saved to: {report_path}")
        
        # Print summary
        print("\n" + "="*60)
        print("RAG DEMONSTRATION SUMMARY")
        print("="*60)
        print(f"Knowledge Base: {kb.name}")
        print(f"Documents: {kb.document_count}")
        print(f"Queries Tested: {report['summary']['total_queries']}")
        print(f"Avg Sources per Query: {report['summary']['avg_sources_per_query']:.1f}")
        print(f"Avg Similarity Score: {report['summary']['avg_similarity_score']:.3f}")
        print("="*60)
        
        return report
    
    async def run_full_demo(self):
        """Run the complete RAG demonstration"""
        try:
            # Initialize services
            await self.initialize_services()
            
            # Create demo knowledge base
            kb = await self.create_demo_knowledge_base()
            
            # Wait a moment for processing
            await asyncio.sleep(2)
            
            # Run demo queries
            query_results = await self.run_demo_queries(kb.id)
            
            # Generate report
            report = await self.generate_demo_report(kb, query_results)
            
            logger.info("RAG demonstration completed successfully!")
            
            return kb, report
            
        except Exception as e:
            logger.error(f"Demo failed: {str(e)}")
            raise


async def main():
    """Main demo function"""
    demo = RAGDemo()
    
    try:
        kb, report = await demo.run_full_demo()
        
        print(f"\nDemo completed! Knowledge base ID: {kb.id}")
        print("You can now use this knowledge base for testing RAG queries.")
        print("Report saved to: rag_demo_report.json")
        
    except Exception as e:
        print(f"Demo failed: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())