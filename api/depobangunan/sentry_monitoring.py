import sentry_sdk
from sentry_sdk import start_transaction, start_span, capture_message, capture_exception
from functools import wraps
import time
from typing import Any, Callable, Optional, Dict
from .logging_utils import get_depobangunan_logger

logger = get_depobangunan_logger("sentry_monitoring")


class DepoBangunanSentryMonitor:
    """Custom Sentry monitoring for Depo Bangunan scraper operations."""
    
    VENDOR = "depobangunan"
    COMPONENT_SCRAPER = "scraper"
    COMPONENT_PARSER = "parser"
    COMPONENT_HTTP_CLIENT = "http_client"
    COMPONENT_LOCATION = "location_scraper"
    
    @staticmethod
    def set_scraping_context(keyword: str, page: int = 0, additional_data: Optional[Dict] = None):
        """Set context for the current scraping operation."""
        context = {
            "keyword": keyword,
            "page": page,
            "vendor": DepoBangunanSentryMonitor.VENDOR,
            "timestamp": time.time()
        }
        
        if additional_data:
            context.update(additional_data)
        
        sentry_sdk.set_context("scraping_context", context)
        
        # Add tags for filtering in Sentry
        sentry_sdk.set_tag("vendor", DepoBangunanSentryMonitor.VENDOR)
        sentry_sdk.set_tag("search_keyword", keyword)
        sentry_sdk.set_tag("page_number", str(page))
    
    @staticmethod
    def add_breadcrumb(message: str, category: str = "scraping", level: str = "info", data: Optional[Dict] = None):
        """Add a breadcrumb to track execution flow."""
        sentry_sdk.add_breadcrumb(
            category=category,
            message=message,
            level=level,
            data=data or {}
        )
    
    @staticmethod
    def track_scraping_result(result: Dict[str, Any]):
        """Track the result of a scraping operation."""
        # Extract result metrics
        metrics = {
            'products': result.get('products_count', 0),
            'success': result.get('success', False),
            'errors': result.get('errors_count', 0)
        }
        
        # Update Sentry tags and measurements
        sentry_sdk.set_tag("scraping_success", str(metrics['success']))
        sentry_sdk.set_measurement("products_scraped", metrics['products'])
        sentry_sdk.set_measurement("scraping_errors", metrics['errors'])
        
        # Build context data
        context_data = {
            "products_found": metrics['products'],
            "success": metrics['success'],
            "errors": metrics['errors'],
            "timestamp": time.time()
        }
        sentry_sdk.set_context("scraping_result", context_data)
        
        # Log result to Sentry with appropriate level
        log_level = "info" if metrics['success'] else "warning"
        status_text = "completed" if metrics['success'] else "failed"
        
        message_parts = [f"DepoBangunan scraping {status_text}:"]
        message_parts.append(f"{metrics['products']} products found" if metrics['success'] else f"{metrics['errors']} errors")
        
        capture_message(" ".join(message_parts), level=log_level)


def monitor_depobangunan_function(operation_name: str, component: str = DepoBangunanSentryMonitor.COMPONENT_SCRAPER):
    """
    Decorator to monitor individual Depo Bangunan functions.
    
    Usage:
        @monitor_depobangunan_function("scrape_products", "scraper")
        def scrape_products(keyword):
            # function code
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Add breadcrumb
            DepoBangunanSentryMonitor.add_breadcrumb(
                f"Starting {operation_name}",
                category=f"depobangunan.{component}",
                level="info",
                data={"function": func.__name__, "args_count": len(args)}
            )
            
            # Start performance tracking
            with start_span(op=f"depobangunan.{component}", description=operation_name) as span:
                # Add tags
                span.set_tag("vendor", "depobangunan")
                span.set_tag("component", component)
                span.set_tag("operation", operation_name)
                
                start_time = time.time()
                
                try:
                    # Execute function
                    result = func(*args, **kwargs)
                    
                    # Track success
                    execution_time = time.time() - start_time
                    span.set_data("execution_time", execution_time)
                    span.set_data("status", "success")
                    
                    DepoBangunanSentryMonitor.add_breadcrumb(
                        f"Completed {operation_name} in {execution_time:.2f}s",
                        category=f"depobangunan.{component}",
                        level="info"
                    )
                    
                    return result
                    
                except Exception as e:
                    # Track error
                    execution_time = time.time() - start_time
                    span.set_data("execution_time", execution_time)
                    span.set_data("status", "error")
                    span.set_data("error_type", type(e).__name__)
                    
                    # Add error context
                    sentry_sdk.set_context("error_context", {
                        "function": func.__name__,
                        "operation": operation_name,
                        "component": component,
                        "execution_time": execution_time,
                        "error_message": str(e)
                    })
                    
                    DepoBangunanSentryMonitor.add_breadcrumb(
                        f"Error in {operation_name}: {str(e)}",
                        category=f"depobangunan.{component}",
                        level="error"
                    )
                    
                    # Capture exception
                    capture_exception(e)
                    
                    # Re-raise
                    raise
        
        return wrapper
    return decorator


def track_depobangunan_transaction(transaction_name: str):
    """
    Context manager to track a complete Depo Bangunan transaction.
    
    Usage:
        with track_depobangunan_transaction("scrape_depobangunan_products"):
            # scraping code
            pass
    """
    transaction = start_transaction(
        op="scraping.depobangunan",
        name=transaction_name
    )
    # Set tags after transaction is created
    if transaction:
        transaction.set_tag("vendor", "depobangunan")
        transaction.set_tag("transaction_type", "scraping")
    return transaction


class DepoBangunanTaskMonitor:
    """Monitor individual scraping tasks with progress tracking."""
    
    def __init__(self, task_id: str, task_type: str):
        self.task_id = task_id
        self.task_type = task_type
        self.start_time = time.time()
        
        # Set task context
        sentry_sdk.set_tag("task_id", task_id)
        sentry_sdk.set_tag("task_type", task_type)
        
        sentry_sdk.set_context("task_context", {
            "task_id": task_id,
            "task_type": task_type,
            "started_at": self.start_time,
            "vendor": "depobangunan"
        })
        
        DepoBangunanSentryMonitor.add_breadcrumb(
            f"Task started: {task_id}",
            category="task",
            level="info",
            data={"task_type": task_type}
        )
    
    def record_progress(self, items_processed: int, total_items: int, message: str = ""):
        """Record task progress."""
        progress_percent = (items_processed / total_items * 100) if total_items > 0 else 0
        
        sentry_sdk.set_measurement("task_progress", progress_percent)
        
        DepoBangunanSentryMonitor.add_breadcrumb(
            message or f"Progress: {items_processed}/{total_items} ({progress_percent:.1f}%)",
            category="task.progress",
            level="info",
            data={
                "items_processed": items_processed,
                "total_items": total_items,
                "progress_percent": progress_percent
            }
        )
    
    def complete(self, success: bool = True, result_data: Optional[Dict] = None):
        """Mark task as completed."""
        execution_time = time.time() - self.start_time
        
        sentry_sdk.set_measurement("task_duration", execution_time)
        sentry_sdk.set_tag("task_status", "success" if success else "failed")
        
        DepoBangunanSentryMonitor.add_breadcrumb(
            f"Task completed: {self.task_id} ({'success' if success else 'failed'})",
            category="task",
            level="info" if success else "error",
            data={
                "execution_time": execution_time,
                "result": result_data or {}
            }
        )
        
        capture_message(
            f"DepoBangunan task {self.task_id} completed in {execution_time:.2f}s",
            level="info" if success else "warning"
        )
