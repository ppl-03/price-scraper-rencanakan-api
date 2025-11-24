import sentry_sdk
from sentry_sdk import start_transaction, start_span, capture_message, capture_exception
from functools import wraps
import time
from typing import Any, Callable, Optional, Dict
import logging

logger = logging.getLogger(__name__)


class JuraganMaterialSentryMonitor:
    """Custom Sentry monitoring for Juragan Material scraper operations."""
    
    VENDOR = "juragan_material"
    COMPONENT_SCRAPER = "scraper"
    COMPONENT_PARSER = "parser"
    COMPONENT_HTTP_CLIENT = "http_client"
    COMPONENT_DATABASE = "database"
    
    @staticmethod
    def set_scraping_context(keyword: str, page: int = 0, additional_data: Optional[Dict] = None):
        """Set context for the current scraping operation."""
        context = {
            "keyword": keyword,
            "page": page,
            "vendor": JuraganMaterialSentryMonitor.VENDOR,
            "timestamp": time.time()
        }
        
        if additional_data:
            context.update(additional_data)
        
        sentry_sdk.set_context("scraping_context", context)
        
        # Add tags for filtering in Sentry
        sentry_sdk.set_tag("vendor", JuraganMaterialSentryMonitor.VENDOR)
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
        products_count = result.get('products_count', 0)
        success = result.get('success', False)
        errors_count = result.get('errors_count', 0)
        
        # Set metrics
        sentry_sdk.set_tag("scraping_success", str(success))
        sentry_sdk.set_measurement("products_scraped", products_count)
        sentry_sdk.set_measurement("scraping_errors", errors_count)
        
        # Add context
        sentry_sdk.set_context("scraping_result", {
            "products_found": products_count,
            "success": success,
            "errors": errors_count,
            "timestamp": time.time()
        })
        
        # Log to Sentry
        if success:
            capture_message(
                f"Juragan Material scraping completed: {products_count} products found",
                level="info"
            )
        else:
            capture_message(
                f"Juragan Material scraping failed with {errors_count} errors",
                level="warning"
            )
    
    @staticmethod
    def track_database_operation(operation: str, result: Dict[str, Any]):
        """Track database save operations."""
        success = result.get('success', False)
        inserted = result.get('inserted', 0)
        updated = result.get('updated', 0)
        categorized = result.get('categorized', 0)
        
        # Set metrics
        sentry_sdk.set_measurement("db_inserted", inserted)
        sentry_sdk.set_measurement("db_updated", updated)
        sentry_sdk.set_measurement("db_categorized", categorized)
        
        # Add context
        sentry_sdk.set_context("database_operation", {
            "operation": operation,
            "success": success,
            "inserted": inserted,
            "updated": updated,
            "categorized": categorized,
            "timestamp": time.time()
        })
        
        # Add breadcrumb
        JuraganMaterialSentryMonitor.add_breadcrumb(
            f"Database {operation}: {inserted} inserted, {updated} updated, {categorized} categorized",
            category="juragan_material.database",
            level="info" if success else "error",
            data={
                "operation": operation,
                "inserted": inserted,
                "updated": updated,
                "categorized": categorized
            }
        )


def monitor_juragan_material_function(operation_name: str, component: str = JuraganMaterialSentryMonitor.COMPONENT_SCRAPER):
    """
    Decorator to monitor individual Juragan Material functions.
    
    Usage:
        @monitor_juragan_material_function("scrape_products", "scraper")
        def scrape_products(keyword):
            # function code
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Add breadcrumb
            JuraganMaterialSentryMonitor.add_breadcrumb(
                f"Starting {operation_name}",
                category=f"juragan_material.{component}",
                level="info",
                data={"function": func.__name__, "args_count": len(args)}
            )
            
            # Start performance tracking
            with start_span(op=f"juragan_material.{component}", description=operation_name) as span:
                # Add tags
                span.set_tag("vendor", "juragan_material")
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
                    
                    JuraganMaterialSentryMonitor.add_breadcrumb(
                        f"Completed {operation_name} in {execution_time:.2f}s",
                        category=f"juragan_material.{component}",
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
                    
                    JuraganMaterialSentryMonitor.add_breadcrumb(
                        f"Error in {operation_name}: {str(e)}",
                        category=f"juragan_material.{component}",
                        level="error"
                    )
                    
                    # Capture exception
                    capture_exception(e)
                    
                    # Re-raise
                    raise
        
        return wrapper
    return decorator


def track_juragan_material_transaction(transaction_name: str):
    """
    Context manager to track a complete Juragan Material transaction.
    
    Usage:
        with track_juragan_material_transaction("scrape_juragan_material_products"):
            # scraping code
            pass
    """
    transaction = start_transaction(
        op="scraping.juragan_material",
        name=transaction_name
    )
    # Set tags after transaction is created
    if transaction:
        transaction.set_tag("vendor", "juragan_material")
        transaction.set_tag("transaction_type", "scraping")
    return transaction


class JuraganMaterialTaskMonitor:
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
            "vendor": "juragan_material"
        })
        
        JuraganMaterialSentryMonitor.add_breadcrumb(
            f"Task started: {task_id}",
            category="task",
            level="info",
            data={"task_type": task_type}
        )
    
    def record_progress(self, items_processed: int, total_items: int, message: str = ""):
        """Record task progress."""
        progress_percent = (items_processed / total_items * 100) if total_items > 0 else 0
        
        sentry_sdk.set_measurement("task_progress", progress_percent)
        
        JuraganMaterialSentryMonitor.add_breadcrumb(
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
        
        JuraganMaterialSentryMonitor.add_breadcrumb(
            f"Task completed: {self.task_id} ({'success' if success else 'failed'})",
            category="task",
            level="info" if success else "error",
            data={
                "execution_time": execution_time,
                "result": result_data or {}
            }
        )
        
        capture_message(
            f"Juragan Material task {self.task_id} completed in {execution_time:.2f}s",
            level="info" if success else "warning"
        )
