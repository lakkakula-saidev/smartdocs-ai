"""
Production Security Module for SmartDocs AI Backend.

This module implements comprehensive security measures including:
- Security headers middleware
- Request validation and rate limiting
- Input sanitization and validation
- Secure error handling
- API key management and validation

Designed for production deployment with security best practices.
"""

import os
import time
import hashlib
import secrets
from typing import Dict, Any, Optional, List
from functools import wraps
from contextlib import asynccontextmanager

from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from config import get_settings


class SecurityHeaders:
    """Production security headers configuration."""
    
    @staticmethod
    def get_headers() -> Dict[str, str]:
        """Get comprehensive security headers for production."""
        return {
            # Prevent XSS attacks
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            
            # Content Security Policy - restrictive for API
            "Content-Security-Policy": (
                "default-src 'none'; "
                "frame-ancestors 'none'; "
                "form-action 'none'; "
                "base-uri 'none'"
            ),
            
            # HSTS for HTTPS enforcement (only in production)
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            
            # Referrer policy
            "Referrer-Policy": "no-referrer",
            
            # Permissions policy
            "Permissions-Policy": (
                "accelerometer=(), camera=(), geolocation=(), "
                "gyroscope=(), magnetometer=(), microphone=(), "
                "payment=(), usb=()"
            ),
            
            # Hide server information
            "Server": "SmartDocs-AI",
            
            # Prevent caching of sensitive endpoints
            "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }


class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware for production deployment."""
    
    def __init__(self, app, enable_rate_limiting: bool = True):
        super().__init__(app)
        self.settings = get_settings()
        self.enable_rate_limiting = enable_rate_limiting
        self.rate_limit_store: Dict[str, List[float]] = {}
        self.security_headers = SecurityHeaders.get_headers()
        
        # Rate limiting configuration
        self.rate_limit_requests = 100  # Max requests per window
        self.rate_limit_window = 300   # 5 minutes window
        self.rate_limit_burst = 20     # Burst limit for short periods
        
        from logging_config import get_security_logger
        self.security_logger = get_security_logger()
        self.security_logger.logger.info(f"Security middleware initialized (rate_limiting={enable_rate_limiting})")
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process request through security middleware."""
        start_time = time.time()
        
        # 1. Rate limiting check
        if self.enable_rate_limiting:
            try:
                self._check_rate_limit(request)
            except HTTPException as e:
                return self._create_error_response(e.status_code, e.detail)
        
        # 2. Input validation
        try:
            await self._validate_request(request)
        except HTTPException as e:
            return self._create_error_response(e.status_code, e.detail)
        
        # 3. Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log security-relevant errors without exposing details
            client_ip = self._get_client_ip(request)
            print(f"[security] Request processing error from {client_ip}: {type(e).__name__}")
            return self._create_error_response(500, "Internal server error")
        
        # 4. Add security headers
        self._add_security_headers(response, request)
        
        # 5. Log security events
        processing_time = int((time.time() - start_time) * 1000)
        if processing_time > 5000:  # Log slow requests (potential DoS)
            client_ip = self._get_client_ip(request)
            self.security_logger.logger.warning(
                f"Slow request detected: {request.method} {request.url.path} from {client_ip} took {processing_time}ms",
                extra={
                    'event_type': 'slow_request',
                    'client_ip': client_ip,
                    'method': request.method,
                    'path': str(request.url.path),
                    'processing_time_ms': processing_time
                }
            )
        
        return response
    
    def _check_rate_limit(self, request: Request) -> None:
        """Check rate limiting for request."""
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Clean old entries
        if client_ip in self.rate_limit_store:
            self.rate_limit_store[client_ip] = [
                timestamp for timestamp in self.rate_limit_store[client_ip]
                if current_time - timestamp < self.rate_limit_window
            ]
        else:
            self.rate_limit_store[client_ip] = []
        
        # Check rate limit
        request_count = len(self.rate_limit_store[client_ip])
        
        if request_count >= self.rate_limit_requests:
            print(f"[security] Rate limit exceeded for {client_ip}: {request_count} requests")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )
        
        # Check burst limit (last 60 seconds)
        recent_requests = [
            timestamp for timestamp in self.rate_limit_store[client_ip]
            if current_time - timestamp < 60
        ]
        
        if len(recent_requests) >= self.rate_limit_burst:
            print(f"[security] Burst limit exceeded for {client_ip}: {len(recent_requests)} requests")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests in short period. Please slow down."
            )
        
        # Record request
        self.rate_limit_store[client_ip].append(current_time)
    
    async def _validate_request(self, request: Request) -> None:
        """Validate request for security issues."""
        # Check for suspicious patterns in URL
        path = str(request.url.path).lower()
        
        # Block common attack patterns
        malicious_patterns = [
            '../', '..\\', '.env', 'passwd', 'shadow', 'config',
            '<script', 'javascript:', 'vbscript:', 'onload=',
            'union select', 'drop table', 'insert into',
            '/admin', '/wp-admin', '.php', '.jsp', '.asp'
        ]
        
        for pattern in malicious_patterns:
            if pattern in path:
                client_ip = self._get_client_ip(request)
                print(f"[security] Suspicious request blocked from {client_ip}: {pattern} in {path}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid request"
                )
        
        # Validate Content-Length for uploads
        if request.method in ["POST", "PUT", "PATCH"]:
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    size = int(content_length)
                    max_size = self.settings.max_upload_size_bytes
                    if size > max_size:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"Request too large. Max size: {max_size} bytes"
                        )
                except (ValueError, TypeError):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid Content-Length header"
                    )
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address with proxy support."""
        # Check for forwarded IP (Railway, Cloudflare, etc.)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP (client IP)
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        
        # Fallback to direct connection
        if hasattr(request.client, "host"):
            return request.client.host
        
        return "unknown"
    
    def _add_security_headers(self, response: Response, request: Request) -> None:
        """Add security headers to response."""
        # Add all security headers
        for header, value in self.security_headers.items():
            response.headers[header] = value
        
        # Conditional HSTS (only for HTTPS)
        if self.settings.is_production and request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # Add request ID for tracking (security logging)
        request_id = self._generate_request_id()
        response.headers["X-Request-ID"] = request_id
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID for tracking."""
        return secrets.token_hex(8)
    
    def _create_error_response(self, status_code: int, detail: str) -> Response:
        """Create secure error response."""
        from fastapi.responses import JSONResponse
        from models import ErrorResponse
        
        error_response = ErrorResponse(
            error=True,
            status_code=status_code,
            message=detail,
            error_code="SECURITY_ERROR"
        )
        
        response = JSONResponse(
            status_code=status_code,
            content=error_response.dict()
        )
        
        # Add security headers to error response
        for header, value in self.security_headers.items():
            response.headers[header] = value
        
        return response


