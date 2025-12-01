"""
Logging utilities for DepoBangunan module.

Provides a standardized logger with:
- Component-based prefixes
- Operation context tracking
- Input sanitization for security
- Consistent formatting
"""

import logging
from typing import Any, Dict, Optional

LOG_NAMESPACE = "api.depobangunan"


def _sanitize_log_input(value: Any) -> Any:
    """Sanitize log input to prevent log injection attacks.
    
    Args:
        value: The value to sanitize
        
    Returns:
        Sanitized value with newlines and carriage returns replaced
    """
    if isinstance(value, str):
        return value.replace("\n", " ").replace("\r", " ")
    return value


class DepoBangunanLogger(logging.LoggerAdapter):
    """Logger adapter for DepoBangunan module.
    
    Provides consistent logging with component tracking and input sanitization.
    
    Example:
        logger = DepoBangunanLogger("html_parser")
        logger.info("Processing items", extra={"operation": "parse"})
        # Output: [depobangunan][component=html_parser][op=parse] Processing items
    """
    
    def __init__(self, component: str, extra: Optional[Dict[str, Any]] = None):
        """Initialize the DepoBangunan logger.
        
        Args:
            component: Component name (e.g., "html_parser", "database_service")
            extra: Optional extra context to include in all log messages
        """
        base_logger = logging.getLogger(LOG_NAMESPACE)
        merged_extra = {"component": component}
        if extra:
            merged_extra.update(extra)
        super().__init__(base_logger, merged_extra)
    
    def process(self, msg, kwargs):
        """Process log message to add depobangunan and component prefixes.
        
        Args:
            msg: The log message
            kwargs: Keyword arguments including optional 'extra' dict
            
        Returns:
            Tuple of (processed_message, updated_kwargs)
        """
        msg = _sanitize_log_input(msg)
        extra = kwargs.pop("extra", {})
        
        # Get component and operation from context
        component = _sanitize_log_input(self.extra.get("component", "depobangunan"))
        operation = extra.get("operation") or self.extra.get("operation")
        
        # Build prefix with depobangunan, component, and optional operation
        prefix_parts = [f"[depobangunan][component={component}]"]
        if operation:
            prefix_parts.append(f"[op={_sanitize_log_input(operation)}]")
        
        prefixed = " ".join(prefix_parts) + f" {msg}"
        kwargs["extra"] = {**self.extra, **extra}
        return prefixed, kwargs
    
    def log(self, level, msg, *args, **kwargs):
        """Log a message with sanitized arguments.
        
        Args:
            level: Log level
            msg: Message to log
            *args: Positional arguments for message formatting
            **kwargs: Keyword arguments including optional 'extra' dict
        """
        if not self.isEnabledFor(level):
            return
        msg, kwargs = self.process(_sanitize_log_input(msg), kwargs)
        clean_args = tuple(_sanitize_log_input(arg) for arg in args)
        self.logger.log(level, msg, *clean_args, **kwargs)


def get_depobangunan_logger(component: str, extra: Optional[Dict[str, Any]] = None) -> DepoBangunanLogger:
    """Get a logger instance for DepoBangunan components.
    
    Args:
        component: Component name (e.g., "html_parser", "database_service", "scraper")
        extra: Optional extra context to include in all log messages
        
    Returns:
        Configured DepoBangunanLogger instance
        
    Example:
        logger = get_depobangunan_logger("scraper")
        logger.info("Scraping started", extra={"operation": "scrape_products"})
        # Output: [depobangunan][component=scraper][op=scrape_products] Scraping started
    """
    return DepoBangunanLogger(component, extra)
