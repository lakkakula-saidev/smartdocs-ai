"""
Document upload route handlers for SmartDocs AI Backend.

This module provides endpoints for document upload, processing, and metadata
management including PDF validation, text extraction, chunking, vector
embedding creation, and storage operations.
"""

import time
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from ..config import Settings, get_settings
from ..exceptions import (
    SmartDocsException,
    DocumentProcessingError,
    FileProcessingError
)
from ..logger import get_logger
from ..models.schemas import (
    UploadResponse,
    ErrorResponse,
    DocumentInfo,
    DocumentListResponse,
    FileValidationInfo
)
from ..services.document_service import DocumentService

# Create router with proper tags and metadata
router = APIRouter(
    prefix="",
    tags=["upload"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad request - validation error"},
        413: {"model": ErrorResponse, "description": "File too large"},
        415: {"model": ErrorResponse, "description": "Unsupported file type"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        503: {"model": ErrorResponse, "description": "Service unavailable"}
    }
)

logger = get_logger("upload_routes")


def get_document_service(settings: Settings = Depends(get_settings)) -> DocumentService:
    """
    Dependency to provide DocumentService instance.
    
    Args:
        settings: Application settings from dependency injection
        
    Returns:
        Configured DocumentService instance
    """
    return DocumentService(settings=settings)


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload PDF Document",
    description="""
    Upload a PDF document for processing and analysis.
    
    The system will:
    1. Validate the uploaded file (PDF format, size limits)
    2. Extract text content from the PDF
    3. Split text into semantic chunks
    4. Create vector embeddings using OpenAI
    5. Store embeddings in ChromaDB vector database
    6. Register document metadata for future queries
    
    **File Requirements:**
    - Must be a PDF file (.pdf extension or application/pdf MIME type)
    - Must contain extractable text (not just images)
    - File size limits apply (check system configuration)
    
    **Processing Time:**
    - Small documents (< 10 pages): ~2-5 seconds
    - Medium documents (10-50 pages): ~5-15 seconds  
    - Large documents (50+ pages): ~15-60 seconds
    
    The returned `document_id` is required for all subsequent chat/query operations.
    """,
    responses={
        201: {
            "description": "Document uploaded and processed successfully",
            "content": {
                "application/json": {
                    "examples": {
                        "successful_upload": {
                            "summary": "Successful PDF upload and processing",
                            "value": {
                                "document_id": "a1b2c3d4e5f6789012345678901234ab",
                                "chunks": 42,
                                "bytes": 15420,
                                "filename": "research_paper.pdf",
                                "processing_time_ms": 3200
                            }
                        }
                    }
                }
            }
        },
        400: {
            "description": "Invalid file or processing error",
            "content": {
                "application/json": {
                    "examples": {
                        "unsupported_type": {
                            "summary": "Unsupported file type",
                            "value": {
                                "error": True,
                                "status_code": 400,
                                "message": "Only PDF files are supported",
                                "error_code": "UNSUPPORTED_FILE_TYPE",
                                "details": {
                                    "allowed_types": [".pdf"],
                                    "received_type": "application/msword"
                                }
                            }
                        },
                        "empty_pdf": {
                            "summary": "PDF with no extractable text",
                            "value": {
                                "error": True,
                                "status_code": 400,
                                "message": "No extractable text found in PDF",
                                "error_code": "EMPTY_PDF_TEXT",
                                "details": {
                                    "filename": "scanned_document.pdf"
                                }
                            }
                        }
                    }
                }
            }
        },
        413: {
            "description": "File size exceeds limits",
            "content": {
                "application/json": {
                    "examples": {
                        "file_too_large": {
                            "summary": "File exceeds size limit",
                            "value": {
                                "error": True,
                                "status_code": 413,
                                "message": "File size exceeds maximum allowed limit",
                                "error_code": "FILE_TOO_LARGE",
                                "details": {
                                    "file_size_bytes": 52428800,
                                    "max_size_bytes": 50331648
                                }
                            }
                        }
                    }
                }
            }
        },
        503: {
            "description": "Service unavailable (e.g., OpenAI API issues)",
            "content": {
                "application/json": {
                    "examples": {
                        "api_unavailable": {
                            "summary": "OpenAI API unavailable",
                            "value": {
                                "error": True,
                                "status_code": 503,
                                "message": "Document processing service temporarily unavailable",
                                "error_code": "OPENAI_API_UNAVAILABLE",
                                "details": {
                                    "service": "OpenAI Embeddings API"
                                }
                            }
                        }
                    }
                }
            }
        }
    }
)
async def upload_document(
    file: UploadFile = File(
        ...,
        description="PDF file to upload and process",
        media_type="application/pdf"
    ),
    document_service: DocumentService = Depends(get_document_service)
) -> UploadResponse:
    """
    Upload and process a PDF document.
    
    Args:
        file: Uploaded PDF file
        document_service: Document service dependency
        
    Returns:
        Upload response with document metadata
        
    Raises:
        HTTPException: Various HTTP errors for validation, processing, or service issues
    """
    start_time = time.time()
    
    logger.info(
        "Document upload requested",
        extra={
            "uploaded_filename": file.filename,
            "content_type": file.content_type,
            "size": getattr(file, 'size', None)
        }
    )
    
    try:
        # Process the uploaded document
        upload_response = await document_service.process_upload(file)
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        logger.info(
            "Document upload completed successfully",
            extra={
                "document_id": upload_response.document_id,
                "uploaded_filename": file.filename,
                "chunks": upload_response.chunks,
                "bytes": upload_response.bytes,
                "processing_time_ms": processing_time_ms
            }
        )
        
        return upload_response
        
    except FileProcessingError as e:
        logger.error(
            "File processing error during upload",
            extra={
                "uploaded_filename": file.filename,
                "error_code": e.error_code,
                "message": e.message
            },
            exc_info=True
        )
        
        # Map to appropriate HTTP status codes
        if "UNSUPPORTED_FILE_TYPE" in e.error_code:
            status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        elif "FILE_TOO_LARGE" in e.error_code:
            status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        else:
            status_code = status.HTTP_400_BAD_REQUEST
            
        raise HTTPException(
            status_code=status_code,
            detail=e.message
        )
        
    except DocumentProcessingError as e:
        logger.error(
            "Document processing error during upload",
            extra={
                "uploaded_filename": file.filename,
                "error_code": e.error_code,
                "message": e.message
            },
            exc_info=True
        )
        
        # Map processing errors to HTTP status codes
        if "OPENAI" in e.error_code or "API" in e.error_code:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif "EMPTY_PDF_TEXT" in e.error_code:
            status_code = status.HTTP_400_BAD_REQUEST
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            
        raise HTTPException(
            status_code=status_code,
            detail=e.message
        )
        
    except SmartDocsException as e:
        logger.error(
            "SmartDocs error during upload",
            extra={
                "uploaded_filename": file.filename,
                "error_code": e.error_code,
                "message": e.message
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message
        )
        
    except Exception as e:
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        logger.error(
            "Unexpected error during document upload",
            extra={
                "uploaded_filename": file.filename,
                "error": str(e),
                "processing_time_ms": processing_time_ms
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document upload failed due to internal error"
        )


@router.post(
    "/upload/validate",
    response_model=FileValidationInfo,
    summary="Validate File for Upload",
    description="""
    Validate a file for upload without actually processing it.
    
    This endpoint performs validation checks including:
    - File type and extension validation
    - File size limits
    - Content type verification
    - Basic file integrity checks
    
    Useful for frontend validation before initiating actual upload.
    """,
    responses={
        200: {
            "description": "File validation results",
            "content": {
                "application/json": {
                    "examples": {
                        "valid_file": {
                            "summary": "Valid PDF file",
                            "value": {
                                "filename": "document.pdf",
                                "content_type": "application/pdf",
                                "file_size_bytes": 2048576,
                                "is_valid": True,
                                "validation_errors": []
                            }
                        },
                        "invalid_file": {
                            "summary": "Invalid file with errors",
                            "value": {
                                "filename": "document.docx",
                                "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                "file_size_bytes": 1024000,
                                "is_valid": False,
                                "validation_errors": [
                                    "File type not supported. Only PDF files are allowed.",
                                    "Content type 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' not supported."
                                ]
                            }
                        }
                    }
                }
            }
        }
    }
)
async def validate_file_upload(
    file: UploadFile = File(..., description="File to validate for upload"),
    document_service: DocumentService = Depends(get_document_service)
) -> FileValidationInfo:
    """
    Validate a file for upload eligibility.
    
    Args:
        file: File to validate
        document_service: Document service dependency
        
    Returns:
        File validation information
    """
    logger.info(
        "File validation requested",
        extra={
            "uploaded_filename": file.filename,
            "content_type": file.content_type
        }
    )
    
    try:
        validation_info = await document_service.validate_upload(file)
        
        logger.info(
            "File validation completed",
            extra={
                "uploaded_filename": file.filename,
                "is_valid": validation_info.is_valid,
                "error_count": len(validation_info.validation_errors)
            }
        )
        
        return validation_info
        
    except Exception as e:
        logger.error(
            "Error during file validation",
            extra={
                "uploaded_filename": file.filename,
                "error": str(e)
            },
            exc_info=True
        )
        
        # Return validation info with errors instead of raising exception
        return FileValidationInfo(
            filename=file.filename or "unknown",
            content_type=file.content_type,
            file_size_bytes=getattr(file, 'size', 0) or 0,
            is_valid=False,
            validation_errors=[f"Validation failed: {str(e)}"]
        )


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="List Uploaded Documents",
    description="""
    Get a list of all uploaded and processed documents.
    
    Returns document metadata including:
    - Document ID and original filename
    - Processing status and timestamps
    - File sizes and chunk counts
    - Vector store information
    
    Useful for document management interfaces and status monitoring.
    """,
    responses={
        200: {
            "description": "List of documents",
            "content": {
                "application/json": {
                    "examples": {
                        "document_list": {
                            "summary": "List of uploaded documents",
                            "value": {
                                "documents": [
                                    {
                                        "document_id": "a1b2c3d4e5f6789012345678901234ab",
                                        "filename": "research_paper.pdf",
                                        "file_size_bytes": 2048576,
                                        "text_size_bytes": 15420,
                                        "chunk_count": 42,
                                        "status": "ready",
                                        "collection_name": "doc_a1b2c3d4e5f6789012345678901234ab",
                                        "processing_time_ms": 3200,
                                        "created_at": "2024-01-15T10:30:00.000Z",
                                        "updated_at": "2024-01-15T10:30:03.200Z"
                                    }
                                ],
                                "total_count": 1,
                                "page": None,
                                "page_size": None
                            }
                        }
                    }
                }
            }
        }
    }
)
async def list_documents(
    document_service: DocumentService = Depends(get_document_service)
) -> DocumentListResponse:
    """
    List all uploaded documents.
    
    Args:
        document_service: Document service dependency
        
    Returns:
        List of document information
    """
    logger.info("Document list requested")
    
    try:
        documents = await document_service.list_documents()
        
        logger.info(
            "Document list retrieved successfully",
            extra={"document_count": len(documents)}
        )
        
        return DocumentListResponse(
            documents=documents,
            total_count=len(documents)
        )
        
    except Exception as e:
        logger.error(
            "Error retrieving document list",
            extra={"error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document list"
        )


@router.get(
    "/documents/{document_id}",
    response_model=DocumentInfo,
    summary="Get Document Information",
    description="""
    Get detailed information about a specific document.
    
    Returns comprehensive document metadata including:
    - Processing status and timestamps
    - File sizes and content statistics  
    - Vector store collection details
    - Processing performance metrics
    """,
    responses={
        200: {
            "description": "Document information",
            "content": {
                "application/json": {
                    "examples": {
                        "document_info": {
                            "summary": "Document information",
                            "value": {
                                "document_id": "a1b2c3d4e5f6789012345678901234ab",
                                "filename": "research_paper.pdf",
                                "file_size_bytes": 2048576,
                                "text_size_bytes": 15420,
                                "chunk_count": 42,
                                "status": "ready",
                                "collection_name": "doc_a1b2c3d4e5f6789012345678901234ab",
                                "processing_time_ms": 3200,
                                "created_at": "2024-01-15T10:30:00.000Z",
                                "updated_at": "2024-01-15T10:30:03.200Z"
                            }
                        }
                    }
                }
            }
        },
        404: {
            "description": "Document not found",
            "content": {
                "application/json": {
                    "examples": {
                        "not_found": {
                            "summary": "Document not found",
                            "value": {
                                "error": True,
                                "status_code": 404,
                                "message": "Document with ID 'invalid123' not found",
                                "error_code": "DOCUMENT_NOT_FOUND",
                                "details": {
                                    "document_id": "invalid123"
                                }
                            }
                        }
                    }
                }
            }
        }
    }
)
async def get_document(
    document_id: str,
    document_service: DocumentService = Depends(get_document_service)
) -> DocumentInfo:
    """
    Get information about a specific document.
    
    Args:
        document_id: Document identifier
        document_service: Document service dependency
        
    Returns:
        Document information
        
    Raises:
        HTTPException: 404 if document not found
    """
    logger.info(
        "Document info requested",
        extra={"document_id": document_id}
    )
    
    try:
        document_info = await document_service.get_document(document_id)
        
        logger.info(
            "Document info retrieved successfully",
            extra={
                "document_id": document_id,
                "uploaded_filename": document_info.filename,
                "status": document_info.status
            }
        )
        
        return document_info
        
    except SmartDocsException as e:
        if "NOT_FOUND" in e.error_code:
            logger.warning(
                "Document not found",
                extra={"document_id": document_id}
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID '{document_id}' not found"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=e.message
            )
            
    except Exception as e:
        logger.error(
            "Error retrieving document info",
            extra={"document_id": document_id, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document information"
        )