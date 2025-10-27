"""
Production Logging Configuration for SmartDocs AI Backend.

Implements structured, secure logging with:
- JSON formatting for production
- Log level management
- Sensitive data filtering
- Security event logging
- Performance monitoring

Designed for production deployment with observability integration.
"""

import logging
import logging.handlers
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from config import get_settings


class SensitiveDataFilter(logging.Filter):
    """Filter to remove sensitive data from log records."""
    
    SENSITIVE_KEYS = [
        'password', 'passwd', 'pwd', 'secret', 'token', 'key', 'api_key',
        'authorization', 'auth', 'credential', 'openai_api_key'
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter sensitive data from log record."""
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = self._sanitize_message(record.msg)
        
        if hasattr(record, 'args') and record.args:
            record.args = tuple(self._sanitize_value(arg) for arg in record.args)
        
        return True
    
    def _sanitize_message(self, message: str) -> str:
        """Sanitize sensitive data in message string."""
        # Basic pattern matching for sensitive data
        import re
        
        # API key patterns
        message = re.sub(r'sk-[a-zA-Z0-9]{20,}', 'sk-***REDACTED***', message)
        message = re.sub(r'Bearer [a-zA-Z0-9]{20,}', 'Bearer ***REDACTED***', message)
        
        # Generic sensitive patterns
        for key in self.SENSITIVE_KEYS:
            pattern = rf'{key}["\']?\s*[:=]\s*["\']?[^\s"\']+["\']?'
            message = re.sub(pattern, f'{key}=***REDACTED***', message, flags=re.IGNORECASE)
        
        return message
    
    def _sanitize_value(self, value: Any) -> Any:
        """Sanitize individual values."""
        if isinstance(value, str):
            return self._sanitize_message(value)
        elif isinstance(value, dict):
            return {k: ('***REDACTED***' if any(sk in str(k).lower() for sk in self.SENSITIVE_KEYS) else v) 
                   for k, v in value.items()}
        return value


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra
        self.hostname = os.getenv('HOSTNAME', 'localhost')
        
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Base log structure
        log_entry = {
            'timestamp': datetime.utcfromtimestamp(record.created).isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'hostname': self.hostname,
            'process_id': os.getpid(),
            'thread_id': record.thread
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if enabled
        if self.include_extra:
            extra_fields = {
                k: v for k, v in record.__dict__.items() 
                if k not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                           'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                           'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                           'thread', 'threadName', 'processName', 'process', 'getMessage']
            }
            if extra_fields:
                log_entry['extra'] = extra_fields
        
        return json.dumps(log_entry, default=str, separators=(',', ':'))


class SecurityLogger:
    """Specialized logger for security events."""
    
    def __init__(self, name: str = "security"):
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self):
        """Setup security logger with appropriate handlers."""
        if not self.logger.handlers:
            settings = get_settings()
            
            # Console handler for development
            if settings.is_development:
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setFormatter(logging.Formatter(
                    '[%(asctime)s] [SECURITY] %(levelname)s: %(message)s'
                ))
                self.logger.addHandler(console_handler)
            
            # File handler for production
            if settings.is_production:
                log_dir = Path("/app/logs")
                log_dir.mkdir(exist_ok=True)
                
                file_handler = logging.handlers.RotatingFileHandler(
                    log_dir / "security.log",
                    maxBytes=10*1024*1024,  # 10MB
                    backupCount=5
                )
                file_handler.setFormatter(JSONFormatter())
                self.logger.addHandler(file_handler)
            
            self.logger.setLevel(logging.INFO)
            self.logger.addFilter(SensitiveDataFilter())
    
    def log_auth_attempt(self, client_ip: str, success: bool, details: Dict[str, Any] = None):
        """Log authentication attempt."""
        self.logger.info(
            f"Authentication attempt from {client_ip}: {'SUCCESS' if success else 'FAILED'}",
            extra={
                'event_type': 'auth_attempt',
                'client_ip': client_ip,
                'success': success,
                'details': details or {}
            }
        )
    
    def log_rate_limit(self, client_ip: str, endpoint: str, request_count: int):
        """Log rate limit violation."""
        self.logger.warning(
            f"Rate limit exceeded: {client_ip} made {request_count} requests to {endpoint}",
            extra={
                'event_type': 'rate_limit_exceeded',
                'client_ip': client_ip,
                'endpoint': endpoint,
                'request_count': request_count
            }
        )
    
    def log_suspicious_request(self, client_ip: str, pattern: str, request_path: str):
        """Log suspicious request pattern."""
        self.logger.warning(
            f"Suspicious request blocked from {client_ip}: {pattern} in {request_path}",
            extra={
                'event_type': 'suspicious_request',
                'client_ip': client_ip,
                'pattern': pattern,
                'request_path': request_path
            }
        )
    
    def log_error(self, error_id: str, client_ip: str, error_type: str, details: Dict[str, Any] = None):
        """Log security-relevant error."""
        self.logger.error(
            f"Error [{error_id}] from {client_ip}: {error_type}",
            extra={
                'event_type': 'security_error',
                'error_id': error_id,
                'client_ip': client_ip,
                'error_type': error_type,
                'details': details or {}
            }
        )


def setup_logging() -> None:
    """Setup application-wide logging configuration."""
    settings = get_settings()
    
    # Get log level from environment
    log_level = getattr(logging, settings.environment.upper() == 'DEVELOPMENT' and 'DEBUG' or 'INFO')
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Setup handlers based on environment
    if settings.is_development:
        # Development: Console logging with simple format
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(
            '[%(asctime)s] %(name)s [%(levelname)s]: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        root_logger.addHandler(console_handler)
    else:
        # Production: JSON logging to stdout (for container logging)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(console_handler)
        
        # Also log to file if directory exists
        log_dir = Path("/app/logs")
        if log_dir.exists() or log_dir.parent.exists():
            try:
                log_dir.mkdir(exist_ok=True)
                
                # Application log file
                file_handler = logging.handlers.RotatingFileHandler(
                    log_dir / "application.log",
                    maxBytes=50*1024*1024,  # 50MB
                    backupCount=10
                )
                file_handler.setFormatter(JSONFormatter())
                root_logger.addHandler(file_handler)
                
            except (OSError, PermissionError) as e:
                print(f"[logging] Warning: Could not setup file logging: {e}")
    
    # Add sensitive data filter to all handlers
    sensitive_filter = SensitiveDataFilter()
    for handler in root_logger.handlers:
        handler.addFilter(sensitive_filter)
    
    # Configure specific loggers
    # Reduce noise from external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('chromadb').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    
    print(f"[logging] Logging configured for {settings.environment} environment (level: {logging.getLevelName(log_level)})")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name."""
    return logging.getLogger(name)


def get_security_logger() -> SecurityLogger:
    """Get the security logger instance."""
    return SecurityLogger()


# Performance logging utility
class PerformanceLogger:
    """Logger for performance metrics and monitoring."""
    
    def __init__(self, name: str = "performance"):
        self.logger = logging.getLogger(name)
    
    def log_request_performance(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: int,
        client_ip: Optional[str] = None
    ):
        """Log request performance metrics."""
        self.logger.info(
            f"{method} {path} -> {status_code} ({duration_ms}ms)",
            extra={
                'event_type': 'request_performance',
                'method': method,
                'path': path,
                'status_code': status_code,
                'duration_ms': duration_ms,
                'client_ip': client_ip
            }
        )
    
    def log_slow_operation(
        self,
        operation: str,
        duration_ms: int,
        threshold_ms: int = 1000,
        details: Dict[str, Any] = None
    ):
        """Log slow operations that exceed threshold."""
        if duration_ms > threshold_ms:
            self.logger.warning(
                f"Slow operation detected: {operation} took {duration_ms}ms (threshold: {threshold_ms}ms)",
                extra={
                    'event_type': 'slow_operation',
                    'operation': operation,
                    'duration_ms': duration_ms,
                    'threshold_ms': threshold_ms,
                    'details': details or {}
                }
            )


def get_performance_logger() -> PerformanceLogger:
    """Get the performance logger instance."""
    return PerformanceLogger()


# Initialize logging on module import
if 'pytest' not in sys.modules:  # Skip during testing
    setup_logging()