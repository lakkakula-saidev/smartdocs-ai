"""
Custom exception handling for SmartDocs AI Backend.

This module provides custom exception classes and handlers for improved
error handling and user feedback throughout the application.
"""

from typing import Any, Dict, Optional, Union
import traceback

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import http_exception_handler
from pydantic import ValidationError

from .logger import get_logger

logger = get_logger("exceptions")


class SmartDocsException(Exception):
    """
    Base exception class for SmartDocs AI application.
    
    All custom exceptions should inherit from this class.
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize SmartDocs exception.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}


class ConfigurationError(SmartDocsException):
    """
    Raised when there are configuration-related errors.
    
    Examples:
        - Missing required environment variables
        - Invalid configuration values
        - Dependency configuration issues
    """
    pass


class DocumentProcessingError(SmartDocsException):
    """
    Raised when document processing fails.
    
    Examples:
        - PDF text extraction failures
        - Text chunking errors
        - Vector embedding creation failures
    """
    pass


class VectorStoreError(SmartDocsException):
    """
    Raised when vector store operations fail.
    
    Examples:
        - ChromaDB connection failures
        - Index creation errors
        - Query execution failures
    """
    pass


class AIServiceError(SmartDocsException):
    """
    Raised when AI/LLM service operations fail.
    
    Examples:
        - OpenAI API failures
        - Model loading errors
        - Generation failures
    """
    pass


class ValidationError(SmartDocsException):
    """
    Raised when input validation fails.
    
    Examples:
        - Invalid query format
        - Invalid document ID
        - File validation failures
    """
    pass


class DocumentNotFoundError(SmartDocsException):
    """
    Raised when a requested document is not found.
    """
    
    def __init__(self, document_id: str):
        super().__init__(
            message=f"Document with ID '{document_id}' not found",
            error_code="DOCUMENT_NOT_FOUND",
            details={"document_id": document_id}
        )


class FileProcessingError(SmartDocsException):
    """
    Raised when file processing operations fail.
    
    Examples:
        - File upload failures
        - Temporary file creation errors
        - File format issues
    """
    pass


class RateLimitExceededError(SmartDocsException):
    """
    Raised when rate limits are exceeded.
    """
    
    def __init__(self, limit: int, window: str):
        super().__init__(
            message=f"Rate limit exceeded: {limit} requests per {window}",
            error_code="RATE_LIMIT_EXCEEDED",
            details={"limit": limit, "window": window}
        )


def create_error_response(
    status_code: int,
    message: str,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create standardized error response structure.
    
    Args:
        status_code: HTTP status code
        message: Human-readable error message
        error_code: Machine-readable error code
        details: Additional error details
        request_id: Request ID for tracking
        
    Returns:
        Standardized error response dictionary
    """
    response = {
        "error": True,
        "status_code": status_code,
        "message": message,
        "error_code": error_code or "UNKNOWN_ERROR"
    }
    
    if details:
        response["details"] = details
    
    if request_id:
        response["request_id"] = request_id
    
    return response


async def smartdocs_exception_handler(
    request: Request, 
    exc: SmartDocsException
) -> JSONResponse:
    """
    Handle SmartDocs custom exceptions.
    
    Args:
        request: FastAPI request object
        exc: SmartDocs exception instance
        
    Returns:
        JSON error response
    """
    # Map exception types to HTTP status codes
    status_code_map = {
        ConfigurationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        DocumentProcessingError: status.HTTP_422_UNPROCESSABLE_ENTITY,
        VectorStoreError: status.HTTP_503_SERVICE_UNAVAILABLE,
        AIServiceError: status.HTTP_503_SERVICE_UNAVAILABLE,
        ValidationError: status.HTTP_400_BAD_REQUEST,
        DocumentNotFoundError: status.HTTP_404_NOT_FOUND,
        FileProcessingError: status.HTTP_422_UNPROCESSABLE_ENTITY,
        RateLimitExceededError: status.HTTP_429_TOO_MANY_REQUESTS,
    }
    
    status_code = status_code_map.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Log the exception
    logger.error(
        f"{exc.__class__.__name__}: {exc.message}",
        extra={
            "error_code": exc.error_code,
            "details": exc.details,
            "status_code": status_code,
            "path": request.url.path,
            "method": request.method
        },
        exc_info=True
    )
    
    # Create error response
    error_response = create_error_response(
        status_code=status_code,
        message=exc.message,
        error_code=exc.error_code,
        details=exc.details
    )
    
    return JSONResponse(
        status_code=status_code,
        content=error_response
    )


