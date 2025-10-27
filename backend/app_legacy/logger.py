"""
Structured logging configuration for SmartDocs AI Backend.

This module provides centralized logging setup with support for both
structured (JSON) and simple text formats, configurable log levels,
and FastAPI integration.
"""

import logging
import logging.config
import sys
from datetime import datetime
from typing import Dict, Any, Optional
import json
import traceback

from .config import get_settings, LogLevel


class StructuredFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.
    
    Outputs log records as JSON objects with consistent field names
    and additional context information.
    """
    
    def __init__(self, include_extra: bool = True):
        """
        Initialize the structured formatter.
        
        Args:
            include_extra: Whether to include extra fields from log records
        """
        super().__init__()
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON formatted log entry
        """
        # Base log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields if enabled
        if self.include_extra:
            # Get all extra attributes (those not in standard LogRecord)
            standard_attrs = {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
                'module', 'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                'thread', 'threadName', 'processName', 'process', 'getMessage',
                'exc_info', 'exc_text', 'stack_info', 'taskName'
            }
            
            extra_fields = {}
            for key, value in record.__dict__.items():
                if key not in standard_attrs and not key.startswith('_'):
                    extra_fields[key] = value
            
            if extra_fields:
                log_entry["extra"] = extra_fields
        
        return json.dumps(log_entry, ensure_ascii=False, default=str)


class SimpleFormatter(logging.Formatter):
    """
    Simple text formatter with color support for development.
    """
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def __init__(self, use_colors: bool = True):
        """
        Initialize the simple formatter.
        
        Args:
            use_colors: Whether to use ANSI color codes
        """
        super().__init__()
        self.use_colors = use_colors and sys.stdout.isatty()
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record as simple text.
        
        Args:
            record: Log record to format
            
        Returns:
            Formatted log entry
        """
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        level = record.levelname
        logger_name = record.name
        message = record.getMessage()
        location = f"{record.module}:{record.funcName}:{record.lineno}"
        
        if self.use_colors:
            color = self.COLORS.get(level, '')
            reset = self.COLORS['RESET']
            level = f"{color}{level}{reset}"
        
        formatted = f"{timestamp} [{level}] {logger_name} - {message} ({location})"
        
        # Add exception information if present
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
        
        return formatted


def setup_logging(
    log_level: Optional[str] = None,
    log_format: Optional[str] = None,
    logger_name: str = "smartdocs"
) -> logging.Logger:
    """
    Set up application logging with configuration from settings.
    
    Args:
        log_level: Override log level from settings
        log_format: Override log format from settings ('structured' or 'simple')
        logger_name: Base logger name
        
    Returns:
        Configured logger instance
    """
    settings = get_settings()
    
    # Use provided overrides or fallback to settings
    level = log_level or settings.log_level.value
    format_type = log_format or settings.log_format
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    # Set formatter based on format type
    if format_type.lower() == 'structured':
        formatter = StructuredFormatter()
    else:
        # Use colors in development, plain text in production
        use_colors = settings.is_development
        formatter = SimpleFormatter(use_colors=use_colors)
    
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger.setLevel(numeric_level)
    root_logger.addHandler(console_handler)
    
    # Create and return application logger
    app_logger = logging.getLogger(logger_name)
    
    # Disable propagation to prevent duplicate logs
    app_logger.propagate = False
    app_logger.addHandler(console_handler)
    app_logger.setLevel(numeric_level)
    
    return app_logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance with optional name suffix.
    
    Args:
        name: Optional logger name suffix (e.g., 'api', 'services')
        
    Returns:
        Logger instance
    """
    if name:
        logger_name = f"smartdocs.{name}"
    else:
        logger_name = "smartdocs"
    
    return logging.getLogger(logger_name)


class LoggerMixin:
    """
    Mixin class to add logging capabilities to any class.
    
    Provides a `logger` property that returns a logger instance
    named after the class.
    """
    
    @property
    def logger(self) -> logging.Logger:
        """Get a logger for this class."""
        class_name = self.__class__.__name__.lower()
        return get_logger(class_name)


def log_function_call(
    logger: Optional[logging.Logger] = None,
    level: str = "DEBUG",
    include_args: bool = False,
    include_result: bool = False
):
    """
    Decorator to log function calls with optional arguments and results.
    
    Args:
        logger: Logger to use (defaults to function's module logger)
        level: Log level for the messages
        include_args: Whether to log function arguments
        include_result: Whether to log function return value
        
    Example:
        @log_function_call(include_args=True)
        def process_document(doc_id: str) -> dict:
            return {"status": "processed"}
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Get logger
            if logger is None:
                func_logger = get_logger(func.__module__)
            else:
                func_logger = logger
            
            # Get numeric log level
            numeric_level = getattr(logging, level.upper(), logging.DEBUG)
            
            # Log function entry
            log_data = {
                "function": func.__name__,
                "action": "called"
            }
            
            if include_args and (args or kwargs):
                log_data["args"] = {
                    "positional": args if args else None,
                    "keyword": kwargs if kwargs else None
                }
            
            func_logger.log(numeric_level, f"Calling {func.__name__}", extra=log_data)
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Log successful completion
                completion_data = {
                    "function": func.__name__,
                    "action": "completed",
                    "success": True
                }
                
                if include_result:
                    completion_data["result"] = result
                
                func_logger.log(numeric_level, f"Completed {func.__name__}", extra=completion_data)
                
                return result
                
            except Exception as e:
                # Log exception
                error_data = {
                    "function": func.__name__,
                    "action": "failed",
                    "success": False,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
                
                func_logger.error(f"Failed {func.__name__}: {e}", extra=error_data, exc_info=True)
                raise
        
        return wrapper
    return decorator


# Context manager for adding extra context to logs
class LogContext:
    """
    Context manager for adding extra fields to all log records within a block.
    
    Example:
        with LogContext(request_id="req_123", user_id="user_456"):
            logger.info("Processing request")  # Will include request_id and user_id
    """
    
    def __init__(self, **context):
        """
        Initialize log context.
        
        Args:
            **context: Key-value pairs to add to log records
        """
        self.context = context
        self.old_factory = logging.getLogRecordFactory()
    
    def __enter__(self):
        """Enter the context."""
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context."""
        logging.setLogRecordFactory(self.old_factory)


# Initialize logging on module import
def _initialize_logging():
    """Initialize logging when module is imported."""
    try:
        setup_logging()
    except Exception as e:
        # Fallback to basic logging if setup fails
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        print(f"[logger] Failed to setup structured logging, using basic config: {e}")


# Initialize logging when module is imported
_initialize_logging()

# Export main logger instance
logger = get_logger()