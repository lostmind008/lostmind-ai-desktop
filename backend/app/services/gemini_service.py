"""
Gemini AI Service for LostMindAI Backend.

Provides unified interface to Google's Gemini models with enhanced features
including thinking budgets, caching, and cost optimization based on patterns
from the desktop application and enterprise RAG backend.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, AsyncGenerator
from pathlib import Path

from google.cloud import aiplatform
from google import genai
from google.genai import types

from app.core.config import Settings
from app.models.chat import (
    ChatMessage, ChatSession, SessionCreateRequest, ChatResponse, 
    MessageRole, ModelInfo, GenerationConfig  # ModelSelection, UsageStats - TODO: Add these models
)
from app.models.rag import ChatWithRAGRequest, RAGResponse, AdvancedRAGQuery, RAGContext

# Placeholder logger until utils.logger is created
import logging
logger = logging.getLogger(__name__)


class ComplexityLevel:
    """Query complexity levels for thinking budget optimization."""
    NONE = "none"           # 0 tokens - No thinking needed
    LIGHT = "light"         # 1024 tokens - Light reasoning
    MODERATE = "moderate"   # 4096 tokens - Moderate complexity
    DEEP = "deep"          # 8192 tokens - Deep reasoning
    MAXIMUM = "maximum"     # 24576 tokens - Maximum reasoning


class GeminiService:
    """
    Enhanced Gemini AI service with unified client architecture.
    
    Features from desktop app + enterprise patterns:
    - Unified GenAI client (vertexai=True pattern)
    - Thinking budget optimization
    - Caching integration
    - Cost tracking and optimization
    - Session management
    - File handling capabilities
    """
    
    def __init__(self, settings: Settings, cache_service=None):
        """Initialize Gemini service with enhanced capabilities."""
        self.settings = settings
        self.cache_service = cache_service
        self.client = None
        self.models_cache = {}
        self.sessions: Dict[str, ChatSession] = {}
        
        # Thinking budget configuration
        self.thinking_budget = ThinkingBudget(
            auto_detect=settings.THINKING_BUDGET_AUTO,
            light=settings.THINKING_BUDGET_LIGHT,
            moderate=settings.THINKING_BUDGET_MODERATE,
            deep=settings.THINKING_BUDGET_DEEP,
            maximum=settings.THINKING_BUDGET_MAXIMUM
        )
        
        # Cost tracking
        self.usage_stats = {
            "total_requests": 0,
            "total_tokens": 0,
            "cache_hits": 0,
            "thinking_budget_used": {},
            "cost_saved": 0.0
        }
    
    async def startup(self):
        """Initialize the Gemini service with unified client."""
        try:
            logger.info("Starting Gemini service...")
            
            # Initialize Vertex AI if using cloud
            if self.settings.GOOGLE_CLOUD_PROJECT:
                aiplatform.init(
                    project=self.settings.GOOGLE_CLOUD_PROJECT,
                    location=self.settings.GOOGLE_CLOUD_LOCATION
                )
                
                # Create unified GenAI client (enhanced pattern from YouTube summarizer)
                self.client = genai.Client(
                    vertexai=True,
                    project=self.settings.GOOGLE_CLOUD_PROJECT,
                    location=self.settings.GOOGLE_CLOUD_LOCATION
                )
                logger.info(f"Initialized Vertex AI client: {self.settings.GOOGLE_CLOUD_PROJECT}")
                
            elif self.settings.GEMINI_API_KEY:
                # Direct API key approach
                self.client = genai.Client(
                    api_key=self.settings.GEMINI_API_KEY,
                    vertexai=False
                )
                logger.info("Initialized direct API client")
                
            else:
                raise ValueError("No valid authentication configuration found")
            
            # Load available models
            await self._discover_models()
            
            logger.info("Gemini service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Gemini service: {e}")
            raise
    
    async def shutdown(self):
        """Cleanup the Gemini service."""
        logger.info("Shutting down Gemini service...")
        # Clean up resources, save usage stats, etc.
        self.client = None
    
    async def _discover_models(self):
        """Discover available models and cache their information."""
        try:
            # Use models from configuration as baseline
            config_models = self.settings.gemini_config.get("models", [])
            
            for model_config in config_models:
                model_info = ModelInfo(
                    id=model_config["id"],
                    display_name=model_config["display_name"],
                    description=model_config["description"],
                    type=model_config.get("type", "base"),
                    supported_methods=model_config.get("supported_methods", []),
                    supports_search="googleSearch" in model_config.get("supported_methods", []),
                    supports_thinking="thoughtSummarization" in model_config.get("supported_methods", [])
                )
                self.models_cache[model_info.id] = model_info
            
            logger.info(f"Loaded {len(self.models_cache)} models")
            
        except Exception as e:
            logger.error(f"Error discovering models: {e}")
    
    def get_available_models(self) -> List[ModelInfo]:
        """Get list of available models."""
        return list(self.models_cache.values())
    
    def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """Get information about a specific model."""
        return self.models_cache.get(model_id)
    
    async def create_session(
        self,
        model_id: str,
        system_instruction: Optional[str] = None,
        generation_config: Optional[GenerationConfig] = None
    ) -> ChatSession:
        """Create a new chat session."""
        session_id = str(uuid.uuid4())
        
        session = ChatSession(
            id=session_id,
            model_id=model_id,
            system_instruction=system_instruction or "You are a helpful AI assistant.",
            settings={
                "generation_config": generation_config.dict() if generation_config else {},
                "thinking_budget": self.thinking_budget.dict()
            }
        )
        
        self.sessions[session_id] = session
        logger.info(f"Created new session: {session_id} with model: {model_id}")
        
        return session
    
    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get existing chat session."""
        return self.sessions.get(session_id)
    
    async def process_chat_message(
        self,
        message: str,
        session_id: str,
        files: List[str] = None,
        stream: bool = True,
        use_search: bool = True,
        thinking_mode: bool = False
    ) -> ChatResponse:
        """
        Process a chat message with enhanced capabilities.
        
        Based on desktop app logic with enterprise enhancements.
        """
        start_time = time.time()
        
        try:
            # Get or create session
            session = await self.get_session(session_id)
            if not session:
                session = await self.create_session(
                    model_id=self.settings.DEFAULT_MODEL,
                    system_instruction=None
                )
            
            # Create user message
            user_message = ChatMessage(
                id=str(uuid.uuid4()),
                content=message,
                role=MessageRole.USER,
                files=files or []
            )
            
            # Add to session history
            session.messages.append(user_message)
            
            # Assess complexity and set thinking budget
            complexity = await self._assess_complexity(message, thinking_mode)
            thinking_tokens = self._get_thinking_budget(complexity)
            
            # Check cache first
            cache_key = self._generate_cache_key(message, session.model_id, files)
            if self.cache_service:
                cached_response = await self.cache_service.get(cache_key)
                if cached_response:
                    self.usage_stats["cache_hits"] += 1
                    logger.info(f"Cache hit for message: {message[:50]}...")
                    return ChatResponse(**cached_response)
            
            # Prepare generation config
            gen_config = self._prepare_generation_config(session, thinking_tokens)
            
            # Process with Gemini
            response_content = await self._generate_response(
                session=session,
                user_message=user_message,
                generation_config=gen_config,
                use_search=use_search,
                stream=stream
            )
            
            # Create assistant message
            assistant_message = ChatMessage(
                id=str(uuid.uuid4()),
                content=response_content.get("content", ""),
                role=MessageRole.ASSISTANT,
                used_search=response_content.get("used_search", False),
                thinking_content=response_content.get("thinking", None),
                response_time=time.time() - start_time
            )
            
            # Add to session history
            session.messages.append(assistant_message)
            session.updated_at = datetime.now()
            
            # Update usage stats
            self.usage_stats["total_requests"] += 1
            self.usage_stats["thinking_budget_used"][complexity] = (
                self.usage_stats["thinking_budget_used"].get(complexity, 0) + 1
            )
            
            # Create response
            chat_response = ChatResponse(
                message=assistant_message,
                session_id=session_id,
                model_used=session.model_id,
                tokens_used=response_content.get("tokens_used"),
                cost_estimate=response_content.get("cost_estimate")
            )
            
            # Cache the response
            if self.cache_service:
                await self.cache_service.set(
                    cache_key, 
                    chat_response.dict(), 
                    ttl=self.settings.CACHE_TTL_MEDIUM
                )
            
            return chat_response
            
        except Exception as e:
            logger.error(f"Error processing chat message: {e}")
            
            # Create error response
            error_message = ChatMessage(
                id=str(uuid.uuid4()),
                content=f"I apologize, but I encountered an error: {str(e)}",
                role=MessageRole.ASSISTANT,
                has_error=True,
                response_time=time.time() - start_time
            )
            
            return ChatResponse(
                message=error_message,
                session_id=session_id,
                model_used="error"
            )
    
    async def process_message_stream(
        self,
        session_id: str,
        message: str,
        attachments: List[str] = None,
        use_thinking: bool = True,
        enable_search: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a message and stream the response in real-time."""
        try:
            session = await self.get_session(session_id)
            if not session:
                session = await self.create_session(
                    model_id=self.settings.DEFAULT_MODEL,
                    system_instruction=None
                )
            
            # Create user message
            user_message = ChatMessage(
                id=str(uuid.uuid4()),
                content=message,
                role=MessageRole.USER,
                files=attachments or []
            )
            
            # Add to session history
            session.messages.append(user_message)
            
            # Assess complexity and set thinking budget
            complexity = await self._assess_complexity(message, use_thinking)
            thinking_tokens = self._get_thinking_budget(complexity)
            
            # Stream the response
            response_content = ""
            thinking_content = ""
            
            # Simulate streaming for now - will be replaced with actual Gemini streaming
            for i, chunk in enumerate(f"This is a streaming response to: {message}".split()):
                if i == 0:
                    yield {
                        "type": "thinking",
                        "content": f"Processing '{message[:30]}...'",
                        "complete": False
                    }
                
                response_content += chunk + " "
                yield {
                    "type": "response", 
                    "content": chunk + " ",
                    "complete": False
                }
                
                # Simulate processing delay
                await asyncio.sleep(0.1)
            
            # Complete the streaming
            yield {
                "type": "response",
                "content": "",
                "complete": True
            }
            
            # Create assistant message
            assistant_message = ChatMessage(
                id=str(uuid.uuid4()),
                content=response_content.strip(),
                role=MessageRole.ASSISTANT,
                thinking_content=thinking_content if thinking_content else None,
                used_search=enable_search
            )
            
            # Add to session
            session.messages.append(assistant_message)
            session.updated_at = datetime.now()
            
            # Final completion message
            yield {
                "type": "complete",
                "session_id": session_id,
                "message_id": len(session.messages) - 1
            }
            
        except Exception as e:
            logger.error(f"Error in streaming response: {e}")
            yield {
                "type": "error",
                "content": f"Error generating response: {str(e)}"
            }
    
    async def _assess_complexity(self, message: str, thinking_mode: bool = False) -> str:
        """Assess message complexity for thinking budget allocation."""
        if thinking_mode:
            return ComplexityLevel.MAXIMUM
        
        # Simple heuristics for complexity assessment
        message_lower = message.lower()
        
        # Deep reasoning indicators
        if any(word in message_lower for word in [
            "analyze", "compare", "explain why", "reasoning", "logic", 
            "step by step", "complex", "detailed analysis"
        ]):
            return ComplexityLevel.DEEP
        
        # Moderate complexity indicators  
        if any(word in message_lower for word in [
            "how", "why", "what if", "explain", "describe", "calculate"
        ]):
            return ComplexityLevel.MODERATE
        
        # Light reasoning indicators
        if len(message) > 100 or "?" in message:
            return ComplexityLevel.LIGHT
        
        return ComplexityLevel.NONE
    
    def _get_thinking_budget(self, complexity: str) -> int:
        """Get thinking budget tokens for complexity level."""
        budget_map = {
            ComplexityLevel.NONE: self.thinking_budget.light,
            ComplexityLevel.LIGHT: self.thinking_budget.light,
            ComplexityLevel.MODERATE: self.thinking_budget.moderate,
            ComplexityLevel.DEEP: self.thinking_budget.deep,
            ComplexityLevel.MAXIMUM: self.thinking_budget.maximum
        }
        return budget_map.get(complexity, self.thinking_budget.light)
    
    def _prepare_generation_config(
        self, 
        session: ChatSession, 
        thinking_tokens: int
    ) -> types.GenerateContentConfig:
        """Prepare generation configuration with thinking budget."""
        config_dict = session.settings.get("generation_config", {})
        
        generation_config = {
            "temperature": config_dict.get("temperature", self.settings.DEFAULT_TEMPERATURE),
            "max_output_tokens": config_dict.get("max_output_tokens", self.settings.DEFAULT_MAX_TOKENS),
            "top_p": config_dict.get("top_p", 0.95),
        }
        
        # Add thinking budget if supported
        if thinking_tokens > 0:
            generation_config["thinking_budget"] = thinking_tokens
        
        return types.GenerateContentConfig(**generation_config)
    
    async def _generate_response(
        self,
        session: ChatSession,
        user_message: ChatMessage,
        generation_config: types.GenerateContentConfig,
        use_search: bool = True,
        stream: bool = True
    ) -> Dict[str, Any]:
        """Generate response using Gemini with enhanced error handling."""
        try:
            # Prepare conversation history
            history = []
            
            # Add system instruction
            if session.system_instruction:
                history.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(session.system_instruction)]
                ))
            
            # Add previous messages (excluding system)
            for msg in session.messages[:-1]:  # Exclude the current user message
                if msg.is_visible:
                    history.append(types.Content(
                        role="user" if msg.role == MessageRole.USER else "model",
                        parts=[types.Part.from_text(msg.content)]
                    ))
            
            # Prepare current message parts
            message_parts = [types.Part.from_text(user_message.content)]
            
            # Add file parts if any (TODO: implement file processing)
            # for file_id in user_message.files:
            #     file_part = await self._process_file(file_id)
            #     if file_part:
            #         message_parts.append(file_part)
            
            # Generate response
            response = await self.client.aio.models.generate_content(
                model=session.model_id,
                contents=history + [types.Content(
                    role="user",
                    parts=message_parts
                )],
                config=generation_config
            )
            
            # Extract response content
            content = ""
            thinking_content = None
            used_search = False
            
            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, 'text'):
                            content += part.text
                        elif hasattr(part, 'thinking'):
                            thinking_content = part.thinking
            
            # Check for search grounding usage
            if hasattr(response, 'usage_metadata'):
                used_search = getattr(response.usage_metadata, 'grounding_metadata', None) is not None
            
            return {
                "content": content,
                "thinking": thinking_content,
                "used_search": used_search,
                "tokens_used": getattr(response.usage_metadata, 'total_token_count', None) if hasattr(response, 'usage_metadata') else None,
                "cost_estimate": None  # TODO: implement cost calculation
            }
            
        except Exception as e:
            logger.error(f"Error generating Gemini response: {e}")
            raise
    
    def _generate_cache_key(self, message: str, model_id: str, files: List[str] = None) -> str:
        """Generate cache key for request."""
        import hashlib
        
        key_data = f"{message}:{model_id}:{':'.join(files or [])}"
        return f"chat:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get service usage statistics."""
        return self.usage_stats.copy()
    
    # RAG Integration Methods
    
    async def process_rag_message(
        self,
        session_id: str,
        rag_request: ChatWithRAGRequest,
        cache_service=None,
        vector_service=None
    ) -> ChatResponse:
        """Process a message with RAG-enhanced context."""
        try:
            # Get relevant context from vector database
            rag_context = None
            if rag_request.use_rag and vector_service:
                rag_context = await self._retrieve_rag_context(
                    query=rag_request.message,
                    limit=rag_request.rag_limit,
                    threshold=rag_request.rag_threshold,
                    filters=rag_request.knowledge_filters,
                    vector_service=vector_service
                )
            
            # Enhance message with context if available
            enhanced_message = rag_request.message
            if rag_context and rag_context.context_text:
                enhanced_message = self._format_rag_prompt(
                    original_message=rag_request.message,
                    context=rag_context.context_text,
                    sources=rag_context.source_documents
                )
            
            # Process with standard chat flow
            response = await self.process_message(
                session_id=session_id,
                message=enhanced_message,
                attachments=[],
                use_thinking=True,
                enable_search=False  # RAG replaces search
            )
            
            # Add RAG metadata to response
            if rag_context:
                response.rag_context = rag_context
                response.sources_used = rag_context.source_documents
            
            return response
            
        except Exception as e:
            logger.error(f"Error in RAG message processing: {e}")
            raise
    
    async def _retrieve_rag_context(
        self,
        query: str,
        limit: int = 3,
        threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None,
        vector_service=None
    ) -> Optional[RAGContext]:
        """Retrieve relevant context from vector database."""
        if not vector_service:
            return None
        
        try:
            # Search for relevant chunks
            chunks = await vector_service.search_similar(
                query=query,
                limit=limit,
                score_threshold=threshold,
                filters=filters
            )
            
            if not chunks:
                return None
            
            # Format context text
            context_parts = []
            source_documents = set()
            total_confidence = 0
            
            for chunk in chunks:
                context_parts.append(f"[Source: {chunk.document_title}]\n{chunk.content}")
                source_documents.add(chunk.document_title)
                total_confidence += chunk.similarity_score
            
            context_text = "\n\n".join(context_parts)
            average_confidence = total_confidence / len(chunks) if chunks else 0
            
            return RAGContext(
                query=query,
                relevant_chunks=chunks,
                context_text=context_text,
                source_documents=list(source_documents),
                confidence_score=average_confidence
            )
            
        except Exception as e:
            logger.error(f"Error retrieving RAG context: {e}")
            return None
    
    def _format_rag_prompt(
        self,
        original_message: str,
        context: str,
        sources: List[str]
    ) -> str:
        """Format user message with RAG context."""
        prompt = f"""Based on the following context from our knowledge base, please answer the user's question:

CONTEXT:
{context}

SOURCES: {', '.join(sources)}

USER QUESTION:
{original_message}

Please answer based primarily on the provided context. If the context doesn't contain sufficient information to fully answer the question, mention that explicitly and provide what information is available. Always cite the sources when referencing specific information from the context."""
        
        return prompt
    
    async def process_message_with_cache(
        self,
        session_id: str,
        message: str,
        attachments: List[str] = None,
        cache_service=None,
        **kwargs
    ) -> ChatResponse:
        """Process message with optional caching."""
        # Generate cache key
        cache_key = self._generate_cache_key(message, self.settings.DEFAULT_MODEL, attachments)
        
        # Try to get cached response
        cached_response = None
        if cache_service:
            cached_response = await cache_service.get_cached_response(cache_key)
        
        if cached_response:
            logger.info(f"Returning cached response for message: {message[:50]}...")
            return ChatResponse(**cached_response)
        
        # Generate new response
        response = await self.process_message(
            session_id=session_id,
            message=message,
            attachments=attachments,
            **kwargs
        )
        
        # Cache the response
        if cache_service and response:
            await cache_service.cache_response(
                prompt_hash=cache_key,
                response_data=response.dict()
            )
        
        return response