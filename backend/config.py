"""
Simplified Configuration Management for SmartDocs AI Backend.

Provides centralized configuration using Pydantic BaseSettings with
minimal complexity and essential settings only.
"""

import os
from enum import Enum
from typing import Optional, List
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv, find_dotenv


class Environment(str, Enum):
    """Application environment types."""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class VectorStoreProvider(str, Enum):
    """Supported vector store providers."""
    CHROMA = "chroma"


class Settings(BaseSettings):
    """
    Simplified application settings with environment variable support.
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
        default=[
            "http://localhost:3000",
            "http://localhost:5173",
            "https://lakkakula-saidev.github.io"
        ],
        env="CORS_ORIGINS",
        description="Allowed CORS origins (comma-separated)"
    )
    cors_allow_credentials: bool = Field(
        default=True,
        env="CORS_ALLOW_CREDENTIALS",
        description="Allow credentials in CORS"
    )
    cors_max_age: int = Field(
        default=86400,
        env="CORS_MAX_AGE",
        description="CORS preflight cache duration in seconds"
    )
    
    # === OpenAI Configuration ===
    openai_api_key: Optional[str] = Field(
        default=None,
        env="OPENAI_API_KEY",
        description="OpenAI API key (required for AI features)"
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
    max_context_chars: int = Field(
        default=8000,
        env="MAX_CONTEXT_CHARS",
        ge=1000,
        le=32000,
        description="Maximum context size in characters for RAG"
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
    
    # === Security Configuration ===
    api_key_header: str = Field(
        default="X-API-Key",
        env="API_KEY_HEADER",
        description="Custom API key header name"
    )
    enable_security_headers: bool = Field(
        default=True,
        env="ENABLE_SECURITY_HEADERS",
        description="Enable security headers middleware"
    )
    enable_rate_limiting: bool = Field(
        default=False,
        env="ENABLE_RATE_LIMITING",
        description="Enable rate limiting (auto-enabled in production)"
    )
    rate_limit_requests: int = Field(
        default=100,
        env="RATE_LIMIT_REQUESTS",
        ge=10,
        le=1000,
        description="Max requests per rate limit window"
    )
    rate_limit_window: int = Field(
        default=300,
        env="RATE_LIMIT_WINDOW",
        ge=60,
        le=3600,
        description="Rate limit window in seconds"
    )
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "forbid"  # Prevent extra fields for security
    
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
        if hasattr(info, 'data') and info.data and info.data.get('environment') == Environment.DEVELOPMENT:
            return True
        return v
    
    @field_validator('reload', mode='before')
    @classmethod
    def validate_reload(cls, v, info):
        """Set reload=True automatically for development environment."""
        if hasattr(info, 'data') and info.data and info.data.get('environment') == Environment.DEVELOPMENT:
            return True
        return v
    
    @field_validator('enable_rate_limiting', mode='before')
    @classmethod
    def validate_rate_limiting(cls, v, info):
        """Enable rate limiting automatically in production."""
        if hasattr(info, 'data') and info.data and info.data.get('environment') == Environment.PRODUCTION:
            return True
        return v
    
    @field_validator('cors_origins', mode='before')
    @classmethod
    def validate_cors_origins_security(cls, v, info):
        """Validate CORS origins for production security."""
        if isinstance(v, str):
            origins = [origin.strip() for origin in v.split(',') if origin.strip()]
        else:
            origins = v or []
        
        # In production, block wildcard origins
        if hasattr(info, 'data') and info.data and info.data.get('environment') == Environment.PRODUCTION:
            if '*' in origins:
                print("[security] WARNING: Wildcard CORS origin (*) blocked in production")
                origins = [origin for origin in origins if origin != '*']
        
        return origins
    
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
    
    @property
    def has_openai_key(self) -> bool:
        """Check if OpenAI API key is configured."""
        return bool(self.openai_api_key and self.openai_api_key.strip())
    
    @property
    def is_secure_environment(self) -> bool:
        """Check if running in a secure environment (production/staging)."""
        return self.environment in [Environment.PRODUCTION]
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a clean list."""
        if self.is_development:
            # Development: Allow localhost variants
            return [
                "http://localhost:3000",
                "http://localhost:5173",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173"
            ] + self.cors_origins
        return self.cors_origins
    
    def create_vector_store_dir(self) -> None:
        """Create vector store directory if it doesn't exist."""
        self.vector_store_path.mkdir(parents=True, exist_ok=True)


def load_settings() -> Settings:
    """
    Load application settings with enhanced .env file discovery.
    
    Returns:
        Settings: Configured settings instance
    """
    # Enhanced .env file loading with diagnostics
    try:
        dotenv_path = find_dotenv(usecwd=True)
        if dotenv_path:
            print(f"[config] Located .env file at: {dotenv_path}")
        else:
            print("[config] No .env file discovered")
        
        loaded = load_dotenv(dotenv_path or None)
        print(f"[config] load_dotenv loaded={loaded}")
        
    except Exception as e:
        # Non-fatal; continue with existing environment
        print(f"[config] dotenv load error: {e}")
    
    # Immediate post-load inspection (masked)
    raw_key = os.getenv("OPENAI_API_KEY", "")
    if raw_key:
        print(f"[config] OPENAI_API_KEY present (len={len(raw_key)} prefix={raw_key[:7]}*** masked)")
    else:
        print("[config] OPENAI_API_KEY not found in environment")
    
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
        print(f"[config] OpenAI API key configured: {settings.has_openai_key}")
        
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
    
    Returns:
        Settings: Global settings instance
    """
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


def require_openai_api_key() -> str:
    """
    Get OpenAI API key with validation.
    
    Returns:
        str: Valid OpenAI API key
        
    Raises:
        ValueError: If API key is not configured
    """
    settings = get_settings()
    if not settings.has_openai_key:
        raise ValueError("OPENAI_API_KEY not configured. Please configure your OpenAI API key.")
    return settings.openai_api_key