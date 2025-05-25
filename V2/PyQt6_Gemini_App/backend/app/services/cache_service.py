"""
Redis caching service for LostMindAI chat sessions and responses.
Provides memory-efficient caching with TTL management.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import redis.asyncio as redis
from app.core.config import Settings
from app.models.chat import ChatMessage, ChatSession

logger = logging.getLogger(__name__)

class CacheService:
    """Redis-based caching service for chat data and responses."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.redis_client: Optional[redis.Redis] = None
        self.session_ttl = 24 * 60 * 60  # 24 hours for sessions
        self.message_ttl = 7 * 24 * 60 * 60  # 7 days for messages
        self.response_ttl = 60 * 60  # 1 hour for cached responses
        
    async def connect(self) -> bool:
        """Connect to Redis with proper error handling."""
        try:
            self.redis_client = redis.Redis(
                host=self.settings.redis_host,
                port=self.settings.redis_port,
                db=self.settings.redis_db,
                password=self.settings.redis_password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Successfully connected to Redis")
            return True
            
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Continuing without cache.")
            self.redis_client = None
            return False
    
    async def disconnect(self):
        """Clean disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
            
    def _get_session_key(self, session_id: str) -> str:
        """Generate Redis key for session data."""
        return f"session:{session_id}"
    
    def _get_messages_key(self, session_id: str) -> str:
        """Generate Redis key for session messages."""
        return f"messages:{session_id}"
    
    def _get_response_key(self, prompt_hash: str) -> str:
        """Generate Redis key for cached responses."""
        return f"response:{prompt_hash}"
    
    def _get_user_sessions_key(self, user_id: str) -> str:
        """Generate Redis key for user's session list."""
        return f"user_sessions:{user_id}"
    
    async def cache_session(self, session: ChatSession) -> bool:
        """Cache session metadata."""
        if not self.redis_client:
            return False
            
        try:
            session_key = self._get_session_key(session.id)
            session_data = {
                "id": session.id,
                "title": session.title,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "message_count": session.message_count,
                "model_name": session.model_name,
                "user_id": getattr(session, 'user_id', 'default')
            }
            
            # Cache session data
            await self.redis_client.setex(
                session_key, 
                self.session_ttl, 
                json.dumps(session_data)
            )
            
            # Add to user's session list
            user_sessions_key = self._get_user_sessions_key(
                getattr(session, 'user_id', 'default')
            )
            await self.redis_client.sadd(user_sessions_key, session.id)
            await self.redis_client.expire(user_sessions_key, self.session_ttl)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache session {session.id}: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached session data."""
        if not self.redis_client:
            return None
            
        try:
            session_key = self._get_session_key(session_id)
            session_data = await self.redis_client.get(session_key)
            
            if session_data:
                return json.loads(session_data)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    async def cache_message(self, session_id: str, message: ChatMessage) -> bool:
        """Cache a message in a session."""
        if not self.redis_client:
            return False
            
        try:
            messages_key = self._get_messages_key(session_id)
            message_data = {
                "id": message.id,
                "content": message.content,
                "role": message.role,
                "timestamp": message.timestamp.isoformat(),
                "attachments": message.attachments or [],
                "thinking_content": getattr(message, 'thinking_content', None),
                "metadata": getattr(message, 'metadata', {})
            }
            
            # Add message to list
            await self.redis_client.lpush(
                messages_key, 
                json.dumps(message_data)
            )
            
            # Set expiry and limit list size
            await self.redis_client.expire(messages_key, self.message_ttl)
            await self.redis_client.ltrim(messages_key, 0, 999)  # Keep last 1000 messages
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache message for session {session_id}: {e}")
            return False
    
    async def get_messages(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve cached messages for a session."""
        if not self.redis_client:
            return []
            
        try:
            messages_key = self._get_messages_key(session_id)
            messages_data = await self.redis_client.lrange(
                messages_key, 0, limit - 1
            )
            
            messages = []
            for msg_data in messages_data:
                try:
                    message = json.loads(msg_data)
                    messages.append(message)
                except json.JSONDecodeError:
                    continue
                    
            # Reverse to get chronological order
            return list(reversed(messages))
            
        except Exception as e:
            logger.error(f"Failed to get messages for session {session_id}: {e}")
            return []
    
    async def cache_response(self, prompt_hash: str, response_data: Dict[str, Any]) -> bool:
        """Cache AI response for potential reuse."""
        if not self.redis_client:
            return False
            
        try:
            response_key = self._get_response_key(prompt_hash)
            await self.redis_client.setex(
                response_key,
                self.response_ttl,
                json.dumps(response_data)
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache response {prompt_hash}: {e}")
            return False
    
    async def get_cached_response(self, prompt_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached AI response if available."""
        if not self.redis_client:
            return None
            
        try:
            response_key = self._get_response_key(prompt_hash)
            response_data = await self.redis_client.get(response_key)
            
            if response_data:
                return json.loads(response_data)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get cached response {prompt_hash}: {e}")
            return None
    
    async def get_user_sessions(self, user_id: str = "default") -> List[str]:
        """Get list of session IDs for a user."""
        if not self.redis_client:
            return []
            
        try:
            user_sessions_key = self._get_user_sessions_key(user_id)
            session_ids = await self.redis_client.smembers(user_sessions_key)
            return list(session_ids)
            
        except Exception as e:
            logger.error(f"Failed to get user sessions for {user_id}: {e}")
            return []
    
    async def delete_session(self, session_id: str, user_id: str = "default") -> bool:
        """Delete a session and its messages from cache."""
        if not self.redis_client:
            return False
            
        try:
            # Delete session data
            session_key = self._get_session_key(session_id)
            await self.redis_client.delete(session_key)
            
            # Delete messages
            messages_key = self._get_messages_key(session_id)
            await self.redis_client.delete(messages_key)
            
            # Remove from user's session list
            user_sessions_key = self._get_user_sessions_key(user_id)
            await self.redis_client.srem(user_sessions_key, session_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    async def clear_expired_sessions(self) -> int:
        """Clean up expired sessions and return count of deleted items."""
        if not self.redis_client:
            return 0
            
        try:
            # Get all session keys
            session_keys = await self.redis_client.keys("session:*")
            deleted_count = 0
            
            for key in session_keys:
                ttl = await self.redis_client.ttl(key)
                if ttl == -1:  # No expiry set, probably old data
                    await self.redis_client.expire(key, self.session_ttl)
                elif ttl == -2:  # Key expired/doesn't exist
                    deleted_count += 1
                    
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to clear expired sessions: {e}")
            return 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics and health info."""
        if not self.redis_client:
            return {"status": "disconnected", "error": "Redis not available"}
            
        try:
            info = await self.redis_client.info()
            
            # Count keys by pattern
            session_count = len(await self.redis_client.keys("session:*"))
            message_count = len(await self.redis_client.keys("messages:*"))
            response_count = len(await self.redis_client.keys("response:*"))
            
            return {
                "status": "connected",
                "redis_version": info.get("redis_version", "unknown"),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "total_sessions": session_count,
                "total_message_lists": message_count,
                "cached_responses": response_count,
                "uptime_seconds": info.get("uptime_in_seconds", 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"status": "error", "error": str(e)}
