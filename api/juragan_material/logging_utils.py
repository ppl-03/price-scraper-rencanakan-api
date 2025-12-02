import logging
from typing import Any, Dict, Optional

LOG_NAMESPACE = "api.juragan_material"


def _sanitize_log_input(value: Any) -> Any:
    """Sanitize log input to prevent log injection attacks."""
    if isinstance(value, str):
        return value.replace("\n", " ").replace("\r", " ")
    return value


class JuraganMaterialLogger(logging.LoggerAdapter):
    """
    Custom logger adapter for Juragan Material component.
    
    Provides consistent logging format with component and operation context.
    Automatically sanitizes input to prevent log injection attacks.
    
    Example usage:
        logger = get_juragan_material_logger("scraper")
        logger.info("Scraped %d products", count)
        logger.error("Failed to parse", extra={"operation": "parse_html"})
    """
    
    def __init__(self, component: str, extra: Optional[Dict[str, Any]] = None):
        base_logger = logging.getLogger(LOG_NAMESPACE)
        merged_extra = {"component": component}
        if extra:
            merged_extra.update(extra)
        super().__init__(base_logger, merged_extra)

    def process(self, msg, kwargs):
        """Process log message with component and operation prefixes."""
        msg = _sanitize_log_input(msg)
        extra = kwargs.pop("extra", {})
        component = _sanitize_log_input(self.extra.get("component", "juragan_material"))
        operation = extra.get("operation") or self.extra.get("operation")
        
        prefix_parts = [f"[juragan_material][component={component}]"]
        if operation:
            prefix_parts.append(f"[op={_sanitize_log_input(operation)}]")
        
        prefixed = " ".join(prefix_parts) + f" {msg}"
        kwargs["extra"] = {**self.extra, **extra}
        return prefixed, kwargs

    def log(self, level, msg, *args, **kwargs):
        """Log with sanitization and proper formatting."""
        if not self.isEnabledFor(level):
            return
        msg, kwargs = self.process(_sanitize_log_input(msg), kwargs)
        clean_args = tuple(_sanitize_log_input(arg) for arg in args)
        self.logger.log(level, msg, *clean_args, **kwargs)


def get_juragan_material_logger(component: str, extra: Optional[Dict[str, Any]] = None) -> JuraganMaterialLogger:
    """
    Get a logger instance for Juragan Material component.
    
    Args:
        component: Name of the component (e.g., "scraper", "database", "parser")
        extra: Optional extra context to include in all log messages
        
    Returns:
        Configured JuraganMaterialLogger instance
    """
    return JuraganMaterialLogger(component, extra)
