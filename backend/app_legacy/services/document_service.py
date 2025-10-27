"""
Document service for SmartDocs AI Backend.

This service handles document upload, processing, and metadata management.
It orchestrates PDF text extraction, document chunking, vector embedding
creation, and storage operations.
"""

import os
import uuid
import tempfile
import shutil
import time
from typing import Optional, Dict, Any, List

from fastapi import UploadFile

from ..config import Settings, get_settings
from ..exceptions import (
    DocumentProcessingError,
    FileProcessingError,
    VectorStoreError,
    ExceptionContext
)
from ..logger import get_logger
from ..models.schemas import (
    UploadResponse,
    DocumentInfo,
    FileValidationInfo,
    DocumentStatus
)
from ..db.vector_store import get_document_registry, DocumentRegistry
from ..utils.validation import sanitize_filename
from ..utils.file_utils import extract_pdf_text, validate_file_upload, cleanup_temp_file
from ..utils.text_processing import split_text_into_chunks


class DocumentService:
    """
    Service for document processing and management operations.
    
    Handles the complete document processing pipeline from upload to
    vector storage, with proper error handling and metadata tracking.
    """
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        document_registry: Optional[DocumentRegistry] = None
    ):
        """
        Initialize document service.
        
        Args:
            settings: Application settings (uses global if None)
            document_registry: Document registry instance (uses global if None)
        """
        self.settings = settings or get_settings()
        self.document_registry = document_registry or get_document_registry()
        self.logger = get_logger("document_service")
    
    async def validate_upload(self, file: UploadFile) -> FileValidationInfo:
        """
        Validate uploaded file before processing.
        
        Args:
            file: Uploaded file to validate
            
        Returns:
            File validation information
            
        Raises:
            FileProcessingError: If file validation fails
        """
        self.logger.info(
            f"Validating file upload",
            extra={
                "uploaded_filename": file.filename,
                "content_type": file.content_type,
                "size": getattr(file, 'size', None)
            }
        )
        
        with ExceptionContext(FileProcessingError, "File validation failed"):
            # Use the existing validate_file_upload function
            validate_file_upload(file)
            
            # Create validation info object
            validation_info = FileValidationInfo(
                filename=file.filename or "unknown",
                content_type=file.content_type,
                file_size_bytes=getattr(file, 'size', 0) or 0,
                is_valid=True,
                validation_errors=[]
            )
            
            self.logger.info(f"File validation passed for {file.filename}")
            return validation_info
    
    async def process_upload(self, file: UploadFile) -> UploadResponse:
        """
        Process uploaded PDF document through the complete pipeline.
        
        Args:
            file: Uploaded PDF file
            
        Returns:
            Upload response with document metadata including extracted title
            
        Raises:
            DocumentProcessingError: If any processing step fails
        """
        start_time = time.time()
        document_id = uuid.uuid4().hex
        temp_path = None
        
        self.logger.info(
            f"Starting document processing",
            extra={
                "document_id": document_id,
                "uploaded_filename": file.filename,
                "content_type": file.content_type
            }
        )
        
        try:
            # Step 1: Validate file
            validation_info = await self.validate_upload(file)
            
            # Step 2: Create temporary file
            temp_path = await self._save_uploaded_file(file, document_id)
            
            # Step 3: Extract text from PDF
            extracted_text = await self._extract_text(temp_path, document_id)
            
            # Step 3.5: Create display name from filename (simplified approach)
            display_name = self._clean_filename_for_display(file.filename)
            
            # Step 4: Create document chunks
            documents = await self._create_chunks(extracted_text, document_id)
            
            # Step 5: Create embeddings and store in vector database
            collection_name = await self._store_embeddings(
                document_id, documents, file.filename
            )
            
            # Step 6: Register document metadata (with display name)
            processing_time_ms = int((time.time() - start_time) * 1000)
            doc_info = await self.document_registry.register_document(
                document_id=document_id,
                filename=file.filename,
                file_size_bytes=validation_info.file_size_bytes,
                text_size_bytes=len(extracted_text.encode('utf-8')),
                chunk_count=len(documents),
                processing_time_ms=processing_time_ms,
                display_name=display_name
            )
            
            self.logger.info(
                f"Document processing completed successfully",
                extra={
                    "document_id": document_id,
                    "uploaded_filename": file.filename,
                    "chunk_count": len(documents),
                    "processing_time_ms": processing_time_ms,
                    "display_name": display_name
                }
            )
            
            return UploadResponse(
                document_id=document_id,
                chunks=len(documents),
                bytes=len(extracted_text.encode('utf-8')),
                filename=file.filename,
                processing_time_ms=processing_time_ms,
                display_name=display_name
            )
            
        except Exception as e:
            self.logger.error(
                f"Document processing failed",
                extra={
                    "document_id": document_id,
                    "uploaded_filename": file.filename,
                    "error": str(e)
                },
                exc_info=True
            )
            raise
            
        finally:
            # Always cleanup temporary file
            if temp_path:
                # Extract directory from temp_path for cleanup
                temp_dir = os.path.dirname(temp_path)
                cleanup_temp_file(temp_dir)
    
    async def get_document(self, document_id: str) -> DocumentInfo:
        """
        Get document information by ID.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Document information
            
        Raises:
            DocumentNotFoundError: If document not found
        """
        self.logger.debug(f"Retrieving document info", extra={"document_id": document_id})
        return await self.document_registry.get_document(document_id)
    
    async def list_documents(self) -> List[DocumentInfo]:
        """
        List all registered documents.
        
        Returns:
            List of document information objects
        """
        self.logger.debug("Listing all documents")
        return await self.document_registry.list_documents()
    
    async def delete_document(self, document_id: str) -> bool:
        """
        Delete document and associated vector store data.
        
        Args:
            document_id: Document identifier
            
        Returns:
            True if deletion successful
        """
        self.logger.info(f"Deleting document", extra={"document_id": document_id})
        
        with ExceptionContext(VectorStoreError, f"Failed to delete document {document_id}"):
            return await self.document_registry.delete_document(document_id)
    
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
        self.logger.info(
            f"Renaming document",
            extra={
                "document_id": document_id,
                "new_display_name": new_display_name
            }
        )
        
        # Use the document registry to rename
        updated_doc = await self.document_registry.rename_document(document_id, new_display_name)
        
        self.logger.info(
            f"Document renamed successfully",
            extra={
                "document_id": document_id,
                "new_display_name": new_display_name
            }
        )
        
        return updated_doc
    
    async def _save_uploaded_file(self, file: UploadFile, document_id: str) -> str:
        """
        Save uploaded file to temporary location.
        
        Args:
            file: Uploaded file
            document_id: Document identifier for logging
            
        Returns:
            Temporary file path
            
        Raises:
            FileProcessingError: If file saving fails
        """
        with ExceptionContext(
            FileProcessingError,
            f"Failed to save uploaded file for document {document_id}"
        ):
            # Create temporary directory and path
            temp_dir = tempfile.mkdtemp(prefix=f"smartdocs_upload_{document_id}_")
            sanitized_filename = sanitize_filename(file.filename or "document.pdf")
            temp_path = os.path.join(temp_dir, sanitized_filename)
            
            # Write file data
            with open(temp_path, "wb") as temp_file:
                content = await file.read()
                temp_file.write(content)
            
            self.logger.debug(
                f"File saved to temporary location",
                extra={
                    "document_id": document_id,
                    "temp_path": temp_path,
                    "file_size": len(content)
                }
            )
            
            return temp_path
    
    async def _extract_text(self, file_path: str, document_id: str) -> str:
        """
        Extract text from PDF file.
        
        Args:
            file_path: Path to PDF file
            document_id: Document identifier for logging
            
        Returns:
            Extracted text content
            
        Raises:
            DocumentProcessingError: If text extraction fails
        """
        with ExceptionContext(
            DocumentProcessingError,
            f"Failed to extract text from PDF for document {document_id}"
        ):
            self.logger.debug(
                f"Extracting text from PDF",
                extra={"document_id": document_id, "file_path": file_path}
            )
            
            extracted_text = extract_pdf_text(file_path)
            
            if not extracted_text.strip():
                raise DocumentProcessingError(
                    message="No extractable text found in PDF",
                    error_code="EMPTY_PDF_TEXT",
                    details={"document_id": document_id}
                )
            
            self.logger.debug(
                f"Text extraction completed",
                extra={
                    "document_id": document_id,
                    "text_length": len(extracted_text),
                    "text_size_bytes": len(extracted_text.encode('utf-8'))
                }
            )
            
            return extracted_text
    
    def _clean_filename_for_display(self, filename: Optional[str]) -> str:
        """
        Clean filename for display by removing extension and formatting.
        
        Args:
            filename: Original filename
            
        Returns:
            Cleaned filename for display
        """
        if not filename:
            return "Untitled Document"
            
        # Remove file extension
        name = filename
        if '.' in name:
            name = name.rsplit('.', 1)[0]
            
        # Replace common separators with spaces
        name = name.replace('_', ' ').replace('-', ' ')
        
        # Remove extra whitespace and capitalize
        name = ' '.join(name.split()).title()
        
        return name or "Untitled Document"
    
    async def _create_chunks(self, text: str, document_id: str) -> List[Any]:
        """
        Create document chunks from extracted text.
        
        Args:
            text: Extracted text content
            document_id: Document identifier for logging
            
        Returns:
            List of document chunks (LangChain Document objects)
            
        Raises:
            DocumentProcessingError: If chunking fails
        """
        with ExceptionContext(
            DocumentProcessingError,
            f"Failed to create document chunks for document {document_id}"
        ):
            self.logger.debug(
                f"Creating document chunks",
                extra={
                    "document_id": document_id,
                    "text_length": len(text),
                    "chunk_size": self.settings.chunk_size,
                    "chunk_overlap": self.settings.chunk_overlap
                }
            )
            
            # Import here to avoid circular dependencies
            try:
                from langchain_text_splitters import RecursiveCharacterTextSplitter
            except ImportError:
                try:
                    from langchain.text_splitter import RecursiveCharacterTextSplitter
                except ImportError as e:
                    raise DocumentProcessingError(
                        message="LangChain text splitters not available. Install with: pip install langchain-text-splitters",
                        error_code="LANGCHAIN_TEXT_SPLITTERS_NOT_AVAILABLE",
                        details={"required_packages": ["langchain-text-splitters", "langchain"]}
                    ) from e
            
            # Create splitter and documents
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.settings.chunk_size,
                chunk_overlap=self.settings.chunk_overlap,
                separators=["\n\n", "\n", " ", ""]
            )
            
            documents = splitter.create_documents(
                [text],
                metadatas=[{"document_id": document_id}]
            )
            
            self.logger.debug(
                f"Document chunking completed",
                extra={
                    "document_id": document_id,
                    "chunk_count": len(documents)
                }
            )
            
            return documents
    
    async def _store_embeddings(
        self, 
        document_id: str, 
        documents: List[Any], 
        filename: Optional[str]
    ) -> str:
        """
        Create embeddings and store in vector database.
        
        Args:
            document_id: Document identifier
            documents: List of document chunks
            filename: Original filename for metadata
            
        Returns:
            Collection name
            
        Raises:
            VectorStoreError: If embedding creation or storage fails
        """
        with ExceptionContext(
            VectorStoreError,
            f"Failed to create and store embeddings for document {document_id}"
        ):
            self.logger.debug(
                f"Creating embeddings and storing in vector database",
                extra={
                    "document_id": document_id,
                    "chunk_count": len(documents),
                    "uploaded_filename": filename
                }
            )
            
            # Import embeddings here to avoid circular dependencies
            from ..config import get_settings
            
            try:
                from langchain_openai import OpenAIEmbeddings
            except ImportError:
                try:
                    from langchain.embeddings.openai import OpenAIEmbeddings
                except ImportError as e:
                    raise VectorStoreError(
                        message="OpenAI embeddings not available. Install with: pip install langchain-openai",
                        error_code="EMBEDDINGS_NOT_AVAILABLE",
                        details={"required_package": "langchain-openai"}
                    ) from e
            
            # Get API key and create embeddings
            settings = get_settings()
            if not settings.has_openai_key:
                raise VectorStoreError(
                    message="OpenAI API key not configured. Please set OPENAI_API_KEY environment variable.",
                    error_code="OPENAI_API_KEY_MISSING",
                    details={"required_env": "OPENAI_API_KEY"}
                )
            
            embeddings = OpenAIEmbeddings(openai_api_key=settings.openai_api_key)
            
            # Create collection in vector store
            collection_name = await self.document_registry.vector_store.create_collection(
                document_id=document_id,
                documents=documents,
                embeddings=embeddings,
                metadata={"filename": filename} if filename else None
            )
            
            self.logger.info(
                f"Embeddings created and stored successfully",
                extra={
                    "document_id": document_id,
                    "collection_name": collection_name,
                    "embeddings_count": len(documents)
                }
            )
            
            return collection_name
    
    async def get_processing_status(self, document_id: str) -> Dict[str, Any]:
        """
        Get document processing status and metadata.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Processing status information
        """
        try:
            doc_info = await self.get_document(document_id)
            vector_info = await self.document_registry.vector_store.get_collection_info(document_id)
            
            return {
                "document_id": document_id,
                "status": doc_info.status,
                "filename": doc_info.filename,
                "chunk_count": doc_info.chunk_count,
                "text_size_bytes": doc_info.text_size_bytes,
                "processing_time_ms": doc_info.processing_time_ms,
                "created_at": doc_info.created_at,
                "vector_store": {
                    "collection_name": vector_info.collection_name,
                    "embedding_count": vector_info.embedding_count,
                    "is_accessible": vector_info.is_accessible
                }
            }
        except Exception as e:
            self.logger.error(
                f"Failed to get processing status",
                extra={"document_id": document_id, "error": str(e)},
                exc_info=True
            )
            raise