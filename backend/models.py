"""
Consolidated Pydantic Models for SmartDocs AI Backend.

This module defines all request/response models and validation schemas
for the SmartDocs AI application in a single location.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, ConfigDict


# ---- Enums ----

class HealthStatus(str, Enum):
    """Health status enumeration."""
    OK = "ok"
    DEGRADED = "degraded"
    DOWN = "down"


class DocumentStatus(str, Enum):
    """Document processing status enumeration."""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


# ---- Base Models ----

class TimestampMixin(BaseModel):
    """Mixin for models that include timestamps."""
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp when the resource was created"
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp when the resource was last updated"
    )


# ---- Request Models ----

class AskRequest(BaseModel):
    """Request model for asking questions about a document."""
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid"
    )
    
    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Natural language question to ask about the document",
        examples=[
            "What is the main topic of this document?",
            "Summarize the key findings in bullet points"
        ]
    )
    
    document_id: str = Field(
        ...,
        min_length=32,
        max_length=32,
        pattern=r"^[a-f0-9]{32}$",
        description="Document ID of a previously uploaded PDF (32-character hex string)",
        examples=["a1b2c3d4e5f6789012345678901234ab"]
    )
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate query is not just whitespace."""
        if not v.strip():
            raise ValueError("Query cannot be empty or only whitespace")
        return v.strip()


class RenameDocumentRequest(BaseModel):
    """Request model for renaming a document."""
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid"
    )
    
    document_id: str = Field(
        ...,
        min_length=32,
        max_length=32,
        pattern=r"^[a-f0-9]{32}$",
        description="Document ID to rename (32-character hex string)"
    )
    
    new_display_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="New display name for the document"
    )
    
    @field_validator('new_display_name')
    @classmethod
    def validate_display_name(cls, v: str) -> str:
        """Validate display name is not just whitespace."""
        if not v.strip():
            raise ValueError("Display name cannot be empty or only whitespace")
        return v.strip()


# ---- Response Models ----

class AskResponse(BaseModel):
    """Response model for question answering."""
    
    model_config = ConfigDict(validate_assignment=True)
    
    answer: str = Field(
        ...,
        description="AI-generated answer with enhanced markdown formatting"
    )
    
    document_id: Optional[str] = Field(
        default=None,
        description="Document ID that was queried"
    )
    
    processing_time_ms: Optional[int] = Field(
        default=None,
        ge=0,
        description="Time taken to process the query in milliseconds"
    )
    
    source_chunks_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="Number of document chunks retrieved for context"
    )


class UploadResponse(BaseModel):
    """Response model for document upload."""
    
    model_config = ConfigDict(validate_assignment=True)
    
    document_id: str = Field(
        ...,
        description="Unique identifier for the uploaded document"
    )
    
    chunks: int = Field(
        ...,
        ge=1,
        description="Number of text chunks created from the document"
    )
    
    bytes: int = Field(
        ...,
        ge=1,
        description="Size of extracted text in bytes"
    )
    
    filename: Optional[str] = Field(
        default=None,
        description="Original filename of the uploaded document"
    )
    
    processing_time_ms: Optional[int] = Field(
        default=None,
        ge=0,
        description="Time taken to process the document in milliseconds"
    )
    
    display_name: str = Field(
        ...,
        description="Cleaned filename for display"
    )


class RenameDocumentResponse(BaseModel):
    """Response model for document renaming."""
    
    model_config = ConfigDict(validate_assignment=True)
    
    document_id: str = Field(
        ...,
        description="Document ID that was renamed"
    )
    
    old_display_name: str = Field(
        ...,
        description="Previous display name"
    )
    
    new_display_name: str = Field(
        ...,
        description="Updated display name"
    )
    
    success: bool = Field(
        ...,
        description="Whether the rename operation succeeded"
    )


class HealthResponse(BaseModel):
    """Response model for health check."""
    
    model_config = ConfigDict(validate_assignment=True)
    
    status: HealthStatus = Field(
        ...,
        description="Overall system health status"
    )
    
    has_documents: bool = Field(
        ...,
        description="Whether any documents are currently stored"
    )
    
    last_document_id: Optional[str] = Field(
        default=None,
        description="ID of the most recently uploaded document"
    )
    
    document_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="Total number of documents stored"
    )
    
    uptime_seconds: Optional[int] = Field(
        default=None,
        ge=0,
        description="Server uptime in seconds"
    )
    
    version: Optional[str] = Field(
        default=None,
        description="API version"
    )


class ErrorResponse(BaseModel):
    """Standardized error response model."""
    
    model_config = ConfigDict(validate_assignment=True)
    
    error: bool = Field(
        default=True,
        description="Indicates this is an error response"
    )
    
    status_code: int = Field(
        ...,
        ge=400,
        le=599,
        description="HTTP status code"
    )
    
    message: str = Field(
        ...,
        description="Human-readable error message"
    )
    
    error_code: Optional[str] = Field(
        default=None,
        description="Machine-readable error code"
    )
    
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details and context"
    )
    
    request_id: Optional[str] = Field(
        default=None,
        description="Unique request identifier for tracking"
    )


