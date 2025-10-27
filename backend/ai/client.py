"""
Direct OpenAI client integration for SmartDocs AI.
"""

import os
import time
from typing import List, Dict, Optional

import openai
from openai import OpenAI
import tiktoken

from config import get_settings
from .exceptions import get_logger, AIServiceError, ConfigurationError, EmbeddingResult, ChatResponse


class DirectOpenAIClient:
    """
    Direct OpenAI client with comprehensive error handling and retry logic.
    
    Handles authentication, model configuration, and provides a simplified
    interface for embeddings and chat completions.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI client.
        
        Args:
            api_key: OpenAI API key (uses environment variable if None)
        """
        self.settings = get_settings()
        self.logger = get_logger("openai_client")
        
        # Get API key from parameter or environment
        self.api_key = api_key or self._get_api_key()
        
        # Model configurations
        self.embedding_model = "text-embedding-3-small"  # Cost-effective embedding model
        self.chat_model = "gpt-4o-mini"  # Cost-effective chat model
        self.max_retries = 3
        self.timeout = 30.0
        
        # Initialize client first
        self.client = self._initialize_client()
        
        # Token encoding for text processing
        self.encoding = self._get_encoding()
        
        self.logger.info(
            f"Initialized OpenAI client",
            extra={
                "embedding_model": self.embedding_model,
                "chat_model": self.chat_model,
                "has_api_key": bool(self.api_key)
            }
        )
    
    def _get_api_key(self) -> str:
        """Get OpenAI API key from environment."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ConfigurationError(
                message="OpenAI API key not found in environment variables",
                error_code="OPENAI_API_KEY_MISSING",
                details={"required_env": "OPENAI_API_KEY"}
            )
        return api_key
    
    def _initialize_client(self) -> OpenAI:
        """Initialize OpenAI client with error handling."""
        try:
            client = OpenAI(
                api_key=self.api_key,
                timeout=self.timeout,
                max_retries=self.max_retries
            )
            
            # Skip connectivity test if using test/placeholder API key
            if not self.api_key.startswith("test-") and not self.api_key.endswith("placeholder"):
                # Test client with a simple request
                self._test_client_connectivity(client)
            else:
                self.logger.warning("Skipping connectivity test for test/placeholder API key")
            
            return client
            
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI client: {e}")
            raise ConfigurationError(
                message="Failed to initialize OpenAI client",
                error_code="OPENAI_CLIENT_INIT_FAILED",
                details={"error": str(e)}
            ) from e
    
    def _test_client_connectivity(self, client: OpenAI) -> None:
        """Test client connectivity with a lightweight request."""
        try:
            # Test with a simple model list request (lightweight)
            models = client.models.list()
            available_models = [model.id for model in models.data]
            
            # Verify our required models are available
            if self.embedding_model not in available_models:
                self.logger.warning(f"Embedding model {self.embedding_model} not found in available models")
            
            if self.chat_model not in available_models:
                self.logger.warning(f"Chat model {self.chat_model} not found in available models")
                
        except Exception as e:
            self.logger.error(f"OpenAI client connectivity test failed: {e}")
            raise ConfigurationError(
                message="OpenAI API connectivity test failed",
                error_code="OPENAI_CONNECTIVITY_FAILED",
                details={"error": str(e)}
            ) from e
    
    def _get_encoding(self) -> tiktoken.Encoding:
        """Get tiktoken encoding for token counting."""
        try:
            return tiktoken.get_encoding("cl100k_base")  # GPT-4 encoding
        except Exception as e:
            self.logger.warning(f"Failed to load tiktoken encoding: {e}")
            return None
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Token count
        """
        if not text:
            return 0
            
        if self.encoding:
            try:
                return len(self.encoding.encode(text))
            except Exception:
                pass
        
        # Fallback estimation: roughly 4 characters per token
        return len(text) // 4
    
    async def generate_embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> EmbeddingResult:
        """
        Generate embeddings for texts using OpenAI API.
        
        Args:
            texts: List of texts to embed
            model: Embedding model (uses default if None)
            
        Returns:
            Embedding result with vectors and metadata
            
        Raises:
            AIServiceError: If embedding generation fails
        """
        model = model or self.embedding_model
        
        if not texts:
            return EmbeddingResult(embeddings=[], token_count=0, model=model)
        
        # Filter out empty texts
        valid_texts = [text.strip() for text in texts if text and text.strip()]
        if not valid_texts:
            return EmbeddingResult(embeddings=[], token_count=0, model=model)
        
        self.logger.debug(
            f"Generating embeddings",
            extra={
                "text_count": len(valid_texts),
                "model": model,
                "avg_text_length": sum(len(text) for text in valid_texts) // len(valid_texts)
            }
        )
        
        try:
            # Calculate token count
            total_tokens = sum(self.count_tokens(text) for text in valid_texts)
            
            # Generate embeddings
            response = self.client.embeddings.create(
                input=valid_texts,
                model=model
            )
            
            # Extract embeddings
            embeddings = [item.embedding for item in response.data]
            
            self.logger.info(
                f"Generated embeddings successfully",
                extra={
                    "text_count": len(valid_texts),
                    "embedding_dimensions": len(embeddings[0]) if embeddings else 0,
                    "total_tokens": total_tokens,
                    "model": model
                }
            )
            
            return EmbeddingResult(
                embeddings=embeddings,
                token_count=total_tokens,
                model=model
            )
            
        except Exception as e:
            self.logger.error(
                f"Embedding generation failed",
                extra={
                    "text_count": len(valid_texts),
                    "model": model,
                    "error": str(e)
                },
                exc_info=True
            )
            raise AIServiceError(
                message="Failed to generate embeddings",
                error_code="EMBEDDING_GENERATION_FAILED",
                details={
                    "model": model,
                    "text_count": len(valid_texts),
                    "error": str(e)
                }
            ) from e
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> ChatResponse:
        """
        Generate chat completion using OpenAI API.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Chat model (uses default if None)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream response
            
        Returns:
            Chat completion response
            
        Raises:
            AIServiceError: If chat completion fails
        """
        model = model or self.chat_model
        start_time = time.time()
        
        if not messages:
            raise AIServiceError(
                message="No messages provided for chat completion",
                error_code="EMPTY_MESSAGES",
                details={"messages": messages}
            )
        
        self.logger.debug(
            f"Generating chat completion",
            extra={
                "message_count": len(messages),
                "model": model,
                "temperature": temperature,
                "stream": stream
            }
        )
        
        try:
            # Prepare request parameters
            request_params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "stream": stream
            }
            
            if max_tokens:
                request_params["max_tokens"] = max_tokens
            
            # Generate completion
            response = self.client.chat.completions.create(**request_params)
            
            # Extract content and usage
            content = response.choices[0].message.content
            usage = response.usage.model_dump() if response.usage else {}
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            self.logger.info(
                f"Chat completion generated successfully",
                extra={
                    "model": model,
                    "response_length": len(content) if content else 0,
                    "processing_time_ms": processing_time_ms,
                    "usage": usage
                }
            )
            
            return ChatResponse(
                content=content or "",
                model=model,
                usage=usage,
                processing_time_ms=processing_time_ms
            )
            
        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            self.logger.error(
                f"Chat completion failed",
                extra={
                    "model": model,
                    "message_count": len(messages),
                    "processing_time_ms": processing_time_ms,
                    "error": str(e)
                },
                exc_info=True
            )
            raise AIServiceError(
                message="Failed to generate chat completion",
                error_code="CHAT_COMPLETION_FAILED",
                details={
                    "model": model,
                    "message_count": len(messages),
                    "error": str(e)
                }
            ) from e