"""
File handling utilities for SmartDocs AI Backend.

This module contains functions for PDF processing, file validation,
and temporary file management extracted from the original main.py.
"""

import os
import tempfile
import shutil
from typing import BinaryIO
from pathlib import Path

from fastapi import UploadFile, HTTPException, status

from ..config import get_settings
from ..logger import get_logger
from .validation import sanitize_filename

logger = get_logger("file_utils")


def extract_pdf_text(file_path: str) -> str:
    """
    Extract raw text from a PDF using pypdf (lazy import).
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Extracted text content
        
    Raises:
        HTTPException: If pypdf is not installed or PDF cannot be read
    """
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError as e:
        logger.error("pypdf not installed", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="pypdf not installed. Install with: pip install pypdf"
        ) from e
    
    try:
        logger.debug(f"Extracting text from PDF: {file_path}")
        reader = PdfReader(file_path)
        pages: list[str] = []
        
        for page_num, page in enumerate(reader.pages):
            try:
                txt = page.extract_text() or ""
                pages.append(txt)
                logger.debug(f"Extracted {len(txt)} characters from page {page_num + 1}")
            except Exception as e:
                logger.warning(f"Failed to extract text from page {page_num + 1}: {e}")
                pages.append("")  # Add empty string to maintain page order
        
        text = "\n".join(pages).strip()
        
        if not text:
            logger.error("No extractable text found in PDF", extra={"file_path": file_path})
            raise ValueError("No extractable text")
        
        logger.info(f"Successfully extracted {len(text)} characters from PDF", 
                   extra={"file_path": file_path, "pages": len(pages), "text_length": len(text)})
        return text
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to read PDF: {e}", extra={"file_path": file_path}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read PDF: {e}"
        )


def validate_file_upload(file: UploadFile) -> None:
    """
    Validate uploaded file against configured constraints.
    
    Args:
        file: FastAPI UploadFile object
        
    Raises:
        HTTPException: If file validation fails
    """
    settings = get_settings()
    
    # Check file type
    if (file.content_type not in settings.allowed_file_types and 
        not file.filename.lower().endswith(".pdf")):
        logger.warning(f"Invalid file type: {file.content_type}", 
                      extra={"filename": file.filename, "content_type": file.content_type})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported."
        )
    
    # Check file size if available
    if hasattr(file, 'size') and file.size is not None:
        if file.size > settings.max_upload_size_bytes:
            logger.warning(f"File too large: {file.size} bytes", 
                          extra={"filename": file.filename, "size": file.size, 
                                "max_size": settings.max_upload_size_bytes})
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB"
            )
    
    # Check filename
    if not file.filename:
        logger.warning("No filename provided")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required."
        )
    
    logger.debug(f"File validation passed", 
                extra={"filename": file.filename, "content_type": file.content_type})


def create_temp_file(file: UploadFile, prefix: str = "upload_pdf_") -> tuple[str, str]:
    """
    Create a temporary file from an uploaded file.
    
    Args:
        file: FastAPI UploadFile object
        prefix: Prefix for temporary directory name
        
    Returns:
        Tuple of (temp_directory_path, temp_file_path)
        
    Raises:
        HTTPException: If file creation fails
    """
    try:
        temp_dir = tempfile.mkdtemp(prefix=prefix)
        sanitized_filename = sanitize_filename(file.filename)
        temp_path = os.path.join(temp_dir, sanitized_filename)
        
        logger.debug(f"Creating temporary file", 
                    extra={"temp_dir": temp_dir, "temp_path": temp_path, 
                          "original_filename": file.filename})
        
        return temp_dir, temp_path
        
    except Exception as e:
        logger.error(f"Failed to create temporary file: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create temporary file: {e}"
        )


def cleanup_temp_file(temp_dir: str) -> None:
    """
    Clean up temporary directory and its contents.
    
    Args:
        temp_dir: Path to temporary directory to remove
    """
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.debug(f"Cleaned up temporary directory: {temp_dir}")
    except Exception as e:
        logger.warning(f"Failed to cleanup temporary directory {temp_dir}: {e}")


async def save_upload_to_temp(file: UploadFile, temp_path: str) -> int:
    """
    Save uploaded file content to temporary file.
    
    Args:
        file: FastAPI UploadFile object
        temp_path: Path where to save the file
        
    Returns:
        Number of bytes written
        
    Raises:
        HTTPException: If file save fails
    """
    try:
        bytes_written = 0
        
        with open(temp_path, "wb") as f:
            while chunk := await file.read(8192):  # Read in 8KB chunks
                f.write(chunk)
                bytes_written += len(chunk)
        
        logger.debug(f"Saved {bytes_written} bytes to temporary file", 
                    extra={"temp_path": temp_path, "bytes": bytes_written})
        
        return bytes_written
        
    except Exception as e:
        logger.error(f"Failed to save file to {temp_path}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file: {e}"
        )


def ensure_directory_exists(directory_path: str) -> Path:
    """
    Ensure directory exists, creating it if necessary.
    
    Args:
        directory_path: Path to directory
        
    Returns:
        Path object for the directory
        
    Raises:
        HTTPException: If directory cannot be created
    """
    try:
        path = Path(directory_path)
        path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured directory exists: {path}")
        return path
    except Exception as e:
        logger.error(f"Failed to create directory {directory_path}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create directory: {e}"
        )


def get_file_info(file_path: str) -> dict:
    """
    Get information about a file.
    
    Args:
        file_path: Path to file
        
    Returns:
        Dictionary with file information
    """
    try:
        stat = os.stat(file_path)
        return {
            "path": file_path,
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "exists": True
        }
    except FileNotFoundError:
        return {
            "path": file_path,
            "exists": False
        }
    except Exception as e:
        logger.warning(f"Failed to get file info for {file_path}: {e}")
        return {
            "path": file_path,
            "exists": False,
            "error": str(e)
        }