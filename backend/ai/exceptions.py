"""
AI-related exceptions and common utilities.
"""

import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass


def get_logger(name: str):
    """Get a logger instance."""
    return logging.getLogger(name)


class AIServiceError(Exception):
    """Base exception for AI service errors."""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


class ConfigurationError(Exception):
    """Exception for configuration-related errors."""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


@dataclass
class TextChunk:
    """Simple text chunk representation."""
    content: str
    metadata: Dict[str, Any]
    chunk_id: Optional[str] = None


@dataclass
class EmbeddingResult:
    """Embedding generation result."""
    embeddings: list[list[float]]
    token_count: int
    model: str


@dataclass
class ChatResponse:
    """Chat completion response."""
    content: str
    model: str
    usage: Dict[str, int]
    processing_time_ms: int