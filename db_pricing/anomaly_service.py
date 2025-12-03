# db_pricing/anomaly_service.py
"""
Service for handling price anomaly notifications.
Saves detected price anomalies to the database for review.
"""

from typing import List, Dict, Any, Optional
from django.db import transaction, connection
from django.utils import timezone
from db_pricing.models import PriceAnomaly
import logging
from db_pricing.sentry_monitoring import PriceAnomalySentryMonitor

logger = logging.getLogger(__name__)

# Error message constants
ERROR_ANOMALY_NOT_FOUND = 'Anomaly not found'
ERROR_NO_MATCHING_PRODUCT = 'No matching product found to update'


class PriceAnomalyService:
    """Service to save and manage price anomalies detected during scraping"""
    
    VENDOR_MAP = {
        'gemilang': 'gemilang',
        'mitra10': 'mitra10',
        'tokopedia': 'tokopedia',
        'depobangunan': 'depobangunan',
        'juragan_material': 'juragan_material',
    }
    
    @classmethod
    def _validate_vendor(cls, vendor: str) -> Optional[str]:
        """Validate vendor exists in VENDOR_MAP. Returns error message if invalid."""
        if vendor not in cls.VENDOR_MAP:
            return f"Invalid vendor: {vendor}"
        return None
    
    @classmethod
    def _set_sentry_context(cls, vendor: str, anomalies: List[Dict[str, Any]]) -> None:
        """Set Sentry context for anomaly batch. Silent failure."""
        try:
            sample = anomalies[0] if anomalies else None
            PriceAnomalySentryMonitor.set_anomaly_context(vendor, len(anomalies), sample=sample)
        except Exception:
            logger.debug("Failed to set anomaly Sentry context")
    
    @classmethod
    def _validate_anomaly_fields(cls, anomaly: Dict[str, Any]) -> Optional[str]:
        """Validate required fields. Returns error message if invalid."""
        product_name = anomaly.get('name', '')
        product_url = anomaly.get('url', '')
        
        if not product_name or not product_url:
            return f"Missing required fields for anomaly: {anomaly}"
        return None
    
    @classmethod
    def _create_anomaly_record(cls, vendor: str, anomaly: Dict[str, Any]) -> None:
        """Create a single PriceAnomaly database record."""
        PriceAnomaly.objects.create(
            vendor=cls.VENDOR_MAP[vendor],
            product_name=anomaly.get('name', ''),
            product_url=anomaly.get('url', ''),
            unit=anomaly.get('unit', ''),
            location=anomaly.get('location', ''),
            old_price=anomaly.get('old_price', 0),
            new_price=anomaly.get('new_price', 0),
            change_percent=anomaly.get('change_percent', 0),
            status='pending',
            detected_at=timezone.now()
        )
    
    @classmethod
    def _log_saved_anomaly(cls, vendor: str, anomaly: Dict[str, Any]) -> None:
        """Log successful anomaly save."""
        logger.info(
            f"Saved price anomaly for {vendor}: {anomaly.get('name', '')} "
            f"({anomaly.get('old_price', 0)} -> {anomaly.get('new_price', 0)}, "
            f"{anomaly.get('change_percent', 0)}%)"
        )
    
    @classmethod
    def _handle_anomaly_save_error(cls, anomaly: Dict[str, Any], exception: Exception, errors: List[str]) -> None:
        """Handle error during individual anomaly save."""
        error_msg = f"Error saving anomaly {anomaly.get('name', 'unknown')}: {str(exception)}"
        logger.error(error_msg)
        errors.append(error_msg)
        try:
            PriceAnomalySentryMonitor.capture_exception(exception, context={"anomaly": anomaly.get('name', '')})
        except Exception:
            logger.debug("Failed to capture anomaly save exception to Sentry")
    
    @classmethod
    def _save_single_anomaly(cls, vendor: str, anomaly: Dict[str, Any], errors: List[str]) -> bool:
        """
        Save a single anomaly to database.
        Returns True if saved successfully, False otherwise.
        """
        try:
            # Validate required fields
            validation_error = cls._validate_anomaly_fields(anomaly)
            if validation_error:
                logger.warning(validation_error)
                errors.append(validation_error)
                return False
            
            # Create record
            cls._create_anomaly_record(vendor, anomaly)
            cls._log_saved_anomaly(vendor, anomaly)
            return True
            
        except Exception as e:
            cls._handle_anomaly_save_error(anomaly, e, errors)
            return False
    
    @classmethod
    def _track_save_errors(cls, errors: List[str], saved_count: int) -> None:
        """Track save errors to Sentry if any exist."""
        if errors:
            try:
                PriceAnomalySentryMonitor.track_save_result(False, saved_count, errors)
            except Exception:
                logger.debug("Failed to report save errors to Sentry")
    
    @classmethod
    def _handle_transaction_error(cls, vendor: str, exception: Exception) -> Dict[str, Any]:
        """Handle transaction-level error during save."""
        error_msg = f"Transaction error saving anomalies for {vendor}: {str(exception)}"
        logger.error(error_msg)
        try:
            PriceAnomalySentryMonitor.capture_exception(exception, context={"vendor": vendor})
        except Exception:
            logger.debug("Failed to capture transaction exception to Sentry")
        return {
            'success': False,
            'saved_count': 0,
            'errors': [error_msg]
        }
    
    @classmethod
    def save_anomalies(cls, vendor: str, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Save detected price anomalies to database
        
        Args:
            vendor: Vendor name (gemilang, mitra10, tokopedia, etc.)
            anomalies: List of anomaly dictionaries containing:
                - name: Product name
                - url: Product URL
                - unit: Product unit
                - location: Product location (optional)
                - old_price: Previous price
                - new_price: Current price
                - change_percent: Percentage change
        
        Returns:
            Dictionary with:
                - success: Boolean
                - saved_count: Number of anomalies saved
                - errors: List of errors if any
        """
        if not anomalies:
            return {'success': True, 'saved_count': 0, 'errors': []}
        
        # Validate vendor
        vendor_error = cls._validate_vendor(vendor)
        if vendor_error:
            logger.error(vendor_error)
            return {'success': False, 'saved_count': 0, 'errors': [vendor_error]}
        
        # Set Sentry context
        cls._set_sentry_context(vendor, anomalies)
        
        # Save anomalies in transaction
        saved_count = 0
        errors = []
        
        try:
            with transaction.atomic():
                for anomaly in anomalies:
                    if cls._save_single_anomaly(vendor, anomaly, errors):
                        saved_count += 1
                        
            logger.info(f"Successfully saved {saved_count} anomalies for {vendor}")
            cls._track_save_errors(errors, saved_count)
            
            return {
                'success': True,
                'saved_count': saved_count,
                'errors': errors
            }
            
        except Exception as e:
            return cls._handle_transaction_error(vendor, e)
    
    @classmethod
    def get_pending_anomalies(cls, vendor: str = None) -> List[PriceAnomaly]:
        """
        Get all pending anomalies for review
        
        Args:
            vendor: Optional vendor filter
            
        Returns:
            List of PriceAnomaly objects
        """
        queryset = PriceAnomaly.objects.filter(status='pending')
        
        if vendor and vendor in cls.VENDOR_MAP:
            queryset = queryset.filter(vendor=cls.VENDOR_MAP[vendor])
        
        return list(queryset)
    
    @classmethod
    def mark_as_reviewed(cls, anomaly_id: int, status: str = 'reviewed', notes: str = '') -> bool:
        """
        Mark an anomaly as reviewed
        
        Args:
            anomaly_id: ID of the anomaly
            status: New status (reviewed, approved, rejected)
            notes: Optional review notes
            
        Returns:
            Boolean indicating success
        """
        try:
            anomaly = PriceAnomaly.objects.get(id=anomaly_id)
            anomaly.status = status
            anomaly.notes = notes
            anomaly.reviewed_at = timezone.now()
            anomaly.save()
            
            logger.info(f"Marked anomaly {anomaly_id} as {status}")
            return True
            
        except PriceAnomaly.DoesNotExist:
            logger.error(f"Anomaly {anomaly_id} not found for review")
            try:
                PriceAnomalySentryMonitor.track_review_error(anomaly_id, ERROR_ANOMALY_NOT_FOUND, {"status": status})
            except Exception:
                logger.debug("Failed to report review error to Sentry")
            return False
        except Exception as e:
            logger.error(f"Error marking anomaly {anomaly_id} as reviewed: {str(e)}")
            try:
                PriceAnomalySentryMonitor.capture_exception(e, {"anomaly_id": anomaly_id, "operation": "mark_as_reviewed"})
            except Exception:
                logger.debug("Failed to capture review exception to Sentry")
            return False
    
    @classmethod
    def apply_approved_price(cls, anomaly_id: int) -> Dict[str, Any]:
        """
        Apply an approved price anomaly to the product database
        
        Args:
            anomaly_id: ID of the anomaly to apply
            
        Returns:
            Dictionary with:
                - success: Boolean
                - message: Status message
                - updated: Number of products updated
        """
        try:
            anomaly = PriceAnomaly.objects.get(id=anomaly_id)
            
            # Validate anomaly status
            if anomaly.status != 'approved':
                return {
                    'success': False,
                    'message': f'Anomaly must be approved before applying. Current status: {anomaly.status}',
                    'updated': 0
                }
            
            # Map vendor to pre-defined UPDATE queries (prevents SQL injection)
            # Each query is hardcoded - no dynamic table name construction
            VENDOR_UPDATE_QUERIES = {
                'gemilang': """
                    UPDATE gemilang_products
                    SET price = %s, updated_at = %s
                    WHERE name = %s AND url = %s AND unit = %s
                """,
                'mitra10': """
                    UPDATE mitra10_products
                    SET price = %s, updated_at = %s
                    WHERE name = %s AND url = %s AND unit = %s
                """,
                'tokopedia': """
                    UPDATE tokopedia_products
                    SET price = %s, updated_at = %s
                    WHERE name = %s AND url = %s AND unit = %s
                """,
                'depobangunan': """
                    UPDATE depobangunan_products
                    SET price = %s, updated_at = %s
                    WHERE name = %s AND url = %s AND unit = %s
                """,
                'juragan_material': """
                    UPDATE juragan_material_products
                    SET price = %s, updated_at = %s
                    WHERE name = %s AND url = %s AND unit = %s
                """,
            }
            
            if anomaly.vendor not in VENDOR_UPDATE_QUERIES:
                return {
                    'success': False,
                    'message': f'Unknown vendor: {anomaly.vendor}',
                    'updated': 0
                }
            
            # Get pre-defined query (no f-string formatting)
            update_sql = VENDOR_UPDATE_QUERIES[anomaly.vendor]
            
            # Update the product price in database
            with transaction.atomic():
                with connection.cursor() as cursor:
                    # Execute with fully parameterized query
                    cursor.execute(
                        update_sql,
                        (
                            anomaly.new_price,
                            timezone.now(),
                            anomaly.product_name,
                            anomaly.product_url,
                            anomaly.unit
                        )
                    )
                    
                    updated_count = cursor.rowcount
                    
                    if updated_count > 0:
                        # Mark anomaly as applied
                        anomaly.status = 'applied'
                        anomaly.save()

                        logger.info(
                            f"Applied approved price for {anomaly.vendor}: {anomaly.product_name} "
                            f"updated to {anomaly.new_price}"
                        )

                        return {
                            'success': True,
                            'message': f'Price updated successfully for {updated_count} product(s)',
                            'updated': updated_count
                        }
                    else:
                        logger.warning(
                            f"No matching product found for anomaly {anomaly_id}: "
                            f"{anomaly.product_name}"
                        )
                        try:
                            PriceAnomalySentryMonitor.track_apply_result(anomaly.id, False, 0, message=ERROR_NO_MATCHING_PRODUCT)
                        except Exception:
                            logger.debug("Failed to report anomaly apply failure to Sentry")
                        return {
                            'success': False,
                            'message': ERROR_NO_MATCHING_PRODUCT,
                            'updated': 0
                        }
                        
        except PriceAnomaly.DoesNotExist:
            logger.error(f"Anomaly {anomaly_id} not found")
            try:
                PriceAnomalySentryMonitor.track_apply_result(anomaly_id, False, 0, message=ERROR_ANOMALY_NOT_FOUND)
            except Exception:
                logger.debug("Failed to report missing anomaly to Sentry")
            return {
                'success': False,
                'message': ERROR_ANOMALY_NOT_FOUND,
                'updated': 0
            }
        except Exception as e:
            logger.error(f"Error applying anomaly {anomaly_id}: {str(e)}")
            try:
                PriceAnomalySentryMonitor.capture_exception(e, context={"anomaly_id": anomaly_id})
            except Exception:
                logger.debug("Failed to capture anomaly apply exception to Sentry")
            return {
                'success': False,
                'message': f'Error applying price: {str(e)}',
                'updated': 0
            }
    
    @classmethod
    def reject_anomaly(cls, anomaly_id: int, notes: str = '') -> Dict[str, Any]:
        """
        Reject a price anomaly (keep old price)
        
        Args:
            anomaly_id: ID of the anomaly to reject
            notes: Rejection reason
            
        Returns:
            Dictionary with success status and message
        """
        try:
            anomaly = PriceAnomaly.objects.get(id=anomaly_id)
            
            if anomaly.status == 'rejected':
                return {
                    'success': True,
                    'message': 'Anomaly already rejected'
                }
            
            anomaly.status = 'rejected'
            anomaly.notes = notes
            anomaly.reviewed_at = timezone.now()
            anomaly.save()
            
            logger.info(f"Rejected anomaly {anomaly_id}: {notes}")
            
            return {
                'success': True,
                'message': 'Anomaly rejected successfully'
            }
            
        except PriceAnomaly.DoesNotExist:
            logger.error(f"Anomaly {anomaly_id} not found")
            return {
                'success': False,
                'message': 'Anomaly not found'
            }
        except Exception as e:
            logger.error(f"Error rejecting anomaly {anomaly_id}: {str(e)}")
            return {
                'success': False,
                'message': f'Error rejecting anomaly: {str(e)}'
            }
    
    @classmethod
    def batch_apply_approved(cls, anomaly_ids: List[int]) -> Dict[str, Any]:
        """
        Apply multiple approved anomalies at once
        
        Args:
            anomaly_ids: List of anomaly IDs to apply
            
        Returns:
            Dictionary with:
                - success: Boolean
                - applied_count: Number of anomalies applied
                - failed_count: Number that failed
                - results: List of individual results
        """
        results = []
        applied_count = 0
        failed_count = 0
        
        for anomaly_id in anomaly_ids:
            result = cls.apply_approved_price(anomaly_id)
            results.append({
                'anomaly_id': anomaly_id,
                'success': result['success'],
                'message': result['message']
            })
            
            if result['success']:
                applied_count += 1
            else:
                failed_count += 1
        
        logger.info(
            f"Batch apply completed: {applied_count} applied, {failed_count} failed"
        )
        
        return {
            'success': True,
            'applied_count': applied_count,
            'failed_count': failed_count,
            'results': results
        }
