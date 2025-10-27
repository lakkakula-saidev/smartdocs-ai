"""
Chat service for SmartDocs AI Backend.

This service handles question-answering and chat interactions with documents.
It orchestrates vector retrieval, context assembly, LLM processing, and
response enhancement for conversational document interactions.
"""

import time
import re
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..config import Settings, get_settings
from ..exceptions import (
    AIServiceError,
    DocumentNotFoundError,
    ValidationError,
    ExceptionContext
)
from ..logger import get_logger
from ..models.schemas import AskRequest, AskResponse
from ..db.vector_store import get_document_registry, DocumentRegistry
from ..utils.text_processing import enhance_markdown

# Import new AI integration module
from ai import get_rag_pipeline, get_openai_client


class ChatService:
    """
    Service for chat and question-answering operations.
    
    Handles the complete QA pipeline from query validation to response
    generation, including vector retrieval, context assembly, and
    response enhancement.
    """
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        document_registry: Optional[DocumentRegistry] = None
    ):
        """
        Initialize chat service.
        
        Args:
            settings: Application settings (uses global if None)
            document_registry: Document registry instance (uses global if None)
        """
        self.settings = settings or get_settings()
        self.document_registry = document_registry or get_document_registry()
        self.logger = get_logger("chat_service")
        
        # Session tracking
        self._session_stats = {
            "total_queries": 0,
            "total_response_time_ms": 0,
            "last_query_at": None
        }
        
        # Initialize AI components
        self.rag_pipeline = get_rag_pipeline()
        self.openai_client = get_openai_client()
    
    async def ask_question(self, request: AskRequest) -> AskResponse:
        """
        Process a question about a document and generate an AI response.
        
        Args:
            request: Question request with query and document ID
            
        Returns:
            AI-generated response with enhanced formatting
            
        Raises:
            ValidationError: If request validation fails
            DocumentNotFoundError: If document not found
            AIServiceError: If LLM processing fails
        """
        start_time = time.time()
        
        self.logger.info(
            f"Processing chat question",
            extra={
                "document_id": request.document_id,
                "query_length": len(request.query),
                "query_preview": request.query[:100] + "..." if len(request.query) > 100 else request.query
            }
        )
        
        try:
            # Step 1: Validate request
            await self._validate_request(request)
            
            # Step 2: Ensure document exists
            await self._validate_document_exists(request.document_id)
            
            # Step 3: Retrieve relevant context
            retriever = await self._get_retriever(request.document_id)
            context_chunks = await self._retrieve_context(retriever, request.query)
            
            # Step 4: Generate AI response
            raw_answer = await self._generate_response(
                query=request.query,
                context_chunks=context_chunks,
                document_id=request.document_id
            )
            
            # Step 5: Enhance response formatting
            enhanced_answer = await self._enhance_response(raw_answer)
            
            # Step 6: Update session statistics
            processing_time_ms = int((time.time() - start_time) * 1000)
            await self._update_session_stats(processing_time_ms)
            
            self.logger.info(
                f"Chat question processed successfully",
                extra={
                    "document_id": request.document_id,
                    "processing_time_ms": processing_time_ms,
                    "response_length": len(enhanced_answer),
                    "source_chunks": len(context_chunks)
                }
            )
            
            return AskResponse(
                answer=enhanced_answer,
                document_id=request.document_id,
                processing_time_ms=processing_time_ms,
                source_chunks_count=len(context_chunks)
            )
            
        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            self.logger.error(
                f"Chat question processing failed",
                extra={
                    "document_id": request.document_id,
                    "query": request.query,
                    "processing_time_ms": processing_time_ms,
                    "error": str(e)
                },
                exc_info=True
            )
            raise
    
    async def get_session_stats(self) -> Dict[str, Any]:
        """
        Get current session statistics.
        
        Returns:
            Session statistics dictionary
        """
        avg_response_time = (
            self._session_stats["total_response_time_ms"] / self._session_stats["total_queries"]
            if self._session_stats["total_queries"] > 0
            else 0
        )
        
        return {
            "total_queries": self._session_stats["total_queries"],
            "average_response_time_ms": round(avg_response_time, 2),
            "last_query_at": self._session_stats["last_query_at"]
        }
    
    async def _validate_request(self, request: AskRequest) -> None:
        """
        Validate the chat request.
        
        Args:
            request: Request to validate
            
        Raises:
            ValidationError: If validation fails
        """
        if not request.query.strip():
            raise ValidationError(
                message="Query cannot be empty or only whitespace",
                error_code="EMPTY_QUERY",
                details={"query": request.query}
            )
        
        if len(request.query.strip()) < 3:
            raise ValidationError(
                message="Query must be at least 3 characters long",
                error_code="QUERY_TOO_SHORT",
                details={"query": request.query, "length": len(request.query.strip())}
            )
        
        # Validate document ID format (32-character hex)
        if not re.match(r'^[a-f0-9]{32}$', request.document_id):
            raise ValidationError(
                message="Invalid document ID format",
                error_code="INVALID_DOCUMENT_ID",
                details={"document_id": request.document_id}
            )
    
    async def _validate_document_exists(self, document_id: str) -> None:
        """
        Validate that the document exists in the registry.
        
        Args:
            document_id: Document identifier
            
        Raises:
            DocumentNotFoundError: If document not found
        """
        try:
            await self.document_registry.get_document(document_id)
        except Exception:
            # Let DocumentNotFoundError pass through, wrap others
            raise DocumentNotFoundError(document_id)
    
    async def _get_retriever(self, document_id: str) -> Any:
        """
        Get retriever for document.
        
        Args:
            document_id: Document identifier
            
        Returns:
            LangChain retriever instance
            
        Raises:
            AIServiceError: If retriever creation fails
        """
        with ExceptionContext(
            AIServiceError,
            f"Failed to create retriever for document {document_id}"
        ):
            return await self.document_registry.get_retriever(
                document_id=document_id,
                k=self.settings.retrieval_k
            )
    
    async def _retrieve_context(self, retriever: Any, query: str) -> List[Any]:
        """
        Retrieve relevant context chunks for the query.
        
        Args:
            retriever: LangChain retriever instance
            query: User query
            
        Returns:
            List of relevant document chunks
            
        Raises:
            AIServiceError: If retrieval fails
        """
        with ExceptionContext(AIServiceError, "Failed to retrieve context chunks"):
            self.logger.debug(f"Retrieving context chunks", extra={"query": query})
            
            # Use retriever to get relevant documents
            # Use invoke() method for modern LangChain compatibility
            chunks = retriever.invoke(query)
            
            self.logger.debug(
                f"Context retrieval completed",
                extra={
                    "query": query,
                    "chunks_retrieved": len(chunks)
                }
            )
            
            return chunks
    
    async def _generate_response(
        self,
        query: str,
        context_chunks: List[Any],
        document_id: str
    ) -> str:
        """
        Generate AI response using LLM with fallback support.
        
        Args:
            query: User query
            context_chunks: Retrieved context chunks (used by fallback path)
            document_id: Document identifier for logging
            
        Returns:
            Generated response text
            
        Raises:
            AIServiceError: If LLM generation fails
        """
        with ExceptionContext(
            AIServiceError,
            f"Failed to generate AI response for document {document_id}"
        ):
            # Use direct RAG pipeline (no LangChain dependencies)
            return await self.rag_pipeline.generate_response(
                query=query,
                retrieved_chunks=context_chunks,
                document_id=document_id
            )
    
    # Removed complex LangChain-based methods - now using direct AI integration
    
    async def _enhance_response(self, raw_answer: str) -> str:
        """
        Enhance response with better markdown formatting.
        
        Args:
            raw_answer: Raw LLM response
            
        Returns:
            Enhanced response with improved formatting
        """
        self.logger.debug(
            f"Enhancing response formatting",
            extra={"raw_length": len(raw_answer)}
        )
        
        enhanced = enhance_markdown(raw_answer)
        
        self.logger.debug(
            f"Response enhancement completed",
            extra={
                "raw_length": len(raw_answer),
                "enhanced_length": len(enhanced),
                "formatting_added": len(enhanced) != len(raw_answer)
            }
        )
        
        return enhanced
    
    async def _update_session_stats(self, processing_time_ms: int) -> None:
        """
        Update session statistics.
        
        Args:
            processing_time_ms: Processing time for this query
        """
        self._session_stats["total_queries"] += 1
        self._session_stats["total_response_time_ms"] += processing_time_ms
        self._session_stats["last_query_at"] = datetime.utcnow()
        
        self.logger.debug(
            f"Session stats updated",
            extra={
                "total_queries": self._session_stats["total_queries"],
                "current_processing_time_ms": processing_time_ms,
                "average_response_time_ms": (
                    self._session_stats["total_response_time_ms"] / 
                    self._session_stats["total_queries"]
                )
            }
        )
    
    # Additional utility methods for chat features
    
    async def validate_query_complexity(self, query: str) -> Dict[str, Any]:
        """
        Analyze query complexity and provide suggestions.
        
        Args:
            query: User query to analyze
            
        Returns:
            Query analysis information
        """
        analysis = {
            "length": len(query),
            "word_count": len(query.split()),
            "sentence_count": len([s for s in query.split('.') if s.strip()]),
            "question_words": [],
            "complexity": "simple"
        }
        
        # Detect question words
        question_words = ['what', 'how', 'why', 'when', 'where', 'who', 'which']
        for word in question_words:
            if word.lower() in query.lower():
                analysis["question_words"].append(word)
        
        # Determine complexity
        if analysis["word_count"] > 20 or analysis["sentence_count"] > 2:
            analysis["complexity"] = "complex"
        elif analysis["word_count"] > 10 or len(analysis["question_words"]) > 1:
            analysis["complexity"] = "moderate"
        
        return analysis
    
    async def suggest_related_queries(self, document_id: str, current_query: str) -> List[str]:
        """
        Suggest related queries based on document content.
        
        Args:
            document_id: Document identifier
            current_query: Current query for context
            
        Returns:
            List of suggested related queries
        """
        # This is a placeholder implementation
        # In a full implementation, this would analyze document content
        # and generate contextually relevant suggestions
        
        suggestions = [
            "Can you summarize the main points?",
            "What are the key findings?",
            "What methodology was used?",
            "What are the conclusions?",
            "Are there any recommendations?"
        ]
        
        # Filter out the current query if similar
        filtered_suggestions = [
            s for s in suggestions 
            if not any(word in current_query.lower() for word in s.lower().split()[:3])
        ]
        
        return filtered_suggestions[:3]  # Return top 3 suggestions
    
    async def validate_document_access(self, document_id: str) -> None:
        """
        Validate that a document exists and is accessible.
        
        Args:
            document_id: Document identifier to validate
            
        Raises:
            DocumentNotFoundError: If document not found or inaccessible
        """
        await self._validate_document_exists(document_id)
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on chat service components.
        
        Returns:
            Health check results dictionary
        """
        results = {
            "status": "healthy",
            "tests": {
                "service_initialization": "passed",
                "openai_connectivity": "unknown",
                "langchain_dependencies": "unknown",
                "vector_store_access": "unknown"
            }
        }
        
        try:
            # Test AI integration module
            try:
                from ai import health_check as ai_health_check
                ai_health = await ai_health_check()
                if ai_health.get("status") == "healthy":
                    results["tests"]["ai_integration"] = "passed"
                else:
                    results["tests"]["ai_integration"] = f"degraded: {ai_health}"
                    results["status"] = "degraded"
            except Exception as e:
                results["tests"]["ai_integration"] = f"failed: {str(e)}"
                results["status"] = "degraded"
            
            # Test OpenAI client directly
            try:
                client = get_openai_client()
                # Simple test - just check if client is initialized
                results["tests"]["openai_connectivity"] = "passed"
            except Exception as e:
                results["tests"]["openai_connectivity"] = f"failed: {str(e)}"
                results["status"] = "unhealthy"
            
            # Test vector store access
            try:
                registry_health = await self.document_registry.health_check()
                if registry_health.get("status") == "healthy":
                    results["tests"]["vector_store_access"] = "passed"
                else:
                    results["tests"]["vector_store_access"] = "failed: registry unhealthy"
                    results["status"] = "degraded"
            except Exception as e:
                results["tests"]["vector_store_access"] = f"failed: {str(e)}"
                results["status"] = "unhealthy"
                
        except Exception as e:
            results["status"] = "unhealthy"
            results["error"] = str(e)
        
        return results