import sentry_sdk
from sentry_sdk import capture_message, capture_exception
import time
from typing import List, Dict, Any, Optional


class PriceAnomalySentryMonitor:
    """Sentry monitoring helpers for price anomaly lifecycle."""

    @staticmethod
    def set_anomaly_context(vendor: str, anomalies_count: int, sample: Optional[Dict[str, Any]] = None):
        sentry_sdk.set_tag("anomaly_vendor", vendor)
        sentry_sdk.set_measurement("anomalies_detected", anomalies_count)
        context = {
            "vendor": vendor,
            "anomalies_count": anomalies_count,
            "timestamp": time.time()
        }
        if sample:
            # Only include a small, non-sensitive sample
            context["sample"] = {
                "name": sample.get("name"),
                "unit": sample.get("unit"),
                "change_percent": sample.get("change_percent"),
            }
        sentry_sdk.set_context("anomaly_context", context)

    @staticmethod
    def track_save_result(success: bool, saved_count: int, errors: List[str]):
        # Only report failures to Sentry (avoid noisy success messages)
        if not success:
            sentry_sdk.set_measurement("anomalies_saved", saved_count)
            sentry_sdk.set_tag("anomalies_save_success", "False")
            capture_message(f"Anomaly save completed with errors: {len(errors)} errors", level="warning")
            # include up to 5 error breadcrumbs
            for e in errors[:5]:
                sentry_sdk.add_breadcrumb(category="anomaly.save.error", message=e, level="error")

    @staticmethod
    def track_apply_result(anomaly_id: int, success: bool, updated_count: int, message: str = ""):
        # Only report failures to Sentry (apply failures are relevant errors)
        if not success:
            sentry_sdk.set_tag("anomaly_apply_success", "False")
            sentry_sdk.set_measurement("anomaly_apply_updated", updated_count)
            sentry_sdk.set_context("anomaly_apply", {"anomaly_id": anomaly_id, "updated": updated_count, "message": message})
            capture_message(f"Apply anomaly {anomaly_id}: {message}", level="warning")

    @staticmethod
    def track_review_error(anomaly_id: int, error_message: str, context: Optional[Dict[str, Any]] = None):
        """Track errors that occur during review operations."""
        sentry_sdk.set_tag("anomaly_operation", "review")
        sentry_sdk.set_tag("anomaly_id", str(anomaly_id))
        if context:
            sentry_sdk.set_context("review_error", context)
        capture_message(f"Review anomaly {anomaly_id} error: {error_message}", level="error")

    @staticmethod
    def capture_exception(err: Exception, context: Optional[Dict[str, Any]] = None):
        if context:
            sentry_sdk.set_context("anomaly_error_context", context)
        capture_exception(err)