# ---- Document Models ----

class DocumentInfo(TimestampMixin, BaseModel):
    """Document metadata information."""
    
    model_config = ConfigDict(validate_assignment=True)
    
    document_id: str = Field(
        ...,
        description="Unique document identifier"
    )
    
    filename: Optional[str] = Field(
        default=None,
        description="Original filename"
    )
    
    file_size_bytes: Optional[int] = Field(
        default=None,
        ge=0,
        description="Original file size in bytes"
    )
    
    text_size_bytes: int = Field(
        ...,
        ge=0,
        description="Extracted text size in bytes"
    )
    
    chunk_count: int = Field(
        ...,
        ge=0,
        description="Number of text chunks"
    )
    
    status: DocumentStatus = Field(
        ...,
        description="Current document status"
    )
    
    collection_name: str = Field(
        ...,
        description="Vector store collection name"
    )
    
    processing_time_ms: Optional[int] = Field(
        default=None,
        ge=0,
        description="Total processing time in milliseconds"
    )
    
    extracted_title: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Title extracted from document content during processing"
    )
    
    display_name: Optional[str] = Field(
        default=None,
        max_length=200,
        description="User-customizable display name for the document"
    )
    
    def get_display_name(self) -> str:
        """Get the best available display name using fallback hierarchy."""
        if self.display_name:
            return self.display_name
        if self.extracted_title:
            return self.extracted_title
        if self.filename:
            return self._clean_filename_for_display(self.filename)
        return f"Document {self.document_id[:8]}..."
    
    def _clean_filename_for_display(self, filename: str) -> str:
        """Clean filename for better display."""
        if not filename:
            return "Untitled Document"
        
        # Remove file extension
        base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
        
        # Replace underscores and dashes with spaces
        display_name = base_name.replace('_', ' ').replace('-', ' ')
        
        # Remove excessive whitespace
        display_name = ' '.join(display_name.split())
        
        # Capitalize if it looks like it needs it
        if display_name.islower():
            display_name = display_name.title()
        
        # Truncate if too long
        if len(display_name) > 100:
            display_name = display_name[:97] + "..."
        
        return display_name or "Untitled Document"


class DocumentListResponse(BaseModel):
    """Response model for listing documents."""
    
    model_config = ConfigDict(validate_assignment=True)
    
    documents: List[DocumentInfo] = Field(
        ...,
        description="List of document metadata"
    )
    
    total_count: int = Field(
        ...,
        ge=0,
        description="Total number of documents"
    )
    
    page: Optional[int] = Field(
        default=None,
        ge=1,
        description="Current page number (if paginated)"
    )
    
    page_size: Optional[int] = Field(
        default=None,
        ge=1,
        description="Number of documents per page"
    )


# ---- Validation Models ----

class FileValidationInfo(BaseModel):
    """File validation information."""
    
    model_config = ConfigDict(validate_assignment=True)
    
    filename: str = Field(
        ...,
        description="Original filename"
    )
    
    content_type: Optional[str] = Field(
        default=None,
        description="MIME content type"
    )
    
    file_size_bytes: int = Field(
        ...,
        ge=0,
        description="File size in bytes"
    )
    
    is_valid: bool = Field(
        ...,
        description="Whether the file passes validation"
    )
    
    validation_errors: List[str] = Field(
        default_factory=list,
        description="List of validation error messages"
    )


# ---- System Models ----

class SystemMetrics(BaseModel):
    """System metrics and resource usage."""
    
    model_config = ConfigDict(validate_assignment=True)
    
    total_documents: int = Field(
        ...,
        ge=0,
        description="Total number of documents processed"
    )
    
    total_queries: int = Field(
        ...,
        ge=0,
        description="Total number of queries processed"
    )
    
    average_query_time_ms: Optional[float] = Field(
        default=None,
        ge=0,
        description="Average query processing time in milliseconds"
    )
    
    storage_used_bytes: Optional[int] = Field(
        default=None,
        ge=0,
        description="Total storage used in bytes"
    )
    
    last_query_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp of the last query"
    )


# Export all models for easy importing
__all__ = [
    # Enums
    "HealthStatus",
    "DocumentStatus",
    
    # Request models
    "AskRequest",
    "RenameDocumentRequest",
    
    # Response models
    "AskResponse",
    "UploadResponse", 
    "RenameDocumentResponse",
    "HealthResponse",
    "ErrorResponse",
    "DocumentListResponse",
    
    # Document models
    "DocumentInfo",
    "FileValidationInfo",
    "SystemMetrics",
    
    # Base models
    "TimestampMixin"
]