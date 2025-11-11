# db_pricing/anomaly_service.py
"""
Service for handling price anomaly notifications.
Saves detected price anomalies to the database for review.
"""

from typing import List, Dict, Any
from django.db import transaction
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
