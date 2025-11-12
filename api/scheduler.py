from __future__ import annotations

import logging
import time
from typing import Any, Dict, Iterable, List, Optional
from importlib import import_module
from django.utils import timezone
from datetime import datetime

def _now():
    try:
        return timezone.now()
    except Exception:
        return datetime.now()

from .views import get_scraper_factory

logger = logging.getLogger(__name__)


class BaseScheduler:
    def get_categories(self, vendor: str, server_time) -> List[str]:
        try:
            mod = import_module(f"api.{vendor}.categorizer")
            fn = getattr(mod, 'get_categories', None)
            if fn:
                try:
                    return list(fn(server_time))
                except TypeError:
                    return list(fn())
        except Exception:
            pass
        return []

    def create_scraper(self, vendor: str):
        return get_scraper_factory(vendor)

    def load_db_service(self, vendor: str):
        try:
            mod = import_module(f"api.{vendor}.database_service")
        except Exception:
            return None
        for attr in dir(mod):
            if 'DatabaseService' in attr:
                cls = getattr(mod, attr)
                try:
                    return cls()
                except Exception:
                    return None
        return None

    def normalize_products(self, products: List[Any]) -> List[Dict[str, Any]]:
        out = []
        for p in products:
            if isinstance(p, dict):
                out.append(p)
                continue
            try:
                out.append({'name': getattr(p, 'name'), 'price': getattr(p, 'price'), 'url': getattr(p, 'url'), 'unit': getattr(p, 'unit', '')})
            except Exception:
                logger.warning(f"Unable to normalize product: {p}")
        return out

    def enrich_unit(self, scraper, product):
        try:
            if hasattr(scraper, 'scrape_product_details'):
                url = product.get('url') if isinstance(product, dict) else getattr(product, 'url', None)
                if url:
                    detail = scraper.scrape_product_details(url)
                    unit = getattr(detail, 'unit', None)
                    if unit:
                        if isinstance(product, dict):
                            product['unit'] = unit
                        else:
                            try:
                                setattr(product, 'unit', unit)
                            except Exception:
                                pass
        except Exception:
            pass

    def run(self, server_time=None, vendors: Optional[Iterable[str]] = None, pages_per_keyword: int = 1, use_price_update: bool = False, max_products_per_keyword: Optional[int] = None, expected_start_time=None) -> Dict[str, Any]:
        start_timestamp = time.time()
        server_time = server_time or _now()
        
        timing_delay = None
        if expected_start_time:
            try:
                delay_seconds = (server_time.timestamp() - expected_start_time.timestamp()) if hasattr(server_time, 'timestamp') else 0
                timing_delay = delay_seconds
            except Exception:
                timing_delay = None
        
        summary: Dict[str, Any] = {
            'server_time': str(server_time),
            'start_timestamp': start_timestamp,
            'timing_delay_seconds': timing_delay,
            'vendors': {},
            'errors': [],
            'total_vendors': 0,
            'successful_vendors': 0,
            'failed_vendors': 0
        }
        
        default_vendors = ['depobangunan', 'gemilang', 'juragan_material', 'mitra10']
        vendors = list(vendors) if vendors is not None else default_vendors
        summary['total_vendors'] = len(vendors)
        
        for vendor in vendors:
            vendor_start = time.time()
            vendor_result = {
                'keywords': 0,
                'products_found': 0,
                'saved': 0,
                'errors': [],
                'status': 'unknown',
                'duration_seconds': 0,
                'scrape_failures': 0,
                'scrape_attempts': 0
            }
            
            try:
                cats = self.get_categories(vendor, server_time)
                if not cats:
                    vendor_result['status'] = 'skipped_no_categories'
                    vendor_result['errors'].append(f'No categories returned for vendor {vendor}')
                    logger.warning(f'Vendor {vendor} skipped: no categories available')
                    summary['vendors'][vendor] = vendor_result
                    summary['failed_vendors'] += 1
                    continue
                
                vendor_result['keywords'] = len(cats)
                
                try:
                    scraper = self.create_scraper(vendor)
                except Exception as e:
                    vendor_result['status'] = 'failed_scraper_creation'
                    error_msg = f'Failed to create scraper for {vendor}: {type(e).__name__}: {str(e)}'
                    vendor_result['errors'].append(error_msg)
                    logger.error(error_msg)
                    summary['errors'].append({'vendor': vendor, 'error': error_msg, 'type': 'scraper_creation'})
                    summary['vendors'][vendor] = vendor_result
                    summary['failed_vendors'] += 1
                    continue
                
                db_service = self.load_db_service(vendor)
                if not db_service:
                    logger.warning(f'No database service available for vendor {vendor}')
                
                total_products = 0
                total_saved = 0
                
                for keyword in cats:
                    for page in range(pages_per_keyword):
                        vendor_result['scrape_attempts'] += 1
                        try:
                            result = scraper.scrape_products(keyword=keyword, sort_by_price=True, page=page)
                            if not getattr(result, 'success', False):
                                vendor_result['scrape_failures'] += 1
                                error_msg = f'{vendor} scrape failed for keyword "{keyword}" page {page}: {getattr(result, "error_message", "unknown error")}'
                                vendor_result['errors'].append(error_msg)
                                logger.error(error_msg)
                                continue
                            
                            products = list(getattr(result, 'products', []) or [])
                            
                            for prod in products:
                                prod_unit = prod.get('unit') if isinstance(prod, dict) else getattr(prod, 'unit', None)
                                if not prod_unit:
                                    self.enrich_unit(scraper, prod)
                            
                            products_data = self.normalize_products(products)
                            total_products += len(products_data)
                            
                            if max_products_per_keyword is not None and len(products_data) > max_products_per_keyword:
                                products_data = products_data[:max_products_per_keyword]
                            
                            if db_service and products_data:
                                try:
                                    if use_price_update and hasattr(db_service, 'save_with_price_update'):
                                        res = db_service.save_with_price_update(products_data)
                                        saved_count = int(res.get('inserted', 0) if isinstance(res, dict) else 0) if isinstance(res, dict) else 0
                                        saved_count = saved_count or int(res.get('new_count', 0) if isinstance(res, dict) else 0)
                                    else:
                                        res = db_service.save(products_data)
                                        if isinstance(res, tuple):
                                            saved_count = len(products_data) if res[0] else 0
                                        elif isinstance(res, bool):
                                            saved_count = len(products_data) if res else 0
                                        elif isinstance(res, dict):
                                            saved_count = int(res.get('inserted', 0) or res.get('new_count', 0) or res.get('saved', 0) or 0)
                                        else:
                                            saved_count = 0
                                    total_saved += saved_count
                                except Exception as e:
                                    error_msg = f'{vendor} database save failed for keyword "{keyword}": {type(e).__name__}: {str(e)}'
                                    vendor_result['errors'].append(error_msg)
                                    logger.error(error_msg)
                        except Exception as e:
                            vendor_result['scrape_failures'] += 1
                            error_msg = f'{vendor} exception during scrape keyword "{keyword}" page {page}: {type(e).__name__}: {str(e)}'
                            vendor_result['errors'].append(error_msg)
                            logger.exception(error_msg)
                
                vendor_result['products_found'] = total_products
                vendor_result['saved'] = total_saved
                
                if vendor_result['scrape_failures'] == vendor_result['scrape_attempts'] and vendor_result['scrape_attempts'] > 0:
                    vendor_result['status'] = 'failed_all_scrapes'
                    summary['failed_vendors'] += 1
                    summary['errors'].append({'vendor': vendor, 'error': f'All {vendor_result["scrape_attempts"]} scrape attempts failed', 'type': 'complete_failure'})
                elif vendor_result['scrape_failures'] > 0:
                    vendor_result['status'] = 'partial_success'
                    summary['successful_vendors'] += 1
                elif total_products == 0:
                    vendor_result['status'] = 'no_products_found'
                    vendor_result['errors'].append(f'No products found for vendor {vendor}')
                    summary['successful_vendors'] += 1
                else:
                    vendor_result['status'] = 'success'
                    summary['successful_vendors'] += 1
                    
            except Exception as e:
                vendor_result['status'] = 'failed_exception'
                error_msg = f'{vendor} critical exception: {type(e).__name__}: {str(e)}'
                vendor_result['errors'].append(error_msg)
                logger.exception(error_msg)
                summary['errors'].append({'vendor': vendor, 'error': error_msg, 'type': 'critical_exception'})
                summary['failed_vendors'] += 1
            
            vendor_result['duration_seconds'] = round(time.time() - vendor_start, 2)
            summary['vendors'][vendor] = vendor_result
        
        summary['total_duration_seconds'] = round(time.time() - start_timestamp, 2)
        summary['end_timestamp'] = time.time()
        
        return summary

