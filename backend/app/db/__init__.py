"""
Database and vector store abstraction layer for SmartDocs AI Backend.

This module provides:
- Abstract interfaces for vector store operations
- Concrete implementations for ChromaDB and Pinecone
- Document registry management for session handling
- Factory pattern for vector store creation based on configuration

The abstraction layer enables:
- Provider-agnostic vector operations
- Easy switching between vector stores
- Consistent document management
- Backward compatibility with existing data
"""

from .vector_store import (
    # Abstract interfaces
    VectorStoreInterface,
    DocumentRegistry,
    
    # Concrete implementations
    ChromaVectorStore,
    PineconeVectorStore,
    
    # Factory and registry
    VectorStoreFactory,
    get_document_registry,
    get_vector_store,
    
    # Utility functions
    create_vector_store,
    get_vector_store_for_document,
)

__all__ = [
    # Abstract interfaces
    "VectorStoreInterface",
    "DocumentRegistry",
    
    # Concrete implementations
    "ChromaVectorStore",
    "PineconeVectorStore",
    
    # Factory and registry
    "VectorStoreFactory",
    "get_document_registry",
    "get_vector_store",
    
    # Utility functions
    "create_vector_store",
    "get_vector_store_for_document",
]