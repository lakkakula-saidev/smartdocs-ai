"""
Utility modules for SmartDocs AI Backend.

This package contains various utility functions and helpers used throughout
the application, extracted from the original monolithic main.py file.
"""

from .file_utils import (
    extract_pdf_text,
    validate_file_upload,
    create_temp_file,
    cleanup_temp_file
)

from .text_processing import (
    enhance_markdown,
    split_text_into_chunks
)

from .validation import (
    validate_query,
    validate_document_id,
    sanitize_filename
)

__all__ = [
    # File utilities
    "extract_pdf_text",
    "validate_file_upload", 
    "create_temp_file",
    "cleanup_temp_file",
    
    # Text processing
    "enhance_markdown",
    "split_text_into_chunks",
    
    # Validation
    "validate_query",
    "validate_document_id", 
    "sanitize_filename",
]