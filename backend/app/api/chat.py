"""
Chat API endpoints for Gemini conversation handling.
Routes for managing chat sessions and processing messages.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
import json
import io

from app.models.chat import (
    ChatSession, ChatMessage, SessionCreateRequest, ChatRequest,
    ChatResponse, ModelSelection, UsageStats
)
from app.services.gemini_service import GeminiService
from app.core.dependencies import get_gemini_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sessions", response_model=ChatSession)
async def create_session(
    session_data: SessionCreateRequest,
    gemini_service: GeminiService = Depends(get_gemini_service)
) -> ChatSession:
    """Create a new chat session with optional model configuration."""
    session = await gemini_service.create_session(
        title=session_data.title,
        system_prompt=session_data.system_prompt,
        model_name=session_data.model_name,
        temperature=session_data.temperature,
        max_tokens=session_data.max_tokens
    )
    return session


@router.get("/sessions", response_model=List[ChatSession])
async def list_sessions(
    limit: int = 50,
    offset: int = 0,
    gemini_service: GeminiService = Depends(get_gemini_service)
) -> List[ChatSession]:
    """List all chat sessions with pagination."""
    sessions = await gemini_service.list_sessions(limit=limit, offset=offset)
    return sessions


@router.get("/sessions/{session_id}", response_model=ChatSession)
async def get_session(
    session_id: str,
    gemini_service: GeminiService = Depends(get_gemini_service)
) -> ChatSession:
    """Get a specific chat session by ID."""
    session = await gemini_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    gemini_service: GeminiService = Depends(get_gemini_service)
):
    """Delete a chat session and all its messages."""
    success = await gemini_service.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted successfully"}


@router.post("/sessions/{session_id}/messages", response_model=ChatResponse)
async def send_message(
    session_id: str,
    message_data: ChatRequest,
    gemini_service: GeminiService = Depends(get_gemini_service)
) -> ChatResponse:
    """Send a message to a chat session and get AI response."""
    try:
        response = await gemini_service.process_message(
            session_id=session_id,
            message=message_data.message,
            attachments=message_data.files or [],
            use_thinking=message_data.thinking_mode,
            enable_search=message_data.use_search
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")


@router.post("/sessions/{session_id}/messages/stream")
async def send_message_stream(
    session_id: str,
    message_data: ChatRequest,
    gemini_service: GeminiService = Depends(get_gemini_service)
):
    """Send a message and stream the AI response in real-time."""
    try:
        async def generate_stream():
            async for chunk in gemini_service.process_message_stream(
                session_id=session_id,
                message=message_data.message,
                attachments=message_data.files or [],
                use_thinking=message_data.thinking_mode,
                enable_search=message_data.use_search
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessage])
async def get_messages(
    session_id: str,
    limit: int = 100,
    offset: int = 0,
    gemini_service: GeminiService = Depends(get_gemini_service)
) -> List[ChatMessage]:
    """Get messages from a chat session with pagination."""
    messages = await gemini_service.get_messages(
        session_id=session_id,
        limit=limit,
        offset=offset
    )
    if messages is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return messages


@router.post("/sessions/{session_id}/files")
async def upload_file(
    session_id: str,
    file: UploadFile = File(...),
    gemini_service: GeminiService = Depends(get_gemini_service)
):
    """Upload a file to be processed in the chat session."""
    try:
        # Read file content
        content = await file.read()
        
        # Process the file through Gemini service
        result = await gemini_service.process_file(
            session_id=session_id,
            filename=file.filename,
            content=content,
            content_type=file.content_type
        )
        
        return {
            "message": "File uploaded and processed successfully",
            "file_info": {
                "filename": file.filename,
                "size": len(content),
                "content_type": file.content_type
            },
            "processing_result": result
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@router.get("/sessions/{session_id}/export")
async def export_session(
    session_id: str,
    format: str = "json",  # json, html, markdown
    gemini_service: GeminiService = Depends(get_gemini_service)
):
    """Export a chat session in various formats."""
    try:
        exported_data = await gemini_service.export_session(session_id, format)
        if not exported_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Determine content type and filename based on format
        if format == "html":
            media_type = "text/html"
            filename = f"chat_session_{session_id}.html"
        elif format == "markdown":
            media_type = "text/markdown"
            filename = f"chat_session_{session_id}.md"
        else:  # json
            media_type = "application/json"
            filename = f"chat_session_{session_id}.json"
        
        # Create file-like object for download
        file_content = io.BytesIO(exported_data.encode() if isinstance(exported_data, str) else exported_data)
        
        return StreamingResponse(
            io.BytesIO(exported_data.encode()),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting session: {str(e)}")


@router.get("/models", response_model=List[ModelSelection])
async def list_available_models(
    gemini_service: GeminiService = Depends(get_gemini_service)
) -> List[ModelSelection]:
    """Get list of available Gemini models with their capabilities."""
    models = await gemini_service.get_available_models()
    return models


@router.get("/sessions/{session_id}/stats", response_model=UsageStats)
async def get_session_stats(
    session_id: str,
    gemini_service: GeminiService = Depends(get_gemini_service)
) -> UsageStats:
    """Get usage statistics for a specific session."""
    stats = await gemini_service.get_session_stats(session_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Session not found")
    return stats


@router.get("/stats", response_model=UsageStats)
async def get_global_stats(
    gemini_service: GeminiService = Depends(get_gemini_service)
) -> UsageStats:
    """Get global usage statistics across all sessions."""
    stats = await gemini_service.get_global_stats()
    return stats


@router.post("/sessions/{session_id}/clear")
async def clear_session_history(
    session_id: str,
    gemini_service: GeminiService = Depends(get_gemini_service)
):
    """Clear all messages from a session while keeping the session itself."""
    success = await gemini_service.clear_session_history(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session history cleared successfully"}


@router.post("/sessions/{session_id}/regenerate", response_model=ChatResponse)
async def regenerate_last_response(
    session_id: str,
    gemini_service: GeminiService = Depends(get_gemini_service)
) -> ChatResponse:
    """Regenerate the last AI response in the session."""
    try:
        response = await gemini_service.regenerate_last_response(session_id)
        return response
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error regenerating response: {str(e)}")