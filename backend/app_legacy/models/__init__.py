"""
Pydantic models for SmartDocs AI Backend API.

This module provides request/response models and validation schemas
for all API endpoints in the SmartDocs AI application.
"""

from .schemas import (
    # Request models
    AskRequest,
    
    # Response models
    AskResponse,
    UploadResponse,
    HealthResponse,
    ErrorResponse,
    
    # Metadata models
    DocumentInfo,
    VectorStoreInfo,
    ProcessingStatus,
    
    # Status enums
    HealthStatus,
    DocumentStatus,
    ProcessingStage
)

__all__ = [
    # Request models
    "AskRequest",
    
    # Response models  
    "AskResponse",
    "UploadResponse",
    "HealthResponse",
    "ErrorResponse",
    
    # Metadata models
    "DocumentInfo",
    "VectorStoreInfo", 
    "ProcessingStatus",
    
    # Status enums
    "HealthStatus",
    "DocumentStatus",
    "ProcessingStage"
]