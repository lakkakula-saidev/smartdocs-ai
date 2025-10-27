"""
Document management routes for SmartDocs AI Backend.

Simplified document operations using direct storage integration.
"""

from typing import List

from fastapi import APIRouter, HTTPException, status

from models import DocumentInfo, RenameDocumentRequest, RenameDocumentResponse, ErrorResponse
from storage import get_unified_storage, DocumentNotFoundError

# Create router
router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    responses={
        404: {"model": ErrorResponse, "description": "Document not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)


@router.get(
    "/",
    response_model=List[DocumentInfo],
    summary="List All Documents",
    description="""
    List all uploaded documents.
    
    Returns:
        List of document information objects with metadata
    """
)
async def list_documents() -> List[DocumentInfo]:
    """
    List all uploaded documents.
    
    Returns:
        List of document information objects
    """
    print("[documents] Listing all documents")
    
    try:
        storage = get_unified_storage()
        documents = await storage.list_documents()
        
        print(f"[documents] Successfully retrieved {len(documents)} documents")
        
        return documents
        
    except Exception as e:
        print(f"[documents] ERROR: Failed to list documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document list"
        )


@router.get(
    "/{document_id}",
    response_model=DocumentInfo,
    summary="Get Document Information",
    description="""
    Get detailed information about a specific document.
    
    Args:
        document_id: Unique document identifier
        
    Returns:
        Document information with metadata
        
    Raises:
        404: If document not found
    """
)
async def get_document(document_id: str) -> DocumentInfo:
    """
    Get detailed information about a specific document.
    
    Args:
        document_id: Unique document identifier
        
    Returns:
        Document information with metadata
        
    Raises:
        HTTPException: 404 if document not found
    """
    print(f"[documents] Retrieving document info for {document_id}")
    
    try:
        storage = get_unified_storage()
        document = await storage.get_document(document_id)
        
        print(f"[documents] Successfully retrieved document info for {document_id}")
        
        return document
        
    except DocumentNotFoundError:
        print(f"[documents] Document not found: {document_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found"
        )
    except Exception as e:
        print(f"[documents] ERROR: Failed to retrieve document info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document information"
        )


@router.put(
    "/{document_id}/rename",
    response_model=RenameDocumentResponse,
    summary="Rename Document",
    description="""
    Rename a document's display name.
    
    Args:
        document_id: Unique document identifier
        request: Rename request with new display name
        
    Returns:
        Rename operation result
        
    Raises:
        404: If document not found
    """
)
async def rename_document(
    document_id: str,
    request: RenameDocumentRequest
) -> RenameDocumentResponse:
    """
    Rename a document's display name.
    
    Args:
        document_id: Unique document identifier
        request: Rename request with new display name
        
    Returns:
        Rename operation result
        
    Raises:
        HTTPException: 404 if document not found
    """
    print(f"[documents] Renaming document {document_id} to '{request.new_display_name}'")
    
    try:
        storage = get_unified_storage()
        
        # Get current document info
        current_doc = await storage.get_document(document_id)
        old_display_name = current_doc.get_display_name()
        
        # Perform rename
        updated_doc = await storage.rename_document(document_id, request.new_display_name)
        
        response = RenameDocumentResponse(
            document_id=document_id,
            old_display_name=old_display_name,
            new_display_name=request.new_display_name,
            success=True
        )
        
        print(f"[documents] Successfully renamed document {document_id}")
        
        return response
        
    except DocumentNotFoundError:
        print(f"[documents] Document not found for rename: {document_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found"
        )
    except Exception as e:
        print(f"[documents] ERROR: Failed to rename document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rename document"
        )


@router.delete(
    "/{document_id}",
    response_model=dict,
    summary="Delete Document", 
    description="""
    Delete a document and all associated data.
    
    Args:
        document_id: Unique document identifier
        
    Returns:
        Deletion confirmation
        
    Raises:
        404: If document not found
    """
)
async def delete_document(document_id: str) -> dict:
    """
    Delete a document and all associated data.
    
    Args:
        document_id: Unique document identifier
        
    Returns:
        Deletion confirmation
        
    Raises:
        HTTPException: 404 if document not found, 500 for other errors
    """
    print(f"[documents] Deleting document {document_id}")
    
    try:
        storage = get_unified_storage()
        
        # Verify document exists before deletion
        await storage.get_document(document_id)
        
        # Perform deletion
        success = await storage.delete_document(document_id)
        
        if success:
            print(f"[documents] Successfully deleted document {document_id}")
            return {
                "document_id": document_id,
                "deleted": True,
                "message": "Document deleted successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete document"
            )
        
    except DocumentNotFoundError:
        print(f"[documents] Document not found for deletion: {document_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found"
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[documents] ERROR: Failed to delete document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )