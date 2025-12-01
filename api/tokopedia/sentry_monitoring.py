import sentry_sdk
from sentry_sdk import start_transaction, start_span, capture_message, capture_exception
from functools import wraps
import time
from typing import Any, Callable, Optional, Dict
import logging

logger = logging.getLogger(__name__)


class TokopediaSentryMonitor:
    """Custom Sentry monitoring for Tokopedia scraper operations."""
    
    VENDOR = "tokopedia"
    COMPONENT_SCRAPER = "scraper"
    COMPONENT_PARSER = "parser"
    COMPONENT_HTTP_CLIENT = "http_client"
    COMPONENT_URL_BUILDER = "url_builder"
    
    @staticmethod
    def _set_context_and_tags(context_name: str, context_data: Dict[str, Any], tags: Optional[Dict[str, str]] = None):
        """Helper to set context and tags atomically."""
        sentry_sdk.set_context(context_name, context_data)
        if tags:
            for key, value in tags.items():
                sentry_sdk.set_tag(key, value)
    
    @staticmethod
    def set_scraping_context(keyword: str, page: int = 0, additional_data: Optional[Dict] = None):
        """Set context for the current scraping operation."""
        context = {
            "keyword": keyword,
            "page": page,
            "vendor": TokopediaSentryMonitor.VENDOR,
            "timestamp": time.time()
        }
        
        if additional_data:
            context.update(additional_data)
        
        tags = {
            "vendor": TokopediaSentryMonitor.VENDOR,
            "search_keyword": keyword,
            "page_number": str(page)
        }
        
        TokopediaSentryMonitor._set_context_and_tags("scraping_context", context, tags)
    
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
    def _set_measurements(measurements: Dict[str, float]):
        """Helper to set multiple measurements at once."""
        for key, value in measurements.items():
            sentry_sdk.set_measurement(key, value)
    
    @staticmethod
    def _capture_result_message(success: bool, success_msg: str, failure_msg: str):
        """Helper to capture appropriate message based on success."""
        # Only capture messages for failures to reduce noise in Sentry.
        if not success:
            capture_message(failure_msg, level="warning")
    
    @staticmethod
    def track_scraping_result(result: Dict[str, Any]):
        """Track the result of a scraping operation."""
        # Only record failures to reduce noise. Do not count successful products.
        success = result.get('success', False)
        errors_count = result.get('errors_count', 0)

        if not success:
            # Set only error-related measurements
            measurements = {
                "scraping_errors": errors_count
            }
            TokopediaSentryMonitor._set_measurements(measurements)
            sentry_sdk.set_tag("scraping_success", "False")

            # Add context for failure
            context = {
                "success": False,
                "errors": errors_count,
                "timestamp": time.time()
            }
            sentry_sdk.set_context("scraping_result", context)

            # Log failure to Sentry
            failure_msg = f"Tokopedia scraping failed with {errors_count} errors"
            TokopediaSentryMonitor._capture_result_message(False, "", failure_msg)
    
    @staticmethod
    def track_database_operation(operation: str, result: Dict[str, Any]):
        """Track database operation results."""
        # Only record database failures to reduce noise.
        success = result.get('success', False)
        anomalies_count = len(result.get('anomalies', []))

        if not success:
            # Set only anomaly/error related measurements
            measurements = {
                "anomalies_detected": anomalies_count
            }
            TokopediaSentryMonitor._set_measurements(measurements)

            # Add failure context
            context = {
                "operation": operation,
                "success": False,
                "anomalies": anomalies_count,
                "timestamp": time.time()
            }
            sentry_sdk.set_context("database_operation", context)

            # Log failure
            failure_msg = f"Tokopedia database {operation} failed"
            TokopediaSentryMonitor._capture_result_message(False, "", failure_msg)


