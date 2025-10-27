"""
Documents API routes for SmartDocs AI Backend.

This module provides REST endpoints for document management operations
including listing, retrieving, and managing document metadata.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException

from ..services.document_service import DocumentService
from ..models.schemas import DocumentInfo
from ..exceptions import DocumentNotFoundError
from ..logger import get_logger

router = APIRouter(prefix="/documents", tags=["documents"])
logger = get_logger("routes.documents")


def get_document_service() -> DocumentService:
    """Dependency to get document service instance."""
    return DocumentService()


@router.get("/", response_model=List[DocumentInfo])
async def list_documents(
    document_service: DocumentService = Depends(get_document_service)
):
    """
    List all uploaded documents.
    
    Returns:
        List of document information objects with metadata
        
    Example:
        GET /documents/
        
        Response:
        [
            {
                "document_id": "abc123...",
                "filename": "my-document.pdf",
                "display_name": "My Document", 
                "file_size_bytes": 1024000,
                "text_size_bytes": 50000,
                "chunk_count": 25,
                "status": "ready",
                "collection_name": "doc_abc123...",
                "processing_time_ms": 2500,
                "created_at": "2024-01-01T12:00:00Z"
            }
        ]
    """
    logger.info("Listing all documents")
    
    try:
        documents = await document_service.list_documents()
        
        logger.info(
            f"Successfully retrieved document list",
            extra={"document_count": len(documents)}
        )
        
        return documents
        
    except Exception as e:
        logger.error(
            f"Failed to list documents: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve document list"
        )


@router.get("/{document_id}", response_model=DocumentInfo)
async def get_document(
    document_id: str,
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Get detailed information about a specific document.
    
    Args:
        document_id: Unique document identifier
        
    Returns:
        Document information with metadata
        
    Raises:
        404: If document not found
        
    Example:
        GET /documents/abc123def456...
        
        Response:
        {
            "document_id": "abc123def456...",
            "filename": "research-paper.pdf",
            "display_name": "Research Paper",
            "file_size_bytes": 2048000,
            "text_size_bytes": 75000,
            "chunk_count": 38,
            "status": "ready",
            "collection_name": "doc_abc123def456...",
            "processing_time_ms": 3200,
            "created_at": "2024-01-01T12:00:00Z"
        }
    """
    logger.info(f"Retrieving document info", extra={"document_id": document_id})
    
    try:
        document = await document_service.get_document(document_id)
        
        logger.info(
            f"Successfully retrieved document info",
            extra={
                "document_id": document_id,
                "display_name": document.display_name or document.get_display_name()
            }
        )
        
        return document
        
    except DocumentNotFoundError:
        logger.warning(f"Document not found", extra={"document_id": document_id})
        raise HTTPException(
            status_code=404,
            detail=f"Document {document_id} not found"
        )
    except Exception as e:
        logger.error(
            f"Failed to retrieve document info: {str(e)}",
            extra={"document_id": document_id},
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve document information"
        )