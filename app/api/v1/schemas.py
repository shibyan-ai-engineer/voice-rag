"""
Pydantic models for request and response validation.
"""
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class TextQueryRequest(BaseModel):
    """Request model for text-based queries."""
    query_text: str = Field(..., description="The text query to process")
    
    
class WebSocketAction(BaseModel):
    """Request model for WebSocket actions."""
    action: Literal["pause_listening", "resume_listening"] = Field(
        ..., description="The action to perform"
    )
    
    
class WebSocketMessage(BaseModel):
    """Response model for WebSocket messages."""
    type: Literal["wake_word_detected", "log", "error"] = Field(
        ..., description="The type of message"
    )
    message: str = Field(..., description="The message content")


class TextQueryResponse(BaseModel):
    """Response model for text-based queries."""
    response_text: str = Field(..., description="The generated response text")
    context_used: List[str] = Field([], description="Context chunks used for generating the response")


class ChatVoiceResponse(BaseModel):
    """Response model for voice-based chat."""
    user_query_text: str = Field(..., description="The transcribed user query")
    response_text: str = Field(..., description="The generated response text")
    response_audio_url: str = Field(..., description="URL to the audio response file")


class UploadPdfResponse(BaseModel):
    """Response model for PDF uploads."""
    message: str = Field(..., description="Status message")
    filename: str = Field(..., description="Name of the processed PDF file")


class StatusResponse(BaseModel):
    """Response model for API status check."""
    status: str = Field(..., description="API status")
    models_loaded: Dict[str, bool] = Field(..., description="Status of loaded models")
    indexed_document_name: Optional[str] = Field(None, description="Name of the currently indexed document")


class ErrorResponse(BaseModel):
    """Response model for errors."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")