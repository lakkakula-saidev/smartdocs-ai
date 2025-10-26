"""
Vector store abstraction layer for SmartDocs AI Backend.

This module provides a unified interface for vector store operations
supporting multiple providers (ChromaDB, Pinecone) with a consistent API.

Key components:
- VectorStoreInterface: Abstract base class for vector operations
- ChromaVectorStore: ChromaDB implementation
- PineconeVectorStore: Pinecone implementation 
- DocumentRegistry: Session management for document-based operations
- VectorStoreFactory: Provider-agnostic vector store creation
"""

import os
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime

from ..config import Settings, VectorStoreProvider, get_settings
from ..exceptions import (
    VectorStoreError,
    DocumentNotFoundError,
    ConfigurationError,
    DocumentProcessingError,
    ExceptionContext
)
from ..logger import get_logger
from ..models.schemas import VectorStoreInfo, DocumentInfo, DocumentStatus

logger = get_logger("vector_store")


class VectorStoreInterface(ABC):
    """
    Abstract interface for vector store operations.
    
    Defines the contract that all vector store implementations must follow,
    enabling provider-agnostic vector operations throughout the application.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize vector store interface.
        
        Args:
            settings: Application settings instance
        """
        self.settings = settings
        self.logger = get_logger(f"vector_store.{self.__class__.__name__}")
    
    @abstractmethod
    async def create_collection(
        self, 
        document_id: str,
        documents: List[Any],
        embeddings: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new vector collection for a document.
        
        Args:
            document_id: Unique document identifier
            documents: List of document chunks (LangChain Document objects)
            embeddings: Embedding function/model instance
            metadata: Optional collection metadata
            
        Returns:
            Collection name or identifier
            
        Raises:
            VectorStoreError: If collection creation fails
        """
        pass
    
    @abstractmethod
    async def get_retriever(
        self,
        document_id: str,
        k: int = 4,
        **kwargs
    ) -> Any:
        """
        Get a retriever for semantic search.
        
        Args:
            document_id: Document identifier
            k: Number of chunks to retrieve
            **kwargs: Additional retriever parameters
            
        Returns:
            LangChain retriever instance
            
        Raises:
            DocumentNotFoundError: If document not found
            VectorStoreError: If retriever creation fails
        """
        pass
    
    @abstractmethod
    async def delete_collection(self, document_id: str) -> bool:
        """
        Delete a document collection.
        
        Args:
            document_id: Document identifier
            
        Returns:
            True if deletion successful
            
        Raises:
            VectorStoreError: If deletion fails
        """
        pass
    
    @abstractmethod
    async def get_collection_info(self, document_id: str) -> VectorStoreInfo:
        """
        Get information about a vector store collection.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Vector store information
            
        Raises:
            DocumentNotFoundError: If document not found
        """
        pass
    
    @abstractmethod
    async def list_collections(self) -> List[str]:
        """
        List all available collections.
        
        Returns:
            List of document IDs with collections
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Check vector store health and connectivity.
        
        Returns:
            Health status information
        """
        pass


class ChromaVectorStore(VectorStoreInterface):
    """
    ChromaDB implementation of vector store interface.
    
    Provides persistent vector storage using ChromaDB with filesystem
    persistence compatible with the existing main.py implementation.
    """
    
    def __init__(self, settings: Settings):
        """Initialize ChromaDB vector store."""
        super().__init__(settings)
        self._collections: Dict[str, Any] = {}
        self._ensure_chroma_available()
    
    def _ensure_chroma_available(self) -> None:
        """Ensure ChromaDB dependencies are available."""
        try:
            # Try modern package first
            from langchain_chroma import Chroma
            self._chroma_class = Chroma
        except ImportError:
            try:
                # Fallback to legacy path
                from langchain_community.vectorstores import Chroma
                self._chroma_class = Chroma
            except ImportError as e:
                raise ConfigurationError(
                    message="ChromaDB not available. Install with: pip install langchain-chroma",
                    error_code="CHROMA_NOT_AVAILABLE",
                    details={"package": "langchain-chroma"}
                ) from e
    
    def _get_persist_directory(self, document_id: str) -> str:
        """Get persistence directory for document."""
        return str(self.settings.vector_store_path / document_id)
    
    def _get_collection_name(self, document_id: str) -> str:
        """Get collection name for document."""
        return f"doc_{document_id}"
    
    async def create_collection(
        self,
        document_id: str,
        documents: List[Any],
        embeddings: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create ChromaDB collection from documents."""
        collection_name = self._get_collection_name(document_id)
        persist_dir = self._get_persist_directory(document_id)
        
        with ExceptionContext(VectorStoreError, f"Failed to create ChromaDB collection for document {document_id}"):
            # Ensure directory exists
            Path(persist_dir).mkdir(parents=True, exist_ok=True)
            
            self.logger.info(
                f"Creating ChromaDB collection",
                extra={
                    "document_id": document_id,
                    "collection_name": collection_name,
                    "persist_dir": persist_dir,
                    "chunk_count": len(documents)
                }
            )
            
            # Create vector store from documents
            vectorstore = self._chroma_class.from_documents(
                documents,
                embedding=embeddings,
                collection_name=collection_name,
                persist_directory=persist_dir,
            )
            
            # Handle persistence (newer versions auto-persist)
            if hasattr(vectorstore, "persist"):
                vectorstore.persist()
            
            # Cache the collection
            self._collections[document_id] = {
                "vectorstore": vectorstore,
                "collection_name": collection_name,
                "persist_directory": persist_dir,
                "created_at": datetime.utcnow(),
                "chunk_count": len(documents)
            }
            
            self.logger.info(
                f"Successfully created ChromaDB collection",
                extra={
                    "document_id": document_id,
                    "collection_name": collection_name,
                    "embeddings_count": len(documents)
                }
            )
            
            return collection_name
    
    async def get_retriever(self, document_id: str, k: int = 4, **kwargs) -> Any:
        """Get ChromaDB retriever for document."""
        if document_id not in self._collections:
            # Try to load from persistence
            await self._load_collection(document_id)
        
        if document_id not in self._collections:
            raise DocumentNotFoundError(document_id)
        
        vectorstore = self._collections[document_id]["vectorstore"]
        return vectorstore.as_retriever(search_kwargs={"k": k, **kwargs})
    
    async def _load_collection(self, document_id: str) -> None:
        """Load collection from persistent storage."""
        collection_name = self._get_collection_name(document_id)
        persist_dir = self._get_persist_directory(document_id)
        
        if not Path(persist_dir).exists():
            return
        
        with ExceptionContext(VectorStoreError, f"Failed to load ChromaDB collection for document {document_id}"):
            # Load embeddings (would need to be passed or configured)
            from ..config import get_settings
            
            try:
                from langchain_openai import OpenAIEmbeddings
            except ImportError:
                from langchain.embeddings.openai import OpenAIEmbeddings
            
            settings = get_settings()
            if not settings.has_openai_key:
                raise VectorStoreError(
                    message="OpenAI API key not configured for loading collection",
                    error_code="OPENAI_API_KEY_MISSING"
                )
            
            embeddings = OpenAIEmbeddings(openai_api_key=settings.openai_api_key)
            
            # Load existing collection
            vectorstore = self._chroma_class(
                collection_name=collection_name,
                embedding_function=embeddings,
                persist_directory=persist_dir,
            )
            
            # Get chunk count
            try:
                chunk_count = len(vectorstore._collection.get()["ids"])
            except Exception:
                chunk_count = 0
            
            self._collections[document_id] = {
                "vectorstore": vectorstore,
                "collection_name": collection_name,
                "persist_directory": persist_dir,
                "loaded_at": datetime.utcnow(),
                "chunk_count": chunk_count
            }
            
            self.logger.info(
                f"Loaded ChromaDB collection from persistence",
                extra={
                    "document_id": document_id,
                    "collection_name": collection_name,
                    "chunk_count": chunk_count
                }
            )
    
    async def delete_collection(self, document_id: str) -> bool:
        """Delete ChromaDB collection."""
        with ExceptionContext(VectorStoreError, f"Failed to delete ChromaDB collection for document {document_id}"):
            # Remove from memory
            if document_id in self._collections:
                del self._collections[document_id]
            
            # Remove persistent storage
            persist_dir = Path(self._get_persist_directory(document_id))
            if persist_dir.exists():
                import shutil
                shutil.rmtree(persist_dir)
                
            self.logger.info(f"Deleted ChromaDB collection for document {document_id}")
            return True
    
    async def get_collection_info(self, document_id: str) -> VectorStoreInfo:
        """Get ChromaDB collection information."""
        if document_id not in self._collections:
            await self._load_collection(document_id)
        
        if document_id not in self._collections:
            raise DocumentNotFoundError(document_id)
        
        collection_data = self._collections[document_id]
        persist_dir = self._get_persist_directory(document_id)
        
        return VectorStoreInfo(
            document_id=document_id,
            collection_name=collection_data["collection_name"],
            persist_directory=persist_dir,
            embedding_count=collection_data["chunk_count"],
            embedding_model="text-embedding-ada-002",  # Default OpenAI model
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
            is_accessible=Path(persist_dir).exists()
        )
    
    async def list_collections(self) -> List[str]:
        """List all ChromaDB collections."""
        collections = list(self._collections.keys())
        
        # Also scan persistence directory for additional collections
        persist_base = self.settings.vector_store_path
        if persist_base.exists():
            for item in persist_base.iterdir():
                if item.is_dir() and item.name not in collections:
                    # Check if it looks like a valid document ID (32-char hex)
                    if len(item.name) == 32 and all(c in '0123456789abcdef' for c in item.name):
                        collections.append(item.name)
        
        return collections
    
    async def health_check(self) -> Dict[str, Any]:
        """Check ChromaDB health."""
        try:
            # Try to create a test collection
            test_persist_dir = self.settings.vector_store_path / "_health_check"
            test_persist_dir.mkdir(exist_ok=True)
            
            return {
                "status": "healthy",
                "provider": "chroma",
                "collections_loaded": len(self._collections),
                "persist_directory": str(self.settings.vector_store_path),
                "persist_directory_exists": self.settings.vector_store_path.exists()
            }
        except Exception as e:
            self.logger.error(f"ChromaDB health check failed: {e}")
            return {
                "status": "unhealthy",
                "provider": "chroma", 
                "error": str(e)
            }


class PineconeVectorStore(VectorStoreInterface):
    """
    Pinecone implementation of vector store interface.
    
    Provides cloud-based vector storage using Pinecone with proper
    configuration and error handling.
    """
    
    def __init__(self, settings: Settings):
        """Initialize Pinecone vector store."""
        super().__init__(settings)
        self._collections: Dict[str, str] = {}  # document_id -> namespace mapping
        self._ensure_pinecone_available()
        self._initialize_pinecone()
    
    def _ensure_pinecone_available(self) -> None:
        """Ensure Pinecone dependencies are available."""
        try:
            import pinecone
            from langchain_pinecone import PineconeVectorStore as LangChainPinecone
            self._pinecone = pinecone
            self._langchain_pinecone = LangChainPinecone
        except ImportError as e:
            raise ConfigurationError(
                message="Pinecone not available. Install with: pip install langchain-pinecone pinecone-client",
                error_code="PINECONE_NOT_AVAILABLE",
                details={"packages": ["langchain-pinecone", "pinecone-client"]}
            ) from e
    
    def _initialize_pinecone(self) -> None:
        """Initialize Pinecone client."""
        if not self.settings.pinecone_api_key:
            raise ConfigurationError(
                message="Pinecone API key not configured",
                error_code="PINECONE_API_KEY_MISSING",
                details={"required_env": "PINECONE_API_KEY"}
            )
        
        if not self.settings.pinecone_environment:
            raise ConfigurationError(
                message="Pinecone environment not configured", 
                error_code="PINECONE_ENVIRONMENT_MISSING",
                details={"required_env": "PINECONE_ENVIRONMENT"}
            )
        
        with ExceptionContext(ConfigurationError, "Failed to initialize Pinecone client"):
            self._pinecone.init(
                api_key=self.settings.pinecone_api_key,
                environment=self.settings.pinecone_environment
            )
            
            # Verify index exists
            if self.settings.pinecone_index_name not in self._pinecone.list_indexes():
                raise ConfigurationError(
                    message=f"Pinecone index '{self.settings.pinecone_index_name}' not found",
                    error_code="PINECONE_INDEX_NOT_FOUND",
                    details={"index_name": self.settings.pinecone_index_name}
                )
    
    async def create_collection(
        self,
        document_id: str,
        documents: List[Any],
        embeddings: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create Pinecone namespace for document."""
        namespace = f"doc_{document_id}"
        
        with ExceptionContext(VectorStoreError, f"Failed to create Pinecone collection for document {document_id}"):
            self.logger.info(
                f"Creating Pinecone collection",
                extra={
                    "document_id": document_id,
                    "namespace": namespace,
                    "index_name": self.settings.pinecone_index_name,
                    "chunk_count": len(documents)
                }
            )
            
            # Create vector store with namespace
            vectorstore = self._langchain_pinecone.from_documents(
                documents,
                embeddings,
                index_name=self.settings.pinecone_index_name,
                namespace=namespace
            )
            
            # Cache the namespace mapping
            self._collections[document_id] = namespace
            
            self.logger.info(
                f"Successfully created Pinecone collection",
                extra={
                    "document_id": document_id,
                    "namespace": namespace,
                    "embeddings_count": len(documents)
                }
            )
            
            return namespace
    
    async def get_retriever(self, document_id: str, k: int = 4, **kwargs) -> Any:
        """Get Pinecone retriever for document."""
        if document_id not in self._collections:
            raise DocumentNotFoundError(document_id)
        
        namespace = self._collections[document_id]
        
        with ExceptionContext(VectorStoreError, f"Failed to create Pinecone retriever for document {document_id}"):
            # Create embeddings instance
            from ..config import require_openai_api_key
            
            try:
                from langchain_openai import OpenAIEmbeddings
            except ImportError:
                from langchain.embeddings.openai import OpenAIEmbeddings
            
            api_key = require_openai_api_key()
            embeddings = OpenAIEmbeddings(openai_api_key=api_key)
            
            # Create vector store instance
            vectorstore = self._langchain_pinecone(
                index_name=self.settings.pinecone_index_name,
                embedding=embeddings,
                namespace=namespace
            )
            
            return vectorstore.as_retriever(search_kwargs={"k": k, **kwargs})
    
    async def delete_collection(self, document_id: str) -> bool:
        """Delete Pinecone namespace."""
        if document_id not in self._collections:
            return False
        
        namespace = self._collections[document_id]
        
        with ExceptionContext(VectorStoreError, f"Failed to delete Pinecone collection for document {document_id}"):
            # Delete all vectors in namespace
            index = self._pinecone.Index(self.settings.pinecone_index_name)
            index.delete(delete_all=True, namespace=namespace)
            
            # Remove from cache
            del self._collections[document_id]
            
            self.logger.info(f"Deleted Pinecone collection for document {document_id}")
            return True
    
    async def get_collection_info(self, document_id: str) -> VectorStoreInfo:
        """Get Pinecone collection information."""
        if document_id not in self._collections:
            raise DocumentNotFoundError(document_id)
        
        namespace = self._collections[document_id]
        
        # Get stats from Pinecone index
        try:
            index = self._pinecone.Index(self.settings.pinecone_index_name)
            stats = index.describe_index_stats()
            namespace_stats = stats.get("namespaces", {}).get(namespace, {})
            vector_count = namespace_stats.get("vector_count", 0)
        except Exception:
            vector_count = 0
        
        return VectorStoreInfo(
            document_id=document_id,
            collection_name=namespace,
            persist_directory=f"pinecone://{self.settings.pinecone_index_name}/{namespace}",
            embedding_count=vector_count,
            embedding_model="text-embedding-ada-002",
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
            is_accessible=True
        )
    
    async def list_collections(self) -> List[str]:
        """List all Pinecone collections (namespaces)."""
        try:
            index = self._pinecone.Index(self.settings.pinecone_index_name)
            stats = index.describe_index_stats()
            namespaces = list(stats.get("namespaces", {}).keys())
            
            # Extract document IDs from namespaces (remove "doc_" prefix)
            document_ids = []
            for ns in namespaces:
                if ns.startswith("doc_") and len(ns) == 36:  # "doc_" + 32-char hex
                    document_ids.append(ns[4:])
            
            return document_ids
        except Exception as e:
            self.logger.error(f"Failed to list Pinecone collections: {e}")
            return list(self._collections.keys())
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Pinecone health."""
        try:
            index = self._pinecone.Index(self.settings.pinecone_index_name)
            stats = index.describe_index_stats()
            
            return {
                "status": "healthy",
                "provider": "pinecone",
                "index_name": self.settings.pinecone_index_name,
                "total_vector_count": stats.get("total_vector_count", 0),
                "namespaces": len(stats.get("namespaces", {}))
            }
        except Exception as e:
            self.logger.error(f"Pinecone health check failed: {e}")
            return {
                "status": "unhealthy",
                "provider": "pinecone",
                "error": str(e)
            }


class DocumentRegistry:
    """
    Document registry for managing vector store sessions and metadata.
    
    Provides centralized management of document-to-vector-store mappings
    with persistent storage and session management capabilities.
    """
    
    def __init__(self, vector_store: VectorStoreInterface):
        """
        Initialize document registry.
        
        Args:
            vector_store: Vector store implementation instance
        """
        self.vector_store = vector_store
        self.logger = get_logger("document_registry")
        self._documents: Dict[str, DocumentInfo] = {}
        self._last_document_id: Optional[str] = None
    
    async def register_document(
        self,
        document_id: str,
        filename: Optional[str] = None,
        file_size_bytes: Optional[int] = None,
        text_size_bytes: int = 0,
        chunk_count: int = 0,
        processing_time_ms: Optional[int] = None
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
            
        Returns:
            Document information object
        """
        collection_name = f"doc_{document_id}"
        
        doc_info = DocumentInfo(
            document_id=document_id,
            filename=filename,
            file_size_bytes=file_size_bytes,
            text_size_bytes=text_size_bytes,
            chunk_count=chunk_count,
            status=DocumentStatus.READY,
            collection_name=collection_name,
            processing_time_ms=processing_time_ms,
            created_at=datetime.utcnow()
        )
        
        self._documents[document_id] = doc_info
        self._last_document_id = document_id
        
        self.logger.info(
            f"Registered document",
            extra={
                "document_id": document_id,
                "uploaded_filename": filename,
                "chunk_count": chunk_count
            }
        )
        
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
            # Try to discover from vector store
            collections = await self.vector_store.list_collections()
            if document_id in collections:
                # Create minimal document info
                doc_info = DocumentInfo(
                    document_id=document_id,
                    text_size_bytes=0,
                    chunk_count=0,
                    status=DocumentStatus.READY,
                    collection_name=f"doc_{document_id}",
                    created_at=datetime.utcnow()
                )
                self._documents[document_id] = doc_info
                return doc_info
        
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
        # Delete from vector store
        deleted = await self.vector_store.delete_collection(document_id)
        
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
        
        self.logger.info(f"Deleted document {document_id}")
        return deleted
    
    async def get_retriever(
        self,
        document_id: Optional[str] = None,
        k: int = 4
    ) -> Any:
        """
        Get retriever for document.
        
        Args:
            document_id: Document identifier (uses last document if None)
            k: Number of chunks to retrieve
            
        Returns:
            LangChain retriever instance
            
        Raises:
            DocumentNotFoundError: If no documents available
        """
        if document_id is None:
            document_id = self._last_document_id
        
        if document_id is None:
            raise DocumentNotFoundError("No documents have been uploaded yet")
        
        return await self.vector_store.get_retriever(document_id, k=k)
    
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
        Get registry health information.
        
        Returns:
            Health status dictionary
        """
        vector_health = await self.vector_store.health_check()
        
        return {
            "registry_status": "healthy",
            "document_count": self.document_count,
            "last_document_id": self.last_document_id,
            "vector_store": vector_health
        }


class VectorStoreFactory:
    """
    Factory for creating vector store instances based on configuration.
    
    Provides a centralized way to create vector store implementations
    based on the configured provider and settings.
    """
    
    @staticmethod
    def create_vector_store(settings: Settings) -> VectorStoreInterface:
        """
        Create vector store instance based on settings.
        
        Args:
            settings: Application settings
            
        Returns:
            Vector store implementation instance
            
        Raises:
            ConfigurationError: If provider not supported
        """
        logger = get_logger("vector_store_factory")
        
        if settings.vector_store_provider == VectorStoreProvider.CHROMA:
            logger.info("Creating ChromaDB vector store")
            return ChromaVectorStore(settings)
        
        elif settings.vector_store_provider == VectorStoreProvider.PINECONE:
            logger.info("Creating Pinecone vector store")
            return PineconeVectorStore(settings)
        
        else:
            raise ConfigurationError(
                message=f"Unsupported vector store provider: {settings.vector_store_provider}",
                error_code="UNSUPPORTED_PROVIDER",
                details={
                    "provider": settings.vector_store_provider,
                    "supported_providers": [p.value for p in VectorStoreProvider]
                }
            )


# Global instances
_vector_store: Optional[VectorStoreInterface] = None
_document_registry: Optional[DocumentRegistry] = None


def get_vector_store() -> VectorStoreInterface:
    """
    Get global vector store instance.
    
    Returns:
        Vector store implementation instance
    """
    global _vector_store
    if _vector_store is None:
        settings = get_settings()
        _vector_store = VectorStoreFactory.create_vector_store(settings)
    return _vector_store


def get_document_registry() -> DocumentRegistry:
    """
    Get global document registry instance.
    
    Returns:
        Document registry instance
    """
    global _document_registry
    if _document_registry is None:
        vector_store = get_vector_store()
        _document_registry = DocumentRegistry(vector_store)
    return _document_registry


# Convenience functions
async def create_vector_store(
    document_id: str,
    documents: List[Any],
    embeddings: Any,
    filename: Optional[str] = None,
    file_size_bytes: Optional[int] = None,
    text_size_bytes: int = 0,
    processing_time_ms: Optional[int] = None
) -> str:
    """
    Create vector store collection and register document.
    
    Args:
        document_id: Document identifier
        documents: Document chunks
        embeddings: Embedding function
        filename: Original filename
        file_size_bytes: Original file size
        text_size_bytes: Extracted text size
        processing_time_ms: Processing time
        
    Returns:
        Collection name
    """
    registry = get_document_registry()
    
    # Create collection
    collection_name = await registry.vector_store.create_collection(
        document_id, documents, embeddings
    )
    
    # Register document
    await registry.register_document(
        document_id=document_id,
        filename=filename,
        file_size_bytes=file_size_bytes,
        text_size_bytes=text_size_bytes,
        chunk_count=len(documents),
        processing_time_ms=processing_time_ms
    )
    
    return collection_name


async def get_vector_store_for_document(document_id: str) -> VectorStoreInterface:
    """
    Get vector store instance for a specific document.
    
    Args:
        document_id: Document identifier
        
    Returns:
        Vector store instance
        
    Raises:
        DocumentNotFoundError: If document not found
    """
    registry = get_document_registry()
    await registry.get_document(document_id)  # Validates document exists
    return registry.vector_store