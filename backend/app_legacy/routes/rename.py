"""
Document rename routes for SmartDocs AI Backend.

This module provides API endpoints for renaming document display names,
allowing users to customize how their documents are displayed in the interface.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Annotated

from ..config import get_settings, Settings
from ..exceptions import DocumentNotFoundError, DocumentProcessingError
from ..logger import get_logger
from ..models.schemas import RenameDocumentRequest, RenameDocumentResponse
from ..services.document_service import DocumentService

logger = get_logger("rename_routes")

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    responses={404: {"description": "Document not found"}}
)


def get_document_service(settings: Annotated[Settings, Depends(get_settings)]) -> DocumentService:
    """Dependency to get document service instance."""
    return DocumentService(settings)


@router.put("/{document_id}/rename", response_model=RenameDocumentResponse)
async def rename_document(
    document_id: str,
    request: RenameDocumentRequest,
    document_service: Annotated[DocumentService, Depends(get_document_service)]
) -> RenameDocumentResponse:
    """
    Rename a document's display name.
    
    Updates the display name for an existing document. The document ID in the URL
    must match the document_id in the request body for security.
    
    Args:
        document_id: Document identifier from URL path
        request: Rename request containing document_id and new_display_name
        document_service: Document service dependency
        
    Returns:
        Rename response with old and new display names
        
    Raises:
        HTTPException: If document not found or validation fails
    """
    logger.info(
        f"Document rename requested",
        extra={
            "document_id": document_id,
            "new_display_name": request.new_display_name,
            "request_document_id": request.document_id
        }
    )
    
    # Validate that URL document_id matches request document_id
    if document_id != request.document_id:
        logger.warning(
            f"Document ID mismatch in rename request",
            extra={
                "url_document_id": document_id,
                "request_document_id": request.document_id
            }
        )
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Document ID mismatch",
                "message": f"URL document ID '{document_id}' does not match request document ID '{request.document_id}'",
                "error_code": "DOCUMENT_ID_MISMATCH"
            }
        )
    
    try:
        # Get current document info to capture old display name
        current_doc = await document_service.get_document(document_id)
        old_display_name = current_doc.get_display_name()
        
        # Perform the rename
        updated_doc = await document_service.rename_document(document_id, request.new_display_name)
        
        logger.info(
            f"Document renamed successfully",
            extra={
                "document_id": document_id,
                "old_display_name": old_display_name,
                "new_display_name": request.new_display_name
            }
        )
        
        return RenameDocumentResponse(
            document_id=document_id,
            old_display_name=old_display_name,
            new_display_name=request.new_display_name,
            success=True
        )
        
    except DocumentNotFoundError:
        logger.error(
            f"Document not found for rename",
            extra={"document_id": document_id}
        )
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Document not found",
                "message": f"No document found with ID: {document_id}",
                "error_code": "DOCUMENT_NOT_FOUND",
                "document_id": document_id
            }
        )
        
    except Exception as e:
        logger.error(
            f"Failed to rename document",
            extra={
                "document_id": document_id,
                "new_display_name": request.new_display_name,
                "error": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Document rename failed",
                "message": f"Failed to rename document: {str(e)}",
                "error_code": "RENAME_FAILED",
                "document_id": document_id
            }
        )


@router.get("/{document_id}", response_model=dict)
async def get_document(
    document_id: str,
    document_service: Annotated[DocumentService, Depends(get_document_service)]
) -> dict:
    """
    Get document metadata by ID.
    
    Retrieves detailed information about a document including its current
    display name, processing status, and other metadata.
    
    Args:
        document_id: Document identifier
        document_service: Document service dependency
        
    Returns:
        Document information dictionary
        
    Raises:
        HTTPException: If document not found
    """
    logger.debug(
        f"Document metadata requested",
        extra={"document_id": document_id}
    )
    
    try:
        doc_info = await document_service.get_document(document_id)
        
        return {
            "document_id": doc_info.document_id,
            "filename": doc_info.filename,
            "display_name": doc_info.get_display_name(),
            "file_size_bytes": doc_info.file_size_bytes,
            "text_size_bytes": doc_info.text_size_bytes,
            "chunk_count": doc_info.chunk_count,
            "status": doc_info.status,
            "processing_time_ms": doc_info.processing_time_ms,
            "created_at": doc_info.created_at.isoformat() if doc_info.created_at else None
        }
        
    except DocumentNotFoundError:
        logger.error(
            f"Document not found",
            extra={"document_id": document_id}
        )
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Document not found",
                "message": f"No document found with ID: {document_id}",
                "error_code": "DOCUMENT_NOT_FOUND",
                "document_id": document_id
            }
        )
        
    except Exception as e:
        logger.error(
            f"Failed to retrieve document",
            extra={"document_id": document_id, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Document retrieval failed",
                "message": f"Failed to retrieve document: {str(e)}",
                "error_code": "RETRIEVAL_FAILED",
                "document_id": document_id
            }
        )