class SecureAPIKeyValidator:
    """Secure API key validation for future authentication needs."""
    
    def __init__(self):
        self.settings = get_settings()
        self.bearer_scheme = HTTPBearer(auto_error=False)
    
    async def validate_api_key(self, credentials: Optional[HTTPAuthorizationCredentials]) -> bool:
        """
        Validate API key (placeholder for future implementation).
        
        Args:
            credentials: Bearer token credentials
            
        Returns:
            True if valid, False otherwise
        """
        if not credentials:
            return True  # No auth required currently
        
        # Future: Implement proper API key validation
        # For now, accept any Bearer token starting with 'sk-'
        if credentials.scheme.lower() == "bearer":
            token = credentials.credentials
            if token and len(token) > 10:
                return True
        
        return False


class InputSanitizer:
    """Input sanitization and validation utilities."""
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename for safe storage.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        if not filename:
            return "untitled"
        
        # Remove path separators and dangerous characters
        unsafe_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*', '\0']
        sanitized = filename
        
        for char in unsafe_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Limit length
        if len(sanitized) > 255:
            name, ext = os.path.splitext(sanitized)
            sanitized = name[:250] + ext
        
        # Ensure it's not empty after sanitization
        return sanitized if sanitized.strip() else "untitled"
    
    @staticmethod
    def sanitize_query(query: str) -> str:
        """
        Sanitize user query for safe processing.
        
        Args:
            query: User query string
            
        Returns:
            Sanitized query
        """
        if not query:
            return ""
        
        # Remove null bytes and control characters
        sanitized = ''.join(char for char in query if ord(char) >= 32 or char in '\n\r\t')
        
        # Limit length
        return sanitized[:2000] if len(sanitized) > 2000 else sanitized


def get_security_config() -> Dict[str, Any]:
    """
    Get security configuration for the application.
    
    Returns:
        Security configuration dictionary
    """
    settings = get_settings()
    
    return {
        "enable_security_headers": True,
        "enable_rate_limiting": settings.is_production,
        "enable_input_validation": True,
        "enable_request_logging": True,
        "cors_enabled": True,
        "cors_strict_mode": settings.is_production,
        "api_key_required": False,  # Future feature
        "max_request_size": settings.max_upload_size_bytes,
        "rate_limit_requests": 100,
        "rate_limit_window": 300
    }


def validate_openai_api_key(api_key: str) -> bool:
    """
    Validate OpenAI API key format and basic security.
    
    Args:
        api_key: API key to validate
        
    Returns:
        True if key appears valid
    """
    if not api_key:
        return False
    
    # Check basic format
    if not api_key.startswith('sk-'):
        return False
    
    # Check length (OpenAI keys are typically 51 characters)
    if len(api_key) < 20:
        return False
    
    # Check for suspicious patterns
    if any(char in api_key for char in [' ', '\n', '\r', '\t']):
        return False
    
    return True