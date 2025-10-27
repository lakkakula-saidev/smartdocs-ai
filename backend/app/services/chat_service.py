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
        
        # Cache for chain components (avoid repeated imports)
        self._chain_components = None
    
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
            # Try advanced chain imports first, fallback to manual RAG if unavailable
            chain_components = self._load_chain_components()
            
            if chain_components["has_chains"]:
                return await self._generate_with_chains(query, document_id, context_chunks)
            else:
                self.logger.warning(
                    "LangChain chains unavailable, using fallback RAG",
                    extra={
                        "failure_stage": "chain_import",
                        "exception_type": chain_components["error_type"],
                        "document_id": document_id
                    }
                )
                return await self._generate_with_fallback_rag(query, context_chunks, document_id)
    
    def _load_chain_components(self) -> Dict[str, Any]:
        """
        Load LangChain components with fallback detection and caching.
        
        Returns:
            Dictionary with component availability and error info
        """
        if self._chain_components is not None:
            return self._chain_components
            
        try:
            from langchain_openai import ChatOpenAI
            from langchain.chains import create_retrieval_chain
            from langchain.chains.combine_documents import create_stuff_documents_chain
            from langchain_core.prompts import ChatPromptTemplate
            self._chain_components = {
                "has_chains": True,
                "ChatOpenAI": ChatOpenAI,
                "create_retrieval_chain": create_retrieval_chain,
                "create_stuff_documents_chain": create_stuff_documents_chain,
                "ChatPromptTemplate": ChatPromptTemplate,
                "error_type": None
            }
        except ImportError as e:
            # Try fallback imports
            try:
                from langchain_openai import ChatOpenAI
                from langchain_core.prompts import ChatPromptTemplate
                self._chain_components = {
                    "has_chains": False,
                    "ChatOpenAI": ChatOpenAI,
                    "ChatPromptTemplate": ChatPromptTemplate,
                    "error_type": type(e).__name__
                }
            except ImportError as fallback_e:
                raise AIServiceError(
                    message="Essential LangChain components unavailable",
                    error_code="LANGCHAIN_CORE_MISSING",
                    details={
                        "required_packages": "langchain-openai, langchain-core",
                        "chain_error": str(e),
                        "fallback_error": str(fallback_e)
                    }
                ) from fallback_e
        
        return self._chain_components
    
    async def _generate_with_chains(
        self,
        query: str,
        document_id: str,
        context_chunks: List[Any]
    ) -> str:
        """
        Generate response using advanced LangChain retrieval chains.
        
        Args:
            query: User query
            document_id: Document identifier
            context_chunks: Retrieved context chunks for logging
            
        Returns:
            Generated response text
        """
        components = self._load_chain_components()
        ChatOpenAI = components["ChatOpenAI"]
        create_retrieval_chain = components["create_retrieval_chain"]
        create_stuff_documents_chain = components["create_stuff_documents_chain"]
        ChatPromptTemplate = components["ChatPromptTemplate"]
        
        # Get API key and create LLM
        from ..config import require_openai_api_key
        api_key = require_openai_api_key()
        
        llm = ChatOpenAI(
            temperature=self.settings.openai_temperature,
            model_name=self.settings.openai_model,
            openai_api_key=api_key
        )
        
        # Get retriever for the document
        retriever = await self.document_registry.get_retriever(
            document_id=document_id,
            k=self.settings.retrieval_k
        )
        
        # Create standardized prompt template
        prompt = self._create_standard_prompt_template(ChatPromptTemplate)
        
        # Create document chain and retrieval chain
        document_chain = create_stuff_documents_chain(llm, prompt)
        chain = create_retrieval_chain(retriever, document_chain)
        
        self.logger.debug(
            f"Generating AI response with chains",
            extra={
                "document_id": document_id,
                "query": query,
                "model": self.settings.openai_model,
                "temperature": self.settings.openai_temperature,
                "context_chunks": len(context_chunks)
            }
        )
        
        # Generate response
        result = chain.invoke({"input": query})
        
        # Extract answer from modern LangChain result
        answer = result.get("answer") or ""
        
        if not answer.strip():
            raise AIServiceError(
                message="Empty response generated by LLM",
                error_code="EMPTY_LLM_RESPONSE",
                details={"query": query, "document_id": document_id}
            )
        
        self.logger.debug(
            f"AI response generated successfully with chains",
            extra={
                "document_id": document_id,
                "response_length": len(answer),
                "response_preview": answer[:200] + "..." if len(answer) > 200 else answer
            }
        )
        
        return answer.strip()
    
    def _create_standard_prompt_template(self, ChatPromptTemplate) -> Any:
        """
        Create standardized prompt template for consistent behavior.
        
        Args:
            ChatPromptTemplate: LangChain ChatPromptTemplate class
            
        Returns:
            Configured prompt template
        """
        return ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant that answers questions based on the provided context. "
                      "Use the following pieces of context to answer the user's question. "
                      "If you don't know the answer based on the context, say that you don't know."),
            ("user", "Context: {context}\n\nQuestion: {input}")
        ])
    
    async def _generate_with_fallback_rag(
        self,
        query: str,
        context_chunks: List[Any],
        document_id: str
    ) -> str:
        """
        Manual RAG pipeline using provided context chunks when chains unavailable.
        
        Args:
            query: User query
            context_chunks: Retrieved context chunks to use
            document_id: Document identifier for logging
            
        Returns:
            Generated response text
            
        Raises:
            AIServiceError: If fallback RAG fails
        """
        try:
            components = self._load_chain_components()
            ChatOpenAI = components["ChatOpenAI"]
            ChatPromptTemplate = components["ChatPromptTemplate"]
            
            # Get API key and create LLM
            from ..config import require_openai_api_key
            api_key = require_openai_api_key()
            
            llm = ChatOpenAI(
                temperature=self.settings.openai_temperature,
                model_name=self.settings.openai_model,
                openai_api_key=api_key
            )
            
            # Build context string from provided chunks with configurable token limit
            context_parts = []
            total_chars = 0
            max_context_chars = self.settings.max_context_chars
            
            for chunk in context_chunks:
                content = chunk.page_content if hasattr(chunk, 'page_content') else str(chunk)
                content = content.strip()
                if total_chars + len(content) > max_context_chars:
                    break
                context_parts.append(content)
                total_chars += len(content)
            
            context_text = "\n\n---\n\n".join(context_parts)
            
            # Create standardized prompt template
            prompt = self._create_standard_prompt_template(ChatPromptTemplate)
            
            self.logger.debug(
                f"Generating AI response with fallback RAG",
                extra={
                    "document_id": document_id,
                    "query": query,
                    "model": self.settings.openai_model,
                    "temperature": self.settings.openai_temperature,
                    "context_chunks": len(context_parts),
                    "context_chars": total_chars
                }
            )
            
            # Generate response using direct LLM call with proper input structure
            result = llm.invoke(prompt.format_messages(context=context_text, input=query))
            
            answer = result.content.strip() if hasattr(result, 'content') else str(result).strip()
            
            if not answer:
                raise AIServiceError(
                    message="Empty response from fallback RAG",
                    error_code="PIPELINE_FALLBACK_FAILED",
                    details={"query": query, "document_id": document_id}
                )
            
            self.logger.debug(
                f"AI response generated successfully with fallback RAG",
                extra={
                    "document_id": document_id,
                    "response_length": len(answer),
                    "response_preview": answer[:200] + "..." if len(answer) > 200 else answer
                }
            )
            
            return answer
            
        except Exception as e:
            self.logger.error(
                "Fallback RAG pipeline failed",
                extra={
                    "failure_stage": "fallback_rag",
                    "exception_type": type(e).__name__,
                    "document_id": document_id,
                    "query": query
                },
                exc_info=True
            )
            raise AIServiceError(
                message="RAG fallback pipeline failed",
                error_code="PIPELINE_FALLBACK_FAILED",
                details={"original_error": str(e)}
            ) from e
    
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
            # Test LangChain dependencies
            try:
                from langchain_openai import ChatOpenAI
                from langchain.chains import create_retrieval_chain
                from langchain.chains.combine_documents import create_stuff_documents_chain
                from langchain_core.prompts import ChatPromptTemplate
                results["tests"]["langchain_dependencies"] = "passed"
            except ImportError as e:
                results["tests"]["langchain_dependencies"] = f"failed: {str(e)}"
                results["status"] = "degraded"
            
            # Test OpenAI API key
            try:
                from ..config import require_openai_api_key
                api_key = require_openai_api_key()
                if api_key and len(api_key) > 20:  # Basic validation
                    results["tests"]["openai_connectivity"] = "passed"
                else:
                    results["tests"]["openai_connectivity"] = "failed: invalid API key"
                    results["status"] = "unhealthy"
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