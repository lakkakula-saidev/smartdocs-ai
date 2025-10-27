"""
Validation utilities for SmartDocs AI Backend.

This module contains functions for validating user input, document IDs,
queries, and other data validation tasks.
"""

import re
import uuid
from typing import Optional

from fastapi import HTTPException, status

from ..logger import get_logger

logger = get_logger("validation")

# Validation patterns
DOCUMENT_ID_PATTERN = re.compile(r'^[a-f0-9]{32}$')  # 32-character hex string
SAFE_FILENAME_PATTERN = re.compile(r'^[a-zA-Z0-9._-]+$')


def validate_query(query: str, min_length: int = 1, max_length: int = 5000) -> str:
    """
    Validate user query input.
    
    Args:
        query: User query string
        min_length: Minimum query length
        max_length: Maximum query length
        
    Returns:
        Cleaned and validated query
        
    Raises:
        HTTPException: If query validation fails
    """
    if not query:
        logger.warning("Empty query provided")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query must not be empty."
        )
    
    # Strip whitespace
    query = query.strip()
    
    if len(query) < min_length:
        logger.warning(f"Query too short: {len(query)} characters", 
                      extra={"query_length": len(query), "min_length": min_length})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Query must be at least {min_length} characters long."
        )
    
    if len(query) > max_length:
        logger.warning(f"Query too long: {len(query)} characters", 
                      extra={"query_length": len(query), "max_length": max_length})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Query must not exceed {max_length} characters."
        )
    
    # Check for potentially problematic patterns
    if _contains_suspicious_patterns(query):
        logger.warning("Query contains suspicious patterns", extra={"query": query[:100]})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query contains invalid patterns."
        )
    
    logger.debug(f"Query validation passed", extra={"query_length": len(query)})
    return query


def validate_document_id(document_id: str) -> str:
    """
    Validate document ID format.
    
    Args:
        document_id: Document ID to validate
        
    Returns:
        Validated document ID
        
    Raises:
        HTTPException: If document ID is invalid
    """
    if not document_id:
        logger.warning("Empty document ID provided")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document ID is required."
        )
    
    document_id = document_id.strip()
    
    if not DOCUMENT_ID_PATTERN.match(document_id):
        logger.warning(f"Invalid document ID format: {document_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format. Expected 32-character hexadecimal string."
        )
    
    logger.debug(f"Document ID validation passed", extra={"document_id": document_id})
    return document_id


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and other security issues.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for filesystem use
    """
    if not filename:
        return "unnamed_file.pdf"
    
    # Remove path components
    filename = filename.split('/')[-1].split('\\')[-1]
    
    # Replace problematic characters
    problematic_chars = '<>:"/\\|?*\x00'
    for char in problematic_chars:
        filename = filename.replace(char, '_')
    
    # Remove control characters
    filename = ''.join(char for char in filename if ord(char) >= 32)
    
    # Remove leading/trailing whitespace and dots
    filename = filename.strip(' .')
    
    # Ensure it's not empty and has an extension
    if not filename:
        filename = "unnamed_file.pdf"
    elif not filename.lower().endswith('.pdf'):
        if '.' in filename:
            name, _ = filename.rsplit('.', 1)
            filename = f"{name}.pdf"
        else:
            filename += '.pdf'
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1)
        max_name_length = 255 - len(ext) - 1
        filename = f"{name[:max_name_length]}.{ext}"
    
    logger.debug(f"Filename sanitized", extra={"original": filename, "sanitized": filename})
    return filename


def generate_document_id() -> str:
    """
    Generate a new unique document ID.
    
    Returns:
        32-character hexadecimal document ID
    """
    document_id = uuid.uuid4().hex
    logger.debug(f"Generated document ID: {document_id}")
    return document_id


def validate_pagination(
    page: Optional[int] = None, 
    page_size: Optional[int] = None,
    max_page_size: int = 100
) -> tuple[int, int]:
    """
    Validate pagination parameters.
    
    Args:
        page: Page number (1-based)
        page_size: Number of items per page
        max_page_size: Maximum allowed page size
        
    Returns:
        Tuple of (validated_page, validated_page_size)
        
    Raises:
        HTTPException: If pagination parameters are invalid
    """
    # Default values
    if page is None:
        page = 1
    if page_size is None:
        page_size = 20
    
    # Validate page number
    if page < 1:
        logger.warning(f"Invalid page number: {page}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page number must be greater than 0."
        )
    
    # Validate page size
    if page_size < 1:
        logger.warning(f"Invalid page size: {page_size}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page size must be greater than 0."
        )
    
    if page_size > max_page_size:
        logger.warning(f"Page size too large: {page_size}", 
                      extra={"page_size": page_size, "max_page_size": max_page_size})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Page size must not exceed {max_page_size}."
        )
    
    logger.debug(f"Pagination validation passed", 
                extra={"page": page, "page_size": page_size})
    return page, page_size


def validate_api_key_format(api_key: str, prefix: str = "sk-") -> bool:
    """
    Validate API key format.
    
    Args:
        api_key: API key to validate
        prefix: Expected prefix for the API key
        
    Returns:
        True if format is valid, False otherwise
    """
    if not api_key:
        return False
    
    if not api_key.startswith(prefix):
        return False
    
    # Basic length check (OpenAI keys are typically 50+ characters)
    if len(api_key) < 20:
        return False
    
    return True


def validate_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if format is valid, False otherwise
    """
    if not email:
        return False
    
    # Simple email validation pattern
    email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    return bool(email_pattern.match(email))


def _contains_suspicious_patterns(text: str) -> bool:
    """
    Check if text contains potentially suspicious patterns.
    
    Args:
        text: Text to check
        
    Returns:
        True if suspicious patterns are found
    """
    suspicious_patterns = [
        # SQL injection patterns
        r'(?i)(union\s+select|drop\s+table|delete\s+from)',
        # Script injection patterns  
        r'(?i)(<script|javascript:|vbscript:)',
        # Command injection patterns
        r'(?i)(;|\||\&\&|\|\|)(\s*)(\w+)',
        # Path traversal patterns
        r'(\.\.\/|\.\.\\)',
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, text):
            return True
    
    return False


def validate_search_query(
    query: str,
    min_length: int = 2,
    max_length: int = 1000
) -> str:
    """
    Validate search query with more lenient rules than chat queries.
    
    Args:
        query: Search query string
        min_length: Minimum query length
        max_length: Maximum query length
        
    Returns:
        Cleaned and validated query
        
    Raises:
        HTTPException: If query validation fails
    """
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty."
        )
    
    query = query.strip()
    
    if len(query) < min_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Search query must be at least {min_length} characters long."
        )
    
    if len(query) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Search query must not exceed {max_length} characters."
        )
    
    return query


def validate_positive_integer(
    value: Optional[int],
    field_name: str,
    min_value: int = 1,
    max_value: Optional[int] = None
) -> int:
    """
    Validate that a value is a positive integer within bounds.
    
    Args:
        value: Value to validate
        field_name: Name of the field for error messages
        min_value: Minimum allowed value
        max_value: Maximum allowed value (optional)
        
    Returns:
        Validated integer value
        
    Raises:
        HTTPException: If validation fails
    """
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} is required."
        )
    
    if not isinstance(value, int):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be an integer."
        )
    
    if value < min_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be at least {min_value}."
        )
    
    if max_value is not None and value > max_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must not exceed {max_value}."
        )
    
    return value