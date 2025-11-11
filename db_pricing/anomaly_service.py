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

logger = logging.getLogger(__name__)


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
            return {
                'success': True,
                'saved_count': 0,
                'errors': []
            }
        
        # Validate vendor
        if vendor not in cls.VENDOR_MAP:
            error_msg = f"Invalid vendor: {vendor}"
            logger.error(error_msg)
            return {
                'success': False,
                'saved_count': 0,
                'errors': [error_msg]
            }
        
        saved_count = 0
        errors = []
        
        try:
            with transaction.atomic():
                for anomaly in anomalies:
                    try:
                        # Extract data from anomaly dictionary
                        product_name = anomaly.get('name', '')
                        product_url = anomaly.get('url', '')
                        unit = anomaly.get('unit', '')
                        location = anomaly.get('location', '')
                        old_price = anomaly.get('old_price', 0)
                        new_price = anomaly.get('new_price', 0)
                        change_percent = anomaly.get('change_percent', 0)
                        
                        # Validate required fields
                        if not product_name or not product_url:
                            error_msg = f"Missing required fields for anomaly: {anomaly}"
                            logger.warning(error_msg)
                            errors.append(error_msg)
                            continue
                        
                        # Create PriceAnomaly record
                        PriceAnomaly.objects.create(
                            vendor=cls.VENDOR_MAP[vendor],
                            product_name=product_name,
                            product_url=product_url,
                            unit=unit,
                            location=location,
                            old_price=old_price,
                            new_price=new_price,
                            change_percent=change_percent,
                            status='pending',
                            detected_at=timezone.now()
                        )
                        
                        saved_count += 1
                        logger.info(
                            f"Saved price anomaly for {vendor}: {product_name} "
                            f"({old_price} -> {new_price}, {change_percent}%)"
                        )
                        
                    except Exception as e:
                        error_msg = f"Error saving anomaly {anomaly.get('name', 'unknown')}: {str(e)}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        
            logger.info(f"Successfully saved {saved_count} anomalies for {vendor}")
            return {
                'success': True,
                'saved_count': saved_count,
                'errors': errors
            }
            
        except Exception as e:
            error_msg = f"Transaction error saving anomalies for {vendor}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'saved_count': 0,
                'errors': [error_msg]
            }
    
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
            logger.error(f"Anomaly {anomaly_id} not found")
            return False
        except Exception as e:
            logger.error(f"Error marking anomaly {anomaly_id} as reviewed: {str(e)}")
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
            
            # Map vendor to table name
            table_map = {
                'gemilang': 'gemilang_products',
                'mitra10': 'mitra10_products',
                'tokopedia': 'tokopedia_products',
                'depobangunan': 'depobangunan_products',
                'juragan_material': 'juragan_material_products',
            }
            
            if anomaly.vendor not in table_map:
                return {
                    'success': False,
                    'message': f'Unknown vendor: {anomaly.vendor}',
                    'updated': 0
                }
            
            table_name = table_map[anomaly.vendor]
            
            # Update the product price in database
            with transaction.atomic():
                with connection.cursor() as cursor:
                    # Update product based on name, url, and unit match
                    update_sql = f"""
                        UPDATE {table_name}
                        SET price = %s, updated_at = %s
                        WHERE name = %s AND url = %s AND unit = %s
                    """
                    
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
                        return {
                            'success': False,
                            'message': 'No matching product found to update',
                            'updated': 0
                        }
                        
        except PriceAnomaly.DoesNotExist:
            logger.error(f"Anomaly {anomaly_id} not found")
            return {
                'success': False,
                'message': 'Anomaly not found',
                'updated': 0
            }
        except Exception as e:
            logger.error(f"Error applying anomaly {anomaly_id}: {str(e)}")
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