def monitor_tokopedia_function(operation_name: str, component: str = TokopediaSentryMonitor.COMPONENT_SCRAPER):
    """
    Decorator to monitor individual Tokopedia functions.
    
    Usage:
        @monitor_tokopedia_function("scrape_products", "scraper")
        def scrape_products(keyword):
            # function code
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Add breadcrumb
            TokopediaSentryMonitor.add_breadcrumb(
                f"Starting {operation_name}",
                category=f"tokopedia.{component}",
                level="info",
                data={"function": func.__name__, "args_count": len(args)}
            )
            
            # Start performance tracking
            with start_span(op=f"tokopedia.{component}", description=operation_name) as span:
                # Add tags
                span.set_tag("vendor", "tokopedia")
                span.set_tag("component", component)
                span.set_tag("operation", operation_name)
                
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    
                    # Track success
                    _track_span_completion(span, execution_time, "success", operation_name, component)
                    
                    return result
                    
                except Exception as e:
                    execution_time = time.time() - start_time
                    
                    # Track error
                    _track_span_completion(span, execution_time, "error", operation_name, component, e)
                    
                    # Re-raise
                    raise
        
        return wrapper
    return decorator


def _track_span_completion(span, execution_time: float, status: str, operation_name: str, component: str, exception: Optional[Exception] = None):
    """Helper to track span completion with consistent error/success handling."""
    span.set_data("execution_time", execution_time)
    span.set_data("status", status)
    
    if status == "success":
        # Do not emit breadcrumbs for successful operations to reduce Sentry noise.
        # Only execution metadata is attached to the span; no Sentry events for success.
        pass
    else:
        span.set_data("error_type", type(exception).__name__)
        
        # Add error context
        sentry_sdk.set_context("error_context", {
            "operation": operation_name,
            "component": component,
            "execution_time": execution_time,
            "error_message": str(exception)
        })
        
        TokopediaSentryMonitor.add_breadcrumb(
            f"Error in {operation_name}: {str(exception)}",
            category=f"tokopedia.{component}",
            level="error"
        )
        
        # Capture exception
        capture_exception(exception)


def track_tokopedia_transaction(transaction_name: str):
    """
    Context manager to track a complete Tokopedia transaction.
    
    Usage:
        with track_tokopedia_transaction("scrape_tokopedia_products"):
            # scraping code
            pass
    """
    transaction = start_transaction(
        op="scraping.tokopedia",
        name=transaction_name
    )
    # Set tags after transaction is created
    if transaction:
        transaction.set_tag("vendor", "tokopedia")
        transaction.set_tag("transaction_type", "scraping")
    return transaction


class TokopediaTaskMonitor:
    """Monitor individual scraping tasks with progress tracking."""
    
    def __init__(self, task_id: str, task_type: str):
        self.task_id = task_id
        self.task_type = task_type
        self.start_time = time.time()
        
        # Set task context and tags
        tags = {
            "task_id": task_id,
            "task_type": task_type
        }
        context = {
            "task_id": task_id,
            "task_type": task_type,
            "started_at": self.start_time,
            "vendor": "tokopedia"
        }
        TokopediaSentryMonitor._set_context_and_tags("task_context", context, tags)
        
        TokopediaSentryMonitor.add_breadcrumb(
            f"Task started: {task_id}",
            category="task",
            level="info",
            data={"task_type": task_type}
        )
    
    def record_progress(self, items_processed: int, total_items: int, message: str = ""):
        """Record task progress."""
        progress_percent = (items_processed / total_items * 100) if total_items > 0 else 0
        
        sentry_sdk.set_measurement("task_progress", progress_percent)
        
        TokopediaSentryMonitor.add_breadcrumb(
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
        # Only report to Sentry when the task failed to reduce noise.
        if not success:
            sentry_sdk.set_measurement("task_duration", execution_time)
            sentry_sdk.set_tag("task_status", "failed")

            TokopediaSentryMonitor.add_breadcrumb(
                f"Task completed: {self.task_id} (failed)",
                category="task",
                level="warning",
                data={
                    "execution_time": execution_time,
                    "result": result_data or {}
                }
            )

            capture_message(
                f"Tokopedia task {self.task_id} failed after {execution_time:.2f}s",
                level="warning"
            )
