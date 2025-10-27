"""
SmartDocs AI - Modular AI Integration Package.

This package provides direct OpenAI integration with modular components:
- client: OpenAI API client with error handling
- chunking: Text chunking utilities
- rag: Retrieval-Augmented Generation pipeline
- exceptions: Common exceptions and data classes

Maintains backward compatibility with the original ai.py interface.
"""

from typing import List, Dict, Any, Optional

from config import get_settings
from .exceptions import (
    AIServiceError,
    ConfigurationError,
    TextChunk,
    EmbeddingResult,
    ChatResponse,
    get_logger
)
from .client import DirectOpenAIClient
from .chunking import TextChunker
from .rag import RAGPipeline


# Global instances for singleton pattern (backward compatibility)
_openai_client: Optional[DirectOpenAIClient] = None
_text_chunker: Optional[TextChunker] = None
_rag_pipeline: Optional[RAGPipeline] = None


def get_openai_client() -> DirectOpenAIClient:
    """Get global OpenAI client instance."""
    global _openai_client
    if _openai_client is None:
        _openai_client = DirectOpenAIClient()
    return _openai_client


def get_text_chunker() -> TextChunker:
    """Get global text chunker instance."""
    global _text_chunker
    if _text_chunker is None:
        settings = get_settings()
        _text_chunker = TextChunker(
            chunk_size=getattr(settings, 'chunk_size', 1000),
            chunk_overlap=getattr(settings, 'chunk_overlap', 150)
        )
    return _text_chunker


def get_rag_pipeline() -> RAGPipeline:
    """Get global RAG pipeline instance."""
    global _rag_pipeline
    if _rag_pipeline is None:
        client = get_openai_client()
        _rag_pipeline = RAGPipeline(client)
    return _rag_pipeline


# Convenience functions for common operations (backward compatibility)
async def embed_texts(texts: List[str]) -> EmbeddingResult:
    """Generate embeddings for texts."""
    client = get_openai_client()
    return await client.generate_embeddings(texts)


def chunk_text(text: str, metadata: Optional[Dict[str, Any]] = None) -> List[TextChunk]:
    """Chunk text into smaller pieces."""
    chunker = get_text_chunker()
    return chunker.chunk_text(text, metadata)


async def generate_rag_response(
    query: str,
    retrieved_chunks: List[Any],
    document_id: Optional[str] = None
) -> str:
    """Generate RAG response for query and chunks."""
    pipeline = get_rag_pipeline()
    return await pipeline.generate_response(query, retrieved_chunks, document_id)


async def health_check() -> Dict[str, Any]:
    """
    Perform health check on all AI components.
    
    Returns:
        Health status dictionary
    """
    results = {
        "status": "healthy",
        "components": {}
    }
    
    try:
        # Test OpenAI client
        client = get_openai_client()
        test_embedding = await client.generate_embeddings(["test"])
        results["components"]["openai_client"] = {
            "status": "healthy",
            "embedding_model": client.embedding_model,
            "chat_model": client.chat_model
        }
    except Exception as e:
        results["status"] = "unhealthy"
        results["components"]["openai_client"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    try:
        # Test text chunker
        chunker = get_text_chunker()
        test_chunks = chunker.chunk_text("This is a test text for chunking.")
        results["components"]["text_chunker"] = {
            "status": "healthy",
            "chunk_size": chunker.chunk_size,
            "chunk_overlap": chunker.chunk_overlap
        }
    except Exception as e:
        results["status"] = "unhealthy"
        results["components"]["text_chunker"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    return results


# Export all public interfaces
__all__ = [
    # Classes
    "DirectOpenAIClient",
    "TextChunker", 
    "RAGPipeline",
    
    # Data classes
    "TextChunk",
    "EmbeddingResult",
    "ChatResponse",
    
    # Exceptions
    "AIServiceError",
    "ConfigurationError",
    
    # Factory functions
    "get_openai_client",
    "get_text_chunker",
    "get_rag_pipeline",
    
    # Convenience functions
    "embed_texts",
    "chunk_text",
    "generate_rag_response",
    "health_check",
    
    # Utilities
    "get_logger"
]