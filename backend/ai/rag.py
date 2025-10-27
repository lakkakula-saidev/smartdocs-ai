"""
Retrieval-Augmented Generation pipeline for document Q&A.
"""

from typing import List, Dict, Any, Optional

from config import get_settings
from .exceptions import get_logger, AIServiceError
from .client import DirectOpenAIClient


class RAGPipeline:
    """
    Retrieval-Augmented Generation pipeline using direct OpenAI integration.
    
    Handles context assembly, prompt formatting, and response generation
    for document-based question answering without LangChain dependencies.
    """
    
    def __init__(self, openai_client: DirectOpenAIClient):
        """
        Initialize RAG pipeline.
        
        Args:
            openai_client: Configured OpenAI client instance
        """
        self.client = openai_client
        self.settings = get_settings()
        self.logger = get_logger("rag_pipeline")
        
        # Context and response configuration
        self.max_context_chars = getattr(self.settings, 'max_context_chars', 8000)
        self.max_response_tokens = 1000
        self.temperature = getattr(self.settings, 'openai_temperature', 0.1)
    
    def build_context_from_chunks(self, chunks: List[Any]) -> str:
        """
        Build context string from retrieved chunks.
        
        Args:
            chunks: Retrieved document chunks (can be various formats)
            
        Returns:
            Formatted context string
        """
        if not chunks:
            return ""
        
        context_parts = []
        total_chars = 0
        
        for i, chunk in enumerate(chunks):
            # Extract content from different chunk formats
            if hasattr(chunk, 'page_content'):
                content = chunk.page_content  # LangChain Document format
            elif hasattr(chunk, 'content'):
                content = chunk.content  # TextChunk format
            elif isinstance(chunk, dict) and 'content' in chunk:
                content = chunk['content']  # Dictionary format
            else:
                content = str(chunk)  # Fallback to string conversion
            
            content = content.strip()
            if not content:
                continue
            
            # Check if adding this chunk would exceed limit
            if total_chars + len(content) > self.max_context_chars:
                break
            
            # Add separator for readability
            separator = f"\n\n--- Document Section {i+1} ---\n"
            context_parts.append(separator + content)
            total_chars += len(separator) + len(content)
        
        context_text = "\n".join(context_parts)
        
        self.logger.debug(
            f"Built context from chunks",
            extra={
                "chunk_count": len(chunks),
                "used_chunks": len(context_parts),
                "context_chars": len(context_text),
                "max_context_chars": self.max_context_chars
            }
        )
        
        return context_text
    
    def create_qa_prompt(self, query: str, context: str) -> List[Dict[str, str]]:
        """
        Create structured prompt for question answering.
        
        Args:
            query: User question
            context: Document context
            
        Returns:
            List of message dictionaries for chat completion
        """
        system_message = {
            "role": "system",
            "content": (
                "You are a helpful assistant that answers questions based on provided document context. "
                "Use the following guidelines:\n"
                "- Answer based only on the provided context\n"
                "- If the answer is not in the context, say you don't know\n"
                "- Be concise but comprehensive\n"
                "- Use markdown formatting for better readability\n"
                "- Include relevant details and examples from the context"
            )
        }
        
        user_message = {
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {query}"
        }
        
        return [system_message, user_message]
    
    async def generate_response(
        self,
        query: str,
        retrieved_chunks: List[Any],
        document_id: Optional[str] = None
    ) -> str:
        """
        Generate response using RAG pipeline.
        
        Args:
            query: User question
            retrieved_chunks: Retrieved document chunks
            document_id: Document identifier for logging
            
        Returns:
            Generated response text
            
        Raises:
            AIServiceError: If response generation fails
        """
        self.logger.info(
            f"Generating RAG response",
            extra={
                "query_length": len(query),
                "chunk_count": len(retrieved_chunks),
                "document_id": document_id
            }
        )
        
        try:
            # Build context from chunks
            context = self.build_context_from_chunks(retrieved_chunks)
            
            if not context.strip():
                return "I couldn't find relevant information in the document to answer your question."
            
            # Create prompt messages
            messages = self.create_qa_prompt(query, context)
            
            # Generate response
            response = await self.client.chat_completion(
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_response_tokens
            )
            
            answer = response.content.strip()
            
            if not answer:
                raise AIServiceError(
                    message="Empty response generated by RAG pipeline",
                    error_code="EMPTY_RAG_RESPONSE",
                    details={"query": query, "document_id": document_id}
                )
            
            self.logger.info(
                f"RAG response generated successfully",
                extra={
                    "document_id": document_id,
                    "response_length": len(answer),
                    "processing_time_ms": response.processing_time_ms,
                    "token_usage": response.usage
                }
            )
            
            return answer
            
        except Exception as e:
            self.logger.error(
                f"RAG response generation failed",
                extra={
                    "query": query,
                    "document_id": document_id,
                    "chunk_count": len(retrieved_chunks),
                    "error": str(e)
                },
                exc_info=True
            )
            raise AIServiceError(
                message="Failed to generate RAG response",
                error_code="RAG_GENERATION_FAILED",
                details={
                    "query": query,
                    "document_id": document_id,
                    "error": str(e)
                }
            ) from e