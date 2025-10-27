"""
Unified Storage Module for SmartDocs AI Backend.

This module combines document registry and vector storage functionality
using direct ChromaDB integration without complex abstractions.
"""

import os
import uuid
import shutil
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

import chromadb
from chromadb.config import Settings as ChromaSettings

from config import get_settings
from models import DocumentInfo, DocumentStatus
from ai import get_openai_client, embed_texts, chunk_text


class DocumentNotFoundError(Exception):
    """Raised when a document is not found."""
    
    def __init__(self, document_id: str):
        self.document_id = document_id
        super().__init__(f"Document with ID '{document_id}' not found")


class VectorStoreError(Exception):
    """Raised when vector store operations fail."""
    pass


class UnifiedStorage:
    """
    Unified storage system combining document registry and vector operations.
    
    Uses direct ChromaDB integration for vector storage and in-memory registry
    for document metadata with optional persistence.
    """
    
    def __init__(self):
        """Initialize unified storage system."""
        self.settings = get_settings()
        self._documents: Dict[str, DocumentInfo] = {}
        self._last_document_id: Optional[str] = None
        
        # Initialize ChromaDB client
        self._init_chromadb()
        
        print(f"[storage] Initialized unified storage with ChromaDB at {self.settings.vector_store_path}")
    
    def _init_chromadb(self):
        """Initialize ChromaDB client with persistent storage."""
        try:
            # Ensure storage directory exists
            self.settings.create_vector_store_dir()
            
            # Initialize ChromaDB with persistent storage
            self.chroma_client = chromadb.PersistentClient(
                path=str(self.settings.vector_store_path),
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            print(f"[storage] ChromaDB client initialized successfully")
            
        except Exception as e:
            print(f"[storage] ERROR: Failed to initialize ChromaDB: {e}")
            raise VectorStoreError(f"Failed to initialize ChromaDB: {e}") from e
    
    def _get_collection_name(self, document_id: str) -> str:
        """Get collection name for document."""
        return f"doc_{document_id}"
    
    async def create_document_collection(
        self,
        document_id: str,
        text_chunks: List[str],
        metadata_list: List[Dict[str, Any]],
        filename: Optional[str] = None
    ) -> str:
        """
        Create a new document collection with embeddings.
        
        Args:
            document_id: Unique document identifier
            text_chunks: List of text chunks to embed
            metadata_list: List of metadata for each chunk
            filename: Original filename for logging
            
        Returns:
            Collection name
            
        Raises:
            VectorStoreError: If collection creation fails
        """
        collection_name = self._get_collection_name(document_id)
        
        try:
            print(f"[storage] Creating collection '{collection_name}' for document {document_id}")
            
            # Generate embeddings for all chunks
            openai_client = get_openai_client()
            embedding_result = await openai_client.generate_embeddings(text_chunks)
            
            if not embedding_result.embeddings:
                raise VectorStoreError("No embeddings generated for text chunks")
            
            # Create or get collection
            collection = self.chroma_client.get_or_create_collection(
                name=collection_name,
                metadata={"document_id": document_id, "filename": filename or ""}
            )
            
            # Prepare documents for ChromaDB
            chunk_ids = [f"{document_id}_chunk_{i}" for i in range(len(text_chunks))]
            
            # Add documents to collection
            collection.add(
                embeddings=embedding_result.embeddings,
                documents=text_chunks,
                metadatas=metadata_list,
                ids=chunk_ids
            )
            
            print(f"[storage] Successfully created collection with {len(text_chunks)} chunks")
            
            return collection_name
            
        except Exception as e:
            print(f"[storage] ERROR: Failed to create collection: {e}")
            raise VectorStoreError(f"Failed to create collection for document {document_id}: {e}") from e
    
    async def query_document(
        self,
        document_id: str,
        query: str,
        k: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Query document collection for relevant chunks.
        
        Args:
            document_id: Document identifier
            query: Search query
            k: Number of results to return
            
        Returns:
            List of relevant chunks with metadata
            
        Raises:
            DocumentNotFoundError: If document not found
            VectorStoreError: If query fails
        """
        collection_name = self._get_collection_name(document_id)
        
        try:
            # Check if document exists
            if document_id not in self._documents:
                raise DocumentNotFoundError(document_id)
            
            # Get collection
            collection = self.chroma_client.get_collection(collection_name)
            
            # Generate query embedding
            openai_client = get_openai_client()
            query_embedding_result = await openai_client.generate_embeddings([query])
            
            if not query_embedding_result.embeddings:
                raise VectorStoreError("Failed to generate query embedding")
            
            # Query collection
            results = collection.query(
                query_embeddings=query_embedding_result.embeddings,
                n_results=k,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            chunks = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    chunk = {
                        'content': doc,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else 0.0
                    }
                    chunks.append(chunk)
            
            print(f"[storage] Retrieved {len(chunks)} relevant chunks for query")
            
            return chunks
            
        except DocumentNotFoundError:
            raise
        except Exception as e:
            print(f"[storage] ERROR: Failed to query document: {e}")
            raise VectorStoreError(f"Failed to query document {document_id}: {e}") from e
    
    async def register_document(
        self,
        document_id: str,
        filename: Optional[str] = None,
        file_size_bytes: Optional[int] = None,
        text_size_bytes: int = 0,
        chunk_count: int = 0,
        processing_time_ms: Optional[int] = None,
        display_name: Optional[str] = None
    ) -> DocumentInfo:
        """
        Register a new document in the registry.
        
        Args:
            document_id: Unique document identifier
            filename: Original filename
            file_size_bytes: Original file size
            text_size_bytes: Extracted text size
            chunk_count: Number of text chunks
            processing_time_ms: Processing time
            display_name: Cleaned filename for display
            
        Returns:
            Document information object
        """
        collection_name = self._get_collection_name(document_id)
        
        doc_info = DocumentInfo(
            document_id=document_id,
            filename=filename,
            file_size_bytes=file_size_bytes,
            text_size_bytes=text_size_bytes,
            chunk_count=chunk_count,
            status=DocumentStatus.READY,
            collection_name=collection_name,
            processing_time_ms=processing_time_ms,
            created_at=datetime.utcnow(),
            display_name=display_name
        )
        
        self._documents[document_id] = doc_info
        self._last_document_id = document_id
        
        print(f"[storage] Registered document {document_id} with {chunk_count} chunks")
        
        return doc_info
    
    async def get_document(self, document_id: str) -> DocumentInfo:
        """
        Get document information.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Document information
            
        Raises:
            DocumentNotFoundError: If document not found
        """
        if document_id not in self._documents:
            # Try to discover from ChromaDB collections
            collection_name = self._get_collection_name(document_id)
            try:
                collection = self.chroma_client.get_collection(collection_name)
                # Create minimal document info if found in ChromaDB but not in registry
                doc_info = DocumentInfo(
                    document_id=document_id,
                    text_size_bytes=0,
                    chunk_count=0,
                    status=DocumentStatus.READY,
                    collection_name=collection_name,
                    created_at=datetime.utcnow()
                )
                self._documents[document_id] = doc_info
                return doc_info
            except Exception:
                pass
        
        if document_id not in self._documents:
            raise DocumentNotFoundError(document_id)
        
        return self._documents[document_id]
    
    async def list_documents(self) -> List[DocumentInfo]:
        """
        List all registered documents.
        
        Returns:
            List of document information objects
        """
        return list(self._documents.values())
    
    async def delete_document(self, document_id: str) -> bool:
        """
        Delete document from registry and vector store.
        
        Args:
            document_id: Document identifier
            
        Returns:
            True if deletion successful
        """
        collection_name = self._get_collection_name(document_id)
        
        try:
            # Delete from ChromaDB
            try:
                self.chroma_client.delete_collection(collection_name)
                print(f"[storage] Deleted ChromaDB collection {collection_name}")
            except Exception as e:
                print(f"[storage] WARNING: Failed to delete ChromaDB collection: {e}")
            
            # Remove from registry
            if document_id in self._documents:
                del self._documents[document_id]
            
            # Update last document ID
            if self._last_document_id == document_id:
                self._last_document_id = None
                if self._documents:
                    # Set to most recent document
                    self._last_document_id = max(
                        self._documents.keys(),
                        key=lambda x: self._documents[x].created_at
                    )
            
            print(f"[storage] Deleted document {document_id}")
            return True
            
        except Exception as e:
            print(f"[storage] ERROR: Failed to delete document: {e}")
            raise VectorStoreError(f"Failed to delete document {document_id}: {e}") from e
    
    async def rename_document(self, document_id: str, new_display_name: str) -> DocumentInfo:
        """
        Rename document's display name.
        
        Args:
            document_id: Document identifier
            new_display_name: New display name for the document
            
        Returns:
            Updated document information
            
        Raises:
            DocumentNotFoundError: If document not found
        """
        if document_id not in self._documents:
            raise DocumentNotFoundError(document_id)
        
        # Get current document info
        doc_info = self._documents[document_id]
        old_display_name = doc_info.display_name or doc_info.get_display_name()
        
        # Update display name
        doc_info.display_name = new_display_name
        
        print(f"[storage] Renamed document {document_id}: '{old_display_name}' -> '{new_display_name}'")
        
        return doc_info
    
    @property
    def last_document_id(self) -> Optional[str]:
        """Get the ID of the last uploaded document."""
        return self._last_document_id
    
    @property
    def document_count(self) -> int:
        """Get total number of registered documents."""
        return len(self._documents)
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Get storage system health information.
        
        Returns:
            Health status dictionary
        """
        try:
            # Test ChromaDB connectivity
            collections = self.chroma_client.list_collections()
            
            return {
                "status": "healthy",
                "document_count": self.document_count,
                "last_document_id": self.last_document_id,
                "chromadb_collections": len(collections),
                "storage_path": str(self.settings.vector_store_path),
                "storage_path_exists": self.settings.vector_store_path.exists()
            }
            
        except Exception as e:
            print(f"[storage] ERROR: Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "document_count": self.document_count,
                "last_document_id": self.last_document_id
            }


# Global instances
_unified_storage: Optional[UnifiedStorage] = None


def get_unified_storage() -> UnifiedStorage:
    """
    Get global unified storage instance.
    
    Returns:
        Unified storage instance
    """
    global _unified_storage
    if _unified_storage is None:
        _unified_storage = UnifiedStorage()
    return _unified_storage


# Legacy compatibility functions for existing code
def get_document_registry():
    """Get document registry (compatibility function)."""
    return get_unified_storage()


def get_vector_store():
    """Get vector store (compatibility function)."""
    return get_unified_storage()


# Convenience functions for document processing
async def process_document_text(
    document_id: str,
    text: str,
    filename: Optional[str] = None,
    file_size_bytes: Optional[int] = None,
    processing_time_ms: Optional[int] = None
) -> DocumentInfo:
    """
    Process document text and store in unified storage.
    
    Args:
        document_id: Unique document identifier
        text: Extracted document text
        filename: Original filename
        file_size_bytes: Original file size
        processing_time_ms: Processing time
        
    Returns:
        Document information
    """
    storage = get_unified_storage()
    settings = get_settings()
    
    # Chunk the text
    text_chunks_obj = chunk_text(text, metadata={"document_id": document_id})
    text_chunks = [chunk.content for chunk in text_chunks_obj]
    metadata_list = [chunk.metadata for chunk in text_chunks_obj]
    
    # Create collection with embeddings
    collection_name = await storage.create_document_collection(
        document_id=document_id,
        text_chunks=text_chunks,
        metadata_list=metadata_list,
        filename=filename
    )
    
    # Clean filename for display
    display_name = None
    if filename:
        # Simple filename cleaning
        base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
        display_name = base_name.replace('_', ' ').replace('-', ' ').title()
    
    # Register document
    doc_info = await storage.register_document(
        document_id=document_id,
        filename=filename,
        file_size_bytes=file_size_bytes,
        text_size_bytes=len(text.encode('utf-8')),
        chunk_count=len(text_chunks),
        processing_time_ms=processing_time_ms,
        display_name=display_name
    )
    
    return doc_info


__all__ = [
    "UnifiedStorage",
    "DocumentNotFoundError", 
    "VectorStoreError",
    "get_unified_storage",
    "get_document_registry",
    "get_vector_store",
    "process_document_text"
]