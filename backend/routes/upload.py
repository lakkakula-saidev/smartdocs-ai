"""
Document upload routes for SmartDocs AI Backend.

Simplified upload processing using direct module imports.
"""

import time
import tempfile
import os
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile, status
import pypdf

from config import get_settings
from models import UploadResponse, ErrorResponse, FileValidationInfo, DocumentListResponse
from storage import get_unified_storage, process_document_text
from security import InputSanitizer

# Create router
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


def validate_file_upload(file: UploadFile) -> None:
    """
    Validate uploaded file.
    
    Args:
        file: Uploaded file to validate
        
    Raises:
        HTTPException: If validation fails
    """
    settings = get_settings()
    
    # Check file type
    if file.content_type not in settings.allowed_file_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Only PDF files are supported. Got: {file.content_type}"
        )
    
    # Sanitize and check filename
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
        )
    
    sanitized_filename = InputSanitizer.sanitize_filename(file.filename)
    if not sanitized_filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File must have .pdf extension"
        )
    
    # Check file size (if available)
    if hasattr(file, 'size') and file.size:
        if file.size > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed size of {settings.max_upload_size_mb}MB"
            )


def extract_pdf_text(file_path: str) -> str:
    """
    Extract text from PDF file.
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        Extracted text content
        
    Raises:
        HTTPException: If text extraction fails
    """
    try:
        text_content = []
        
        with open(file_path, 'rb') as file:
            pdf_reader = pypdf.PdfReader(file)
            
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text.strip():
                        text_content.append(page_text)
                except Exception as e:
                    print(f"[upload] Warning: Failed to extract text from page {page_num + 1}: {e}")
                    continue
        
        full_text = '\n\n'.join(text_content)
        
        if not full_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No extractable text found in PDF. The PDF may contain only images or be corrupted."
            )
        
        return full_text
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[upload] ERROR: PDF text extraction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to extract text from PDF: {str(e)}"
        )


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
    """
)
async def upload_document(
    file: UploadFile = File(..., description="PDF file to upload and process")
) -> UploadResponse:
    """
    Upload and process a PDF document.
    
    Args:
        file: Uploaded PDF file
        
    Returns:
        Upload response with document metadata
        
    Raises:
        HTTPException: Various HTTP errors for validation, processing, or service issues
    """
    start_time = time.time()
    temp_path = None
    
    print(f"[upload] Document upload requested: {file.filename}")
    
    try:
        # Check if OpenAI API key is configured
        settings = get_settings()
        if not settings.has_openai_key:
            print("[upload] ERROR: Upload attempted without OpenAI API key")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI processing service not available. OpenAI API key not configured."
            )
        
        # Step 1: Validate file
        validate_file_upload(file)
        
        # Step 2: Save to temporary file
        import uuid
        document_id = uuid.uuid4().hex
        
        # Use sanitized filename for security
        sanitized_filename = InputSanitizer.sanitize_filename(file.filename or "document.pdf")
        
        temp_dir = tempfile.mkdtemp(prefix=f"smartdocs_upload_{document_id}_")
        temp_path = os.path.join(temp_dir, sanitized_filename)
        
        # Write file data
        content = await file.read()
        with open(temp_path, "wb") as temp_file:
            temp_file.write(content)
        
        print(f"[upload] Saved file to temporary location: {temp_path}")
        
        # Step 3: Extract text from PDF
        extracted_text = extract_pdf_text(temp_path)
        
        print(f"[upload] Extracted {len(extracted_text)} characters of text")
        
        # Step 4: Process document and create embeddings
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        doc_info = await process_document_text(
            document_id=document_id,
            text=extracted_text,
            filename=file.filename,
            file_size_bytes=len(content),
            processing_time_ms=processing_time_ms
        )
        
        final_processing_time_ms = int((time.time() - start_time) * 1000)
        
        print(f"[upload] Document processing completed successfully in {final_processing_time_ms}ms")
        
        return UploadResponse(
            document_id=document_id,
            chunks=doc_info.chunk_count,
            bytes=doc_info.text_size_bytes,
            filename=file.filename,
            processing_time_ms=final_processing_time_ms,
            display_name=doc_info.get_display_name()
        )
        
    except HTTPException:
        raise
        
    except Exception as e:
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        print(f"[upload] ERROR: Unexpected error during upload: {e}")
        
        # Provide helpful error messages based on common issues (without exposing internal details)
        error_str = str(e).lower()
        if "openai" in error_str and ("api" in error_str or "key" in error_str):
            detail = "AI processing service unavailable. Please check configuration."
        elif "chroma" in error_str or "vector" in error_str:
            detail = "Document storage service unavailable. Please try again later."
        elif "permission" in error_str or "access" in error_str:
            detail = "Document processing failed due to system permissions. Please try again later."
        else:
            detail = "Document upload failed due to internal error. Please try again later."
        
        # Log detailed error securely (don't expose to client)
        error_id = __import__('secrets').token_hex(8)
        print(f"[upload] ERROR [{error_id}]: Upload failed: {type(e).__name__}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )
        
    finally:
        # Always cleanup temporary file
        if temp_path and os.path.exists(temp_path):
            try:
                temp_dir = os.path.dirname(temp_path)
                import shutil
                shutil.rmtree(temp_dir)
                print(f"[upload] Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                print(f"[upload] Warning: Failed to cleanup temporary file: {e}")


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
    """
)
async def validate_file_upload_endpoint(
    file: UploadFile = File(..., description="File to validate for upload")
) -> FileValidationInfo:
    """
    Validate a file for upload eligibility.
    
    Args:
        file: File to validate
        
    Returns:
        File validation information
    """
    print(f"[upload] File validation requested: {file.filename}")
    
    validation_errors = []
    
    try:
        validate_file_upload(file)
        is_valid = True
    except HTTPException as e:
        validation_errors.append(e.detail)
        is_valid = False
    except Exception as e:
        validation_errors.append(f"Validation failed: {str(e)}")
        is_valid = False
    
    file_size = getattr(file, 'size', 0) or 0
    
    validation_info = FileValidationInfo(
        filename=file.filename or "unknown",
        content_type=file.content_type,
        file_size_bytes=file_size,
        is_valid=is_valid,
        validation_errors=validation_errors
    )
    
    print(f"[upload] File validation completed: valid={is_valid}, errors={len(validation_errors)}")
    
    return validation_info


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
    """
)
async def list_documents() -> DocumentListResponse:
    """
    List all uploaded documents.
    
    Returns:
        List of document information
    """
    print("[upload] Document list requested")
    
    try:
        storage = get_unified_storage()
        documents = await storage.list_documents()
        
        print(f"[upload] Document list retrieved: {len(documents)} documents")
        
        return DocumentListResponse(
            documents=documents,
            total_count=len(documents)
        )
        
    except Exception as e:
        print(f"[upload] ERROR: Failed to retrieve document list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document list"
        )