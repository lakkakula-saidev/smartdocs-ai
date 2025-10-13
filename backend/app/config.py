"""
Configuration management for SmartDocs AI Backend.

This module provides centralized configuration using Pydantic BaseSettings
for environment variable management and validation.
"""

import os
from enum import Enum
from typing import Optional, List
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic import field_validator
from dotenv import load_dotenv, find_dotenv


class Environment(str, Enum):
    """Application environment types."""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class VectorStoreProvider(str, Enum):
    """Supported vector store providers."""
    CHROMA = "chroma"
    PINECONE = "pinecone"


class LogLevel(str, Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    
    Uses Pydantic BaseSettings for automatic environment variable loading
    and validation. Supports .env file loading with diagnostic logging.
    """
    
    # === Core Configuration ===
    app_name: str = Field(
        default="SmartDocs AI Backend",
        description="Application name"
    )
    app_version: str = Field(
        default="0.1.0",
        description="Application version"
    )
    app_description: str = Field(
        default="PDF ingestion and retrieval QA service using FastAPI + LangChain + ChromaDB.",
        description="Application description"
    )
    
    # === Environment ===
    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        env="ENVIRONMENT",
        description="Application environment"
    )
    debug: bool = Field(
        default=False,
        env="DEBUG",
        description="Enable debug mode"
    )
    
    # === Server Configuration ===
    host: str = Field(
        default="0.0.0.0",
        env="HOST",
        description="Server host"
    )
    port: int = Field(
        default=8000,
        env="PORT",
        description="Server port"
    )
    reload: bool = Field(
        default=False,
        env="RELOAD",
        description="Enable auto-reload in development"
    )
    
    # === CORS Configuration ===
    cors_origins: List[str] = Field(
        default=["*"],
        env="CORS_ORIGINS",
        description="Allowed CORS origins (comma-separated)"
    )
    cors_allow_credentials: bool = Field(
        default=True,
        env="CORS_ALLOW_CREDENTIALS",
        description="Allow credentials in CORS"
    )
    
    # === AI/LLM Configuration ===
    openai_api_key: str = Field(
        ...,
        env="OPENAI_API_KEY",
        description="OpenAI API key (required)"
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        env="OPENAI_MODEL",
        description="OpenAI model for chat completion"
    )
    openai_temperature: float = Field(
        default=0.1,
        env="OPENAI_TEMPERATURE",
        ge=0.0,
        le=2.0,
        description="OpenAI model temperature"
    )
    
    # === Vector Store Configuration ===
    vector_store_provider: VectorStoreProvider = Field(
        default=VectorStoreProvider.CHROMA,
        env="VECTOR_STORE_PROVIDER",
        description="Vector store provider to use"
    )
    vector_store_persist_dir: str = Field(
        default="backend/vectorstores",
        env="VECTOR_STORE_PERSIST_DIR",
        description="Directory for persistent vector storage"
    )
    
    # === Document Processing Configuration ===
    chunk_size: int = Field(
        default=1000,
        env="CHUNK_SIZE",
        ge=100,
        le=10000,
        description="Text chunk size for document splitting"
    )
    chunk_overlap: int = Field(
        default=150,
        env="CHUNK_OVERLAP",
        ge=0,
        le=500,
        description="Text chunk overlap for document splitting"
    )
    retrieval_k: int = Field(
        default=4,
        env="RETRIEVAL_K",
        ge=1,
        le=20,
        description="Number of chunks to retrieve for QA"
    )
    
    # === File Upload Configuration ===
    max_upload_size_mb: int = Field(
        default=50,
        env="MAX_UPLOAD_SIZE_MB",
        ge=1,
        le=500,
        description="Maximum file upload size in MB"
    )
    allowed_file_types: List[str] = Field(
        default=["application/pdf"],
        env="ALLOWED_FILE_TYPES",
        description="Allowed MIME types for file upload (comma-separated)"
    )
    
    # === Logging Configuration ===
    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        env="LOG_LEVEL",
        description="Logging level"
    )
    log_format: str = Field(
        default="structured",
        env="LOG_FORMAT",
        description="Log format: 'structured' or 'simple'"
    )
    
    # === Pinecone Configuration (Optional) ===
    pinecone_api_key: Optional[str] = Field(
        default=None,
        env="PINECONE_API_KEY",
        description="Pinecone API key (required if using Pinecone)"
    )
    pinecone_environment: Optional[str] = Field(
        default=None,
        env="PINECONE_ENVIRONMENT",
        description="Pinecone environment (required if using Pinecone)"
    )
    pinecone_index_name: Optional[str] = Field(
        default="smartdocs-ai",
        env="PINECONE_INDEX_NAME",
        description="Pinecone index name"
    )
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        # Custom field for environment variable parsing
        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str):
            """Custom environment variable parsing for lists."""
            if field_name in ['cors_origins', 'allowed_file_types']:
                return [item.strip() for item in raw_val.split(',') if item.strip()]
            return raw_val
    
    @field_validator('environment', mode='before')
    @classmethod
    def validate_environment(cls, v):
        """Validate and normalize environment value."""
        if isinstance(v, str):
            return v.lower()
        return v
    
    @field_validator('debug', mode='before')
    @classmethod
    def validate_debug(cls, v, info):
        """Set debug=True automatically for development environment."""
        if 'environment' in info.data and info.data['environment'] == Environment.DEVELOPMENT:
            return True
        return v
    
    @field_validator('reload', mode='before')
    @classmethod
    def validate_reload(cls, v, info):
        """Set reload=True automatically for development environment."""
        if 'environment' in info.data and info.data['environment'] == Environment.DEVELOPMENT:
            return True
        return v
    
    @field_validator('pinecone_api_key')
    @classmethod
    def validate_pinecone_config(cls, v, info):
        """Validate Pinecone configuration if Pinecone is selected as provider."""
        if info.data.get('vector_store_provider') == VectorStoreProvider.PINECONE:
            if not v:
                raise ValueError("PINECONE_API_KEY is required when using Pinecone provider")
            if not info.data.get('pinecone_environment'):
                raise ValueError("PINECONE_ENVIRONMENT is required when using Pinecone provider")
        return v
    
    @field_validator('cors_origins', mode='before')
    @classmethod
    def validate_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v
    
    @field_validator('allowed_file_types', mode='before')
    @classmethod
    def validate_allowed_file_types(cls, v):
        """Parse allowed file types from comma-separated string."""
        if isinstance(v, str):
            return [mime_type.strip() for mime_type in v.split(',') if mime_type.strip()]
        return v
    
    @property
    def max_upload_size_bytes(self) -> int:
        """Get maximum upload size in bytes."""
        return self.max_upload_size_mb * 1024 * 1024
    
    @property
    def vector_store_path(self) -> Path:
        """Get vector store persistence directory as Path object."""
        return Path(self.vector_store_persist_dir)
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEVELOPMENT
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION
    
    def create_vector_store_dir(self) -> None:
        """Create vector store directory if it doesn't exist."""
        self.vector_store_path.mkdir(parents=True, exist_ok=True)


def load_settings() -> Settings:
    """
    Load application settings with enhanced .env file discovery and diagnostics.
    
    Provides the same diagnostic logging as the original main.py implementation
    for environment variable loading and OpenAI API key validation.
    
    Returns:
        Settings: Configured settings instance
        
    Raises:
        ValidationError: If required settings are missing or invalid
    """
    # Enhanced .env file loading with diagnostics (matching original main.py pattern)
    try:
        dotenv_path = find_dotenv(usecwd=True)
        if dotenv_path:
            print(f"[env] Located .env file at: {dotenv_path}")
        else:
            print("[env] No .env file discovered via find_dotenv()")
        
        loaded = load_dotenv(dotenv_path or None)
        print(f"[env] load_dotenv loaded={loaded}")
        
    except Exception as e:
        # Non-fatal; continue with existing environment
        print(f"[env] dotenv load error: {e}")
    
    # Immediate post-load inspection (masked, matching original pattern)
    raw_key = os.getenv("OPENAI_API_KEY", "")
    if raw_key:
        print(f"[env] OPENAI_API_KEY present (len={len(raw_key)} prefix={raw_key[:7]}*** masked)")
    else:
        print("[env] OPENAI_API_KEY still empty right after load_dotenv()")
    
    # Load and validate settings
    try:
        settings = Settings()
        
        # Additional startup validation messages
        if settings.is_development:
            print(f"[config] Running in DEVELOPMENT mode (debug={settings.debug}, reload={settings.reload})")
        else:
            print(f"[config] Running in {settings.environment.upper()} mode")
            
        print(f"[config] Vector store provider: {settings.vector_store_provider}")
        print(f"[config] OpenAI model: {settings.openai_model}")
        
        # Ensure vector store directory exists
        settings.create_vector_store_dir()
        
        return settings
        
    except Exception as e:
        print(f"[config] Settings validation failed: {e}")
        raise


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get the global settings instance.
    
    Implements singleton pattern for settings to ensure consistent
    configuration across the application.
    
    Returns:
        Settings: Global settings instance
    """
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


# Convenience function for backward compatibility with main.py patterns
def require_openai_api_key() -> str:
    """
    Get OpenAI API key with validation.
    
    Provides backward compatibility with the original main.py implementation
    while using the new configuration system.
    
    Returns:
        str: Valid OpenAI API key
        
    Raises:
        HTTPException: If API key is not configured
    """
    from fastapi import HTTPException, status
    
    # Reload settings to pick up any new environment changes
    global _settings
    _settings = None  # Force reload
    
    try:
        settings = get_settings()
        return settings.openai_api_key
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPENAI_API_KEY not configured."
        )