async def http_exception_handler_with_logging(
    request: Request, 
    exc: HTTPException
) -> JSONResponse:
    """
    Enhanced HTTP exception handler with logging.
    
    Args:
        request: FastAPI request object  
        exc: HTTP exception instance
        
    Returns:
        JSON error response
    """
    # Log the HTTP exception
    logger.warning(
        f"HTTP {exc.status_code}: {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    # Create standardized error response
    error_response = create_error_response(
        status_code=exc.status_code,
        message=exc.detail,
        error_code=f"HTTP_{exc.status_code}"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response
    )


async def validation_exception_handler(
    request: Request,
    exc: ValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors.
    
    Args:
        request: FastAPI request object
        exc: Pydantic validation error
        
    Returns:
        JSON error response with validation details
    """
    # Extract validation error details
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " -> ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(
        f"Validation error: {len(errors)} field(s) failed validation",
        extra={
            "validation_errors": errors,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    error_response = create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Validation failed",
        error_code="VALIDATION_ERROR",
        details={"validation_errors": errors}
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response
    )


async def general_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    Handle unexpected exceptions.
    
    Args:
        request: FastAPI request object
        exc: Exception instance
        
    Returns:
        JSON error response
    """
    # Log the unexpected exception with full traceback
    logger.error(
        f"Unexpected error: {exc.__class__.__name__}: {str(exc)}",
        extra={
            "exception_type": exc.__class__.__name__,
            "path": request.url.path,
            "method": request.method,
            "traceback": traceback.format_exc()
        },
        exc_info=True
    )
    
    # Don't expose internal error details in production
    from .config import get_settings
    settings = get_settings()
    
    if settings.is_development:
        message = f"{exc.__class__.__name__}: {str(exc)}"
        details = {"traceback": traceback.format_exc().split('\n')}
    else:
        message = "An internal server error occurred"
        details = None
    
    error_response = create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message=message,
        error_code="INTERNAL_SERVER_ERROR",
        details=details
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response
    )


def setup_exception_handlers(app) -> None:
    """
    Set up exception handlers for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    # Custom SmartDocs exceptions
    app.add_exception_handler(SmartDocsException, smartdocs_exception_handler)
    
    # HTTP exceptions with enhanced logging
    app.add_exception_handler(HTTPException, http_exception_handler_with_logging)
    
    # Pydantic validation errors
    app.add_exception_handler(ValidationError, validation_exception_handler)
    
    # General exception handler (catch-all)
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("Exception handlers configured successfully")


# Context manager for exception handling
class ExceptionContext:
    """
    Context manager for handling exceptions with custom error mapping.
    
    Example:
        with ExceptionContext(DocumentProcessingError, "Failed to process document"):
            # Code that might raise various exceptions
            process_document()
    """
    
    def __init__(
        self, 
        exception_class: type,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize exception context.
        
        Args:
            exception_class: Exception class to raise on error
            message: Error message
            error_code: Optional error code
            details: Optional error details
        """
        self.exception_class = exception_class
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Log the original exception
            logger.error(
                f"Exception in context {self.exception_class.__name__}: {exc_val}",
                exc_info=True
            )
            
            # Raise the custom exception
            raise self.exception_class(
                message=self.message,
                error_code=self.error_code,
                details={**self.details, "original_error": str(exc_val)}
            ) from exc_val
        
        return False


# Utility functions for common error scenarios
def raise_if_missing_api_key(api_key: Optional[str]) -> None:
    """
    Raise ConfigurationError if API key is missing.
    
    Args:
        api_key: API key to check
        
    Raises:
        ConfigurationError: If API key is None or empty
    """
    if not api_key:
        raise ConfigurationError(
            message="OpenAI API key not configured",
            error_code="MISSING_API_KEY",
            details={"solution": "Set OPENAI_API_KEY environment variable"}
        )


def raise_if_document_not_found(document_id: str, vector_stores: Dict) -> None:
    """
    Raise DocumentNotFoundError if document is not in vector stores.
    
    Args:
        document_id: Document ID to check
        vector_stores: Dictionary of available vector stores
        
    Raises:
        DocumentNotFoundError: If document is not found
    """
    if document_id not in vector_stores:
        raise DocumentNotFoundError(document_id)


def raise_if_invalid_file_type(filename: str, allowed_types: list) -> None:
    """
    Raise FileProcessingError if file type is not allowed.
    
    Args:
        filename: Name of the file
        allowed_types: List of allowed file extensions
        
    Raises:
        FileProcessingError: If file type is not allowed
    """
    file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
    
    if not any(filename.lower().endswith(ext) for ext in allowed_types):
        raise FileProcessingError(
            message=f"File type not supported: .{file_ext}",
            error_code="UNSUPPORTED_FILE_TYPE",
            details={
                "filename": filename,
                "allowed_types": allowed_types,
                "detected_type": file_ext
            }
        )