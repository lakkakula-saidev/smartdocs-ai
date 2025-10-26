"""
Pydantic schemas for SmartDocs AI Backend API.

This module defines request/response models and validation schemas
for all API endpoints in the SmartDocs AI application.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
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


class ProcessingStage(str, Enum):
    """Document processing stage enumeration."""
    TEXT_EXTRACTION = "text_extraction"
    TEXT_CHUNKING = "text_chunking"
    EMBEDDING_CREATION = "embedding_creation"
    VECTOR_STORAGE = "vector_storage"
    COMPLETED = "completed"
    FAILED = "failed"


# ---- Base Models ----

class TimestampMixin(BaseModel):
    """Mixin for models that include timestamps."""
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp when the resource was created",
        examples=["2024-01-15T10:30:00.000Z"]
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp when the resource was last updated",
        examples=["2024-01-15T10:35:00.000Z"]
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
            "Summarize the key findings in bullet points",
            "What are the technical specifications mentioned?"
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
        description="Document ID to rename (32-character hex string)",
        examples=["a1b2c3d4e5f6789012345678901234ab"]
    )
    
    new_display_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="New display name for the document",
        examples=["My Research Notes", "Updated Contract", "Important Presentation"]
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
    
    model_config = ConfigDict(
        validate_assignment=True
    )
    
    answer: str = Field(
        ...,
        description="AI-generated answer with enhanced markdown formatting",
        examples=[
            "The document discusses **machine learning algorithms** with focus on:\n\n1. **Neural Networks**: Deep learning approaches\n2. **Decision Trees**: Classification methods\n3. **Clustering**: Unsupervised learning techniques"
        ]
    )
    
    document_id: Optional[str] = Field(
        default=None,
        description="Document ID that was queried",
        examples=["a1b2c3d4e5f6789012345678901234ab"]
    )
    
    processing_time_ms: Optional[int] = Field(
        default=None,
        ge=0,
        description="Time taken to process the query in milliseconds",
        examples=[1250]
    )
    
    source_chunks_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="Number of document chunks retrieved for context",
        examples=[4]
    )


class UploadResponse(BaseModel):
    """Response model for document upload."""
    
    model_config = ConfigDict(
        validate_assignment=True
    )
    
    document_id: str = Field(
        ...,
        description="Unique identifier for the uploaded document",
        examples=["a1b2c3d4e5f6789012345678901234ab"]
    )
    
    chunks: int = Field(
        ...,
        ge=1,
        description="Number of text chunks created from the document",
        examples=[42]
    )
    
    bytes: int = Field(
        ...,
        ge=1,
        description="Size of extracted text in bytes",
        examples=[15420]
    )
    
    filename: Optional[str] = Field(
        default=None,
        description="Original filename of the uploaded document",
        examples=["research_paper.pdf"]
    )
    
    processing_time_ms: Optional[int] = Field(
        default=None,
        ge=0,
        description="Time taken to process the document in milliseconds",
        examples=[3200]
    )
    
    display_name: str = Field(
        ...,
        description="Cleaned filename for display (simplified approach)",
        examples=["Machine Learning Research Paper", "Quarterly Report"]
    )


class RenameDocumentResponse(BaseModel):
    """Response model for document renaming."""
    
    model_config = ConfigDict(
        validate_assignment=True
    )
    
    document_id: str = Field(
        ...,
        description="Document ID that was renamed",
        examples=["a1b2c3d4e5f6789012345678901234ab"]
    )
    
    old_display_name: str = Field(
        ...,
        description="Previous display name",
        examples=["Machine Learning Research Paper"]
    )
    
    new_display_name: str = Field(
        ...,
        description="Updated display name",
        examples=["My ML Research Notes"]
    )
    
    success: bool = Field(
        ...,
        description="Whether the rename operation succeeded",
        examples=[True]
    )


class HealthResponse(BaseModel):
    """Response model for health check."""
    
    model_config = ConfigDict(
        validate_assignment=True
    )
    
    status: HealthStatus = Field(
        ...,
        description="Overall system health status",
        examples=[HealthStatus.OK]
    )
    
    has_documents: bool = Field(
        ...,
        description="Whether any documents are currently stored",
        examples=[True]
    )
    
    last_document_id: Optional[str] = Field(
        default=None,
        description="ID of the most recently uploaded document",
        examples=["a1b2c3d4e5f6789012345678901234ab"]
    )
    
    document_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="Total number of documents stored",
        examples=[5]
    )
    
    uptime_seconds: Optional[int] = Field(
        default=None,
        ge=0,
        description="Server uptime in seconds",
        examples=[86400]
    )
    
    version: Optional[str] = Field(
        default=None,
        description="API version",
        examples=["0.1.0"]
    )


class ErrorResponse(BaseModel):
    """Standardized error response model."""
    
    model_config = ConfigDict(
        validate_assignment=True
    )
    
    error: bool = Field(
        default=True,
        description="Indicates this is an error response",
        examples=[True]
    )
    
    status_code: int = Field(
        ...,
        ge=400,
        le=599,
        description="HTTP status code",
        examples=[400, 404, 500]
    )
    
    message: str = Field(
        ...,
        description="Human-readable error message",
        examples=[
            "Document with ID 'invalid123' not found",
            "Query must not be empty",
            "Only PDF files are supported"
        ]
    )
    
    error_code: Optional[str] = Field(
        default=None,
        description="Machine-readable error code",
        examples=["DOCUMENT_NOT_FOUND", "VALIDATION_ERROR", "UNSUPPORTED_FILE_TYPE"]
    )
    
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details and context",
        examples=[{
            "document_id": "invalid123",
            "allowed_types": [".pdf"],
            "validation_errors": [{"field": "query", "message": "cannot be empty"}]
        }]
    )
    
    request_id: Optional[str] = Field(
        default=None,
        description="Unique request identifier for tracking",
        examples=["req_a1b2c3d4e5f6789012345678"]
    )


# ---- Metadata Models ----

class ProcessingStatus(TimestampMixin, BaseModel):
    """Document processing status information."""
    
    model_config = ConfigDict(
        validate_assignment=True
    )
    
    document_id: str = Field(
        ...,
        description="Document identifier",
        examples=["a1b2c3d4e5f6789012345678901234ab"]
    )
    
    status: DocumentStatus = Field(
        ...,
        description="Current document status",
        examples=[DocumentStatus.READY]
    )
    
    stage: ProcessingStage = Field(
        ...,
        description="Current or last processing stage",
        examples=[ProcessingStage.COMPLETED]
    )
    
    progress_percent: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
        description="Processing progress percentage",
        examples=[100]
    )
    
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if processing failed",
        examples=["Failed to extract text from PDF: corrupted file"]
    )


class DocumentInfo(TimestampMixin, BaseModel):
    """Document metadata information."""
    
    model_config = ConfigDict(
        validate_assignment=True
    )
    
    document_id: str = Field(
        ...,
        description="Unique document identifier",
        examples=["a1b2c3d4e5f6789012345678901234ab"]
    )
    
    filename: Optional[str] = Field(
        default=None,
        description="Original filename",
        examples=["research_paper.pdf"]
    )
    
    file_size_bytes: Optional[int] = Field(
        default=None,
        ge=0,
        description="Original file size in bytes",
        examples=[2048576]
    )
    
    text_size_bytes: int = Field(
        ...,
        ge=0,
        description="Extracted text size in bytes",
        examples=[15420]
    )
    
    chunk_count: int = Field(
        ...,
        ge=0,
        description="Number of text chunks",
        examples=[42]
    )
    
    status: DocumentStatus = Field(
        ...,
        description="Current document status",
        examples=[DocumentStatus.READY]
    )
    
    collection_name: str = Field(
        ...,
        description="Vector store collection name",
        examples=["doc_a1b2c3d4e5f6789012345678901234ab"]
    )
    
    processing_time_ms: Optional[int] = Field(
        default=None,
        ge=0,
        description="Total processing time in milliseconds",
        examples=[3200]
    )
    
    extracted_title: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Title extracted from document content during processing",
        examples=["Machine Learning Research Paper", "Q3 Financial Report 2024"]
    )
    
    display_name: Optional[str] = Field(
        default=None,
        max_length=200,
        description="User-customizable display name for the document",
        examples=["My Research Notes", "Important Contract"]
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
        
        # Remove common suffixes like (1), (2), etc.
        import re
        display_name = re.sub(r'\s*\(\d+\)\s*$', '', display_name)
        
        # Remove excessive whitespace
        display_name = ' '.join(display_name.split())
        
        # Capitalize if it looks like it needs it
        if display_name.islower():
            display_name = display_name.title()
        
        # Truncate if too long
        if len(display_name) > 100:
            display_name = display_name[:97] + "..."
        
        return display_name or "Untitled Document"


class VectorStoreInfo(BaseModel):
    """Vector store status and metadata."""
    
    model_config = ConfigDict(
        validate_assignment=True
    )
    
    document_id: str = Field(
        ...,
        description="Associated document identifier",
        examples=["a1b2c3d4e5f6789012345678901234ab"]
    )
    
    collection_name: str = Field(
        ...,
        description="ChromaDB collection name",
        examples=["doc_a1b2c3d4e5f6789012345678901234ab"]
    )
    
    persist_directory: str = Field(
        ...,
        description="Filesystem path where collection is persisted",
        examples=["backend/vectorstores/a1b2c3d4e5f6789012345678901234ab"]
    )
    
    embedding_count: int = Field(
        ...,
        ge=0,
        description="Number of embeddings stored",
        examples=[42]
    )
    
    embedding_model: Optional[str] = Field(
        default="text-embedding-ada-002",
        description="OpenAI embedding model used",
        examples=["text-embedding-ada-002", "text-embedding-3-small"]
    )
    
    chunk_size: Optional[int] = Field(
        default=1000,
        ge=1,
        description="Text chunk size used for processing",
        examples=[1000]
    )
    
    chunk_overlap: Optional[int] = Field(
        default=150,
        ge=0,
        description="Text chunk overlap size",
        examples=[150]
    )
    
    is_accessible: bool = Field(
        ...,
        description="Whether the vector store is currently accessible",
        examples=[True]
    )


# ---- Extended Response Models ----

class DocumentListResponse(BaseModel):
    """Response model for listing documents."""
    
    model_config = ConfigDict(
        validate_assignment=True
    )
    
    documents: List[DocumentInfo] = Field(
        ...,
        description="List of document metadata",
        examples=[[]]
    )
    
    total_count: int = Field(
        ...,
        ge=0,
        description="Total number of documents",
        examples=[5]
    )
    
    page: Optional[int] = Field(
        default=None,
        ge=1,
        description="Current page number (if paginated)",
        examples=[1]
    )
    
    page_size: Optional[int] = Field(
        default=None,
        ge=1,
        description="Number of documents per page",
        examples=[10]
    )


class VectorStoreListResponse(BaseModel):
    """Response model for listing vector stores."""
    
    model_config = ConfigDict(
        validate_assignment=True
    )
    
    vector_stores: List[VectorStoreInfo] = Field(
        ...,
        description="List of vector store information",
        examples=[[]]
    )
    
    total_count: int = Field(
        ...,
        ge=0,
        description="Total number of vector stores",
        examples=[5]
    )


# ---- Validation Models ----

class FileValidationInfo(BaseModel):
    """File validation information."""
    
    model_config = ConfigDict(
        validate_assignment=True
    )
    
    filename: str = Field(
        ...,
        description="Original filename",
        examples=["document.pdf"]
    )
    
    content_type: Optional[str] = Field(
        default=None,
        description="MIME content type",
        examples=["application/pdf"]
    )
    
    file_size_bytes: int = Field(
        ...,
        ge=0,
        description="File size in bytes",
        examples=[2048576]
    )
    
    is_valid: bool = Field(
        ...,
        description="Whether the file passes validation",
        examples=[True]
    )
    
    validation_errors: List[str] = Field(
        default_factory=list,
        description="List of validation error messages",
        examples=[["File type not supported", "File size exceeds limit"]]
    )


# ---- Utility Models ----

class SystemMetrics(BaseModel):
    """System metrics and resource usage."""
    
    model_config = ConfigDict(
        validate_assignment=True
    )
    
    total_documents: int = Field(
        ...,
        ge=0,
        description="Total number of documents processed",
        examples=[25]
    )
    
    total_queries: int = Field(
        ...,
        ge=0,
        description="Total number of queries processed",
        examples=[150]
    )
    
    average_query_time_ms: Optional[float] = Field(
        default=None,
        ge=0,
        description="Average query processing time in milliseconds",
        examples=[1250.5]
    )
    
    storage_used_bytes: Optional[int] = Field(
        default=None,
        ge=0,
        description="Total storage used in bytes",
        examples=[104857600]
    )
    
    last_query_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp of the last query",
        examples=["2024-01-15T10:30:00.000Z"]
    )


# Export all models for easy importing
__all__ = [
    # Enums
    "HealthStatus",
    "DocumentStatus",
    "ProcessingStage",
    
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
    "VectorStoreListResponse",
    
    # Metadata models
    "DocumentInfo",
    "VectorStoreInfo",
    "ProcessingStatus",
    "FileValidationInfo",
    "SystemMetrics",
    
    # Base models
    "TimestampMixin"
]