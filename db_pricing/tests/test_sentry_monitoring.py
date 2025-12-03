import unittest
from unittest.mock import patch, call

from db_pricing.sentry_monitoring import (
    PriceAnomalySentryMonitor,
)


class TestPriceAnomalySentryMonitor(unittest.TestCase):

    @patch('db_pricing.sentry_monitoring.sentry_sdk')
    def test_set_anomaly_context(self, mock_sentry):
        sample = {"name": "Test Product", "unit": "kg", "change_percent": 25}
        PriceAnomalySentryMonitor.set_anomaly_context("tokopedia", 3, sample=sample)

        # tags and measurements set
        mock_sentry.set_tag.assert_any_call("anomaly_vendor", "tokopedia")
        mock_sentry.set_measurement.assert_any_call("anomalies_detected", 3)

        # context set
        mock_sentry.set_context.assert_called()
        ctx_name, ctx = mock_sentry.set_context.call_args[0]
        self.assertEqual(ctx_name, "anomaly_context")
        self.assertEqual(ctx["vendor"], "tokopedia")
        self.assertIn("sample", ctx)

    @patch('db_pricing.sentry_monitoring.capture_message')
    @patch('db_pricing.sentry_monitoring.sentry_sdk')
    def test_track_save_result_success(self, mock_sentry, mock_capture):
        PriceAnomalySentryMonitor.track_save_result(True, 2, [])

        # Success cases should NOT send any Sentry data
        mock_sentry.set_measurement.assert_not_called()
        mock_sentry.set_tag.assert_not_called()
        mock_capture.assert_not_called()

    @patch('db_pricing.sentry_monitoring.capture_message')
    @patch('db_pricing.sentry_monitoring.sentry_sdk')
    def test_track_save_result_failure(self, mock_sentry, mock_capture):
        PriceAnomalySentryMonitor.track_save_result(False, 0, ["err1", "err2"]) 

        # Only failures send Sentry data
        mock_sentry.set_measurement.assert_any_call("anomalies_saved", 0)
        mock_sentry.set_tag.assert_any_call("anomalies_save_success", "False")
        mock_capture.assert_called()
        # Test breadcrumb addition for errors
        mock_sentry.add_breadcrumb.assert_called()

    @patch('db_pricing.sentry_monitoring.capture_message')
    @patch('db_pricing.sentry_monitoring.sentry_sdk')
    def test_track_apply_result_success(self, mock_sentry, mock_capture):
        PriceAnomalySentryMonitor.track_apply_result(123, True, 1, "Applied successfully")

        # Success cases should NOT send any Sentry data
        mock_sentry.set_tag.assert_not_called()
        mock_sentry.set_measurement.assert_not_called()
        mock_sentry.set_context.assert_not_called()
        mock_capture.assert_not_called()

    @patch('db_pricing.sentry_monitoring.capture_message')
    @patch('db_pricing.sentry_monitoring.sentry_sdk')
    def test_track_apply_result_failure(self, mock_sentry, mock_capture):
        PriceAnomalySentryMonitor.track_apply_result(456, False, 0, "No matching product")

        # Only failures send Sentry data
        mock_sentry.set_tag.assert_any_call("anomaly_apply_success", "False")
        mock_sentry.set_measurement.assert_any_call("anomaly_apply_updated", 0)
        mock_sentry.set_context.assert_called()
        mock_capture.assert_called()

    @patch('db_pricing.sentry_monitoring.capture_message')
    @patch('db_pricing.sentry_monitoring.sentry_sdk')
    def test_track_review_error(self, mock_sentry, mock_capture):
        # Test error tracking for review operations
        PriceAnomalySentryMonitor.track_review_error(
            anomaly_id=789,
            error_message="Anomaly not found",
            context={"requested_status": "approved"}
        )

        # Verify Sentry calls for error tracking
        mock_sentry.set_tag.assert_any_call("anomaly_operation", "review")
        mock_sentry.set_tag.assert_any_call("anomaly_id", "789")
        mock_sentry.set_context.assert_called_with("review_error", {"requested_status": "approved"})
        mock_capture.assert_called_once()

    @patch('db_pricing.sentry_monitoring.capture_exception')
    @patch('db_pricing.sentry_monitoring.sentry_sdk')
    def test_capture_exception(self, mock_sentry, mock_capture):
        err = Exception("boom")
        PriceAnomalySentryMonitor.capture_exception(err, context={"a": 1})

        mock_sentry.set_context.assert_called()
        mock_capture.assert_called()


if __name__ == '__main__':
    unittest.main